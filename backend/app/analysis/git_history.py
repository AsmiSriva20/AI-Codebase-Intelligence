from collections import Counter

from git import Repo

from app.config import GIT_HISTORY_MAX_COMMITS, HOTSPOTS_DEFAULT_SINCE_DAYS, HOTSPOTS_TOP_N


def get_file_history(repo_path, path, max_count=GIT_HISTORY_MAX_COMMITS):
    """repo.iter_commits(paths=path) -> list of {sha, author, date, message}"""
    repo = Repo(repo_path)
    commits = list(repo.iter_commits(paths=path, max_count=max_count))
    return [
        {
            "sha": c.hexsha,
            "author": c.author.name,
            "date": c.committed_datetime.isoformat(),
            "message": c.message.strip().split("\n")[0],
        }
        for c in commits
    ]


def compute_churn(repo_path, since_days=HOTSPOTS_DEFAULT_SINCE_DAYS):
    """Commit count per file in the last `since_days`, via a single `git log` call."""
    repo = Repo(repo_path)
    raw = repo.git.log(f"--since={since_days} days ago", "--name-only", "--pretty=format:")
    return dict(Counter(line.strip() for line in raw.splitlines() if line.strip()))


def get_hotspots(repo_path, files, since_days=HOTSPOTS_DEFAULT_SINCE_DAYS, top_n=HOTSPOTS_TOP_N):
    """Top-N files by churn (commit count), restricted to files that still exist."""
    churn = compute_churn(repo_path, since_days)
    valid_paths = {f["path"] for f in files}

    ranked = sorted(
        ((path, count) for path, count in churn.items() if path in valid_paths),
        key=lambda kv: kv[1],
        reverse=True,
    )
    return [{"path": path, "churn": count} for path, count in ranked[:top_n]]
