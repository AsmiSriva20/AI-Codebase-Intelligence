import json
import os
import re

import requests

REQUIREMENT_LINE_RE = re.compile(r"^\s*([A-Za-z0-9_.\-]+)\s*(==|>=|<=|~=|>|<)?\s*([A-Za-z0-9_.\-]*)")
PYPROJECT_DEP_RE = re.compile(r'^\s*([A-Za-z0-9_.\-]+)\s*=\s*["\']([^"\']+)["\']', re.MULTILINE)

PYPROJECT_IGNORE_KEYS = {"python", "name", "version", "description", "readme", "license", "authors"}

OSV_ENDPOINT = "https://api.osv.dev/v1/querybatch"


def _parse_requirements_txt(full_path):
    deps = []
    try:
        with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or line.startswith("-"):
                    continue
                line = line.split(";")[0].strip()  # drop environment markers
                match = REQUIREMENT_LINE_RE.match(line)
                if match:
                    name, _, version = match.groups()
                    deps.append({"name": name, "version": version or None, "ecosystem": "PyPI"})
    except OSError:
        pass
    return deps


def _parse_package_json(full_path):
    deps = []
    try:
        with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return deps

    for section in ("dependencies", "devDependencies"):
        for name, version in (data.get(section) or {}).items():
            clean_version = re.sub(r"^[^\d]*", "", version) if version else None
            deps.append({"name": name, "version": clean_version or None, "ecosystem": "npm"})

    return deps


def _parse_pyproject_toml(full_path):
    deps = []
    try:
        with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
    except OSError:
        return deps

    for name, version in PYPROJECT_DEP_RE.findall(content):
        if name.lower() in PYPROJECT_IGNORE_KEYS:
            continue
        deps.append({"name": name, "version": version.lstrip("^~>=< "), "ecosystem": "PyPI"})

    return deps


MANIFEST_PARSERS = {
    "requirements.txt": _parse_requirements_txt,
    "package.json": _parse_package_json,
    "pyproject.toml": _parse_pyproject_toml,
}


def collect_dependencies(files):
    manifests_found = []
    all_deps = []

    for file in files:
        filename = os.path.basename(file["path"])
        parser = MANIFEST_PARSERS.get(filename)
        if parser:
            manifests_found.append(file["path"])
            all_deps.extend(parser(file["full_path"]))

    unique = {}
    for dep in all_deps:
        key = (dep["name"].lower(), dep["ecosystem"])
        if key not in unique:
            unique[key] = dep

    return manifests_found, list(unique.values())


def check_vulnerabilities(dependencies, timeout=6):
    """
    Best-effort OSV.dev batch lookup for known vulnerabilities. Returns {}
    on any network failure so the dependency list always still works offline.
    """
    queryable = [d for d in dependencies if d.get("version")]
    if not queryable:
        return {}

    queries = [
        {"package": {"name": dep["name"], "ecosystem": dep["ecosystem"]}, "version": dep["version"]}
        for dep in queryable
    ]

    try:
        response = requests.post(OSV_ENDPOINT, json={"queries": queries}, timeout=timeout)
        response.raise_for_status()
        results = response.json().get("results", [])
    except Exception as e:
        print(f"OSV lookup skipped: {e}")
        return {}

    vuln_by_key = {}
    for dep, result in zip(queryable, results):
        vulns = result.get("vulns") or []
        if vulns:
            key = f"{dep['name']}@{dep['version']}"
            vuln_by_key[key] = [v.get("id") for v in vulns if v.get("id")]

    return vuln_by_key


def generate_dependency_report(files):
    manifests, dependencies = collect_dependencies(files)
    vulns = check_vulnerabilities(dependencies)

    enriched = []
    for dep in sorted(dependencies, key=lambda d: d["name"].lower()):
        key = f"{dep['name']}@{dep['version']}" if dep.get("version") else None
        vuln_ids = vulns.get(key, []) if key else []
        enriched.append({
            **dep,
            "vulnerability_ids": vuln_ids,
            "solution": (
                f"Upgrade {dep['name']} past the version(s) named in "
                f"{', '.join(vuln_ids)} — check the advisory on osv.dev for the first patched release."
            ) if vuln_ids else None,
        })

    return {
        "manifests": manifests,
        "total_dependencies": len(enriched),
        "vulnerable_count": sum(1 for d in enriched if d["vulnerability_ids"]),
        "dependencies": enriched,
    }
