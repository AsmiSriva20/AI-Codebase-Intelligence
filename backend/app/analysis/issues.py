import os
import re

from app.config import BINARY_SKIP_EXTENSIONS as SKIP_EXTENSIONS
from app.config import MAX_INDEXABLE_FILE_SIZE as MAX_FILE_SIZE
from app.config import LARGE_FILE_LINES

SEVERITIES = ("critical", "high", "medium", "low", "info")

# (id, severity, category, compiled regex, human message, suggested fix)
RULES = [
    ("hardcoded-aws-key", "critical", "security",
     re.compile(r"AKIA[0-9A-Z]{16}"),
     "Hardcoded AWS access key ID.",
     "Revoke this key in the AWS IAM console immediately, then load credentials from environment variables or a secrets manager (e.g. AWS Secrets Manager)."),

    ("hardcoded-private-key", "critical", "security",
     re.compile(r"-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----"),
     "Private key committed to the repository.",
     "Remove the key from version control and git history, rotate/reissue it, and load it from a secure secret store or mounted volume instead."),

    ("hardcoded-github-token", "critical", "security",
     re.compile(r"gh[pousr]_[A-Za-z0-9]{20,}"),
     "Hardcoded GitHub token.",
     "Revoke the token in GitHub Settings → Developer settings, then load it from an environment variable or CI secret."),

    ("hardcoded-slack-token", "high", "security",
     re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}"),
     "Hardcoded Slack token.",
     "Revoke the token in your Slack app settings and load it from an environment variable instead."),

    ("hardcoded-secret-assignment", "high", "security",
     re.compile(r"""(?i)\b(api[_-]?key|secret|token|password|passwd|pwd)\b\s*[:=]\s*['"][A-Za-z0-9/+_\-]{8,}['"]"""),
     "Possible hardcoded credential or secret.",
     "Move this value out of source control into an environment variable (.env, untracked) or a secrets manager, then rotate the exposed value."),

    ("eval-usage", "high", "security",
     re.compile(r"\beval\s*\("),
     "Use of eval() can execute arbitrary code.",
     "Replace eval() with a safe parser (e.g. json.loads for data) or an explicit allow-list of operations."),

    ("exec-usage", "medium", "security",
     re.compile(r"\bexec\s*\("),
     "Use of exec() can execute arbitrary code.",
     "Avoid exec() on dynamic/user-controlled input; refactor to explicit function dispatch instead."),

    ("shell-true", "high", "security",
     re.compile(r"shell\s*=\s*True"),
     "subprocess call with shell=True risks shell injection.",
     "Pass the command as a list (subprocess.run([...])) and drop shell=True; if a shell is unavoidable, sanitize input with shlex.quote()."),

    ("os-system", "medium", "security",
     re.compile(r"\bos\.system\s*\("),
     "os.system() is prone to shell injection; prefer subprocess with an argument list.",
     "Replace with subprocess.run([...]) using an argument list, which avoids shell interpretation entirely."),

    ("pickle-load", "medium", "security",
     re.compile(r"\bpickle\.(load|loads)\s*\("),
     "Deserializing with pickle can execute arbitrary code from untrusted input.",
     "Only unpickle data you fully trust, or switch to a safe serialization format like JSON."),

    ("yaml-unsafe-load", "medium", "security",
     re.compile(r"yaml\.load\s*\((?!.*Loader\s*=\s*yaml\.SafeLoader)"),
     "yaml.load without SafeLoader can execute arbitrary code.",
     "Use yaml.safe_load(...) or pass Loader=yaml.SafeLoader explicitly."),

    ("disabled-tls-verify-py", "high", "security",
     re.compile(r"verify\s*=\s*False"),
     "TLS certificate verification disabled.",
     "Re-enable verification (verify=True) and fix the underlying certificate/trust issue instead of bypassing it."),

    ("disabled-tls-verify-js", "high", "security",
     re.compile(r"rejectUnauthorized\s*:\s*false|NODE_TLS_REJECT_UNAUTHORIZED\s*=\s*['\"]?0"),
     "TLS certificate verification disabled.",
     "Remove the override and fix the certificate chain (e.g. via NODE_EXTRA_CA_CERTS) instead of disabling verification."),

    ("wildcard-cors", "medium", "security",
     re.compile(r"""Access-Control-Allow-Origin['"]?\s*[:=]\s*['"]\*['"]|allow_origins\s*=\s*\[\s*['"]\*['"]\s*\]"""),
     "Wildcard CORS origin allows any site to call this API.",
     "Restrict Access-Control-Allow-Origin to an explicit allow-list of trusted origins."),

    ("dangerously-set-innerhtml", "medium", "security",
     re.compile(r"dangerouslySetInnerHTML|\.innerHTML\s*="),
     "Assigning raw HTML can introduce XSS if the value includes user input.",
     "Sanitize the HTML first (e.g. with DOMPurify) or avoid raw HTML injection in favor of text content / safe templating."),

    ("sql-string-building", "medium", "security",
     re.compile(r"""(?i)(SELECT|INSERT|UPDATE|DELETE)\b[^\n]{0,80}['"]\s*\+|f['"](?:SELECT|INSERT|UPDATE|DELETE)\b"""),
     "Possible SQL built via string concatenation/f-string; use parameterized queries.",
     "Use parameterized queries or an ORM (e.g. cursor.execute(query, params)) instead of concatenating user input into SQL."),

    ("debug-true", "low", "security",
     re.compile(r"(?i)\bDEBUG\s*=\s*True\b"),
     "Debug mode enabled; should be off in production.",
     "Load this flag from an environment variable and default it to False in production."),

    ("todo-comment", "info", "quality",
     re.compile(r"(?i)(#|//)\s*(TODO|FIXME|HACK|XXX)\b"),
     "Unresolved TODO/FIXME left in code.",
     "Resolve it now or file a tracked issue and reference it in the comment."),

    ("console-log", "info", "quality",
     re.compile(r"\bconsole\.(log|debug)\s*\("),
     "Leftover console.log/debug statement.",
     "Remove the statement or gate it behind a debug flag / proper logger."),

    ("debugger-statement", "low", "quality",
     re.compile(r"^\s*debugger\s*;?\s*$"),
     "Leftover debugger statement.",
     "Remove the debugger statement before committing."),
]

LARGE_FILE_SOLUTION = "Split this file into smaller, single-responsibility modules to make it easier to review and test."


def _should_skip(path):
    lower = path.lower()
    return any(lower.endswith(ext) for ext in SKIP_EXTENSIONS)


def scan_file(full_path, relative_path):
    if _should_skip(relative_path):
        return []

    try:
        if os.path.getsize(full_path) > MAX_FILE_SIZE:
            return []
    except OSError:
        return []

    try:
        with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
    except OSError:
        return []

    findings = []

    for rule_id, severity, category, pattern, message, solution in RULES:
        for lineno, line in enumerate(lines, start=1):
            if pattern.search(line):
                findings.append({
                    "id": rule_id,
                    "severity": severity,
                    "category": category,
                    "message": message,
                    "solution": solution,
                    "path": relative_path,
                    "line": lineno,
                    "snippet": line.strip()[:200],
                })

    if len(lines) > LARGE_FILE_LINES:
        findings.append({
            "id": "large-file",
            "severity": "low",
            "category": "quality",
            "message": f"Large file ({len(lines)} lines) — consider splitting it up for readability.",
            "solution": LARGE_FILE_SOLUTION,
            "path": relative_path,
            "line": 1,
            "snippet": "",
        })

    return findings


def scan_repository(files):
    all_findings = []

    for file in files:
        all_findings.extend(scan_file(file["full_path"], file["path"]))

    by_file = {}
    for finding in all_findings:
        by_file.setdefault(finding["path"], []).append(finding)

    summary = {severity: 0 for severity in SEVERITIES}
    for finding in all_findings:
        summary[finding["severity"]] = summary.get(finding["severity"], 0) + 1

    def risk_score(findings):
        weight = {"critical": 4, "high": 3, "medium": 2, "low": 1, "info": 0}
        return sum(weight.get(f["severity"], 0) for f in findings)

    top_files = sorted(by_file.items(), key=lambda kv: risk_score(kv[1]), reverse=True)[:10]

    return {
        "summary": summary,
        "total_files_scanned": len(files),
        "total_findings": len(all_findings),
        "by_file": by_file,
        "top_files": [{"path": path, "count": len(findings)} for path, findings in top_files if findings],
    }
