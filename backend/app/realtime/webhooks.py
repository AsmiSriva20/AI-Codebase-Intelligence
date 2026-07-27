import hashlib
import hmac
import os

_URL_PREFIXES = ("https://", "http://", "ssh://git@github.com/", "git@github.com:")
_HOST_PREFIXES = ("github.com/",)


def verify_signature(payload_body: bytes, signature_header):
    """Verify GitHub's X-Hub-Signature-256 header against GITHUB_WEBHOOK_SECRET.

    This endpoint is publicly reachable once deployed — an unverified request
    must never trigger a rebuild, so any missing secret/header/mismatch is a
    hard reject, not a fallback.
    """
    secret = os.environ.get("GITHUB_WEBHOOK_SECRET")
    if not secret or not signature_header or not signature_header.startswith("sha256="):
        return False

    expected = hmac.new(secret.encode(), payload_body, hashlib.sha256).hexdigest()
    provided = signature_header[len("sha256="):]
    return hmac.compare_digest(expected, provided)


def parse_push_event(payload: dict):
    """Extract repo clone URL, branch name, and head commit SHA from a GitHub
    'push' webhook payload. Returns branch=None for anything that isn't a
    branch push (e.g. a tag push), which callers should ignore."""
    ref = payload.get("ref", "")
    branch = ref[len("refs/heads/"):] if ref.startswith("refs/heads/") else None

    return {
        "repo_url": payload.get("repository", {}).get("clone_url"),
        "branch": branch,
        "commit_sha": payload.get("after"),
    }


def normalize_repo_url(url):
    """Loose equality for repo URLs across the https/ssh/.git-suffix variants
    GitHub and a user's own `/clone` call might each use for the same repo."""
    if not url:
        return ""
    normalized = url.strip().lower().rstrip("/")
    if normalized.endswith(".git"):
        normalized = normalized[:-4]
    for prefix in _URL_PREFIXES:
        if normalized.startswith(prefix):
            normalized = normalized[len(prefix):]
            break
    for host in _HOST_PREFIXES:
        if normalized.startswith(host):
            normalized = normalized[len(host):]
            break
    return normalized
