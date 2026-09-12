"""Explainable repository health score built only from deterministic analyses."""


SEVERITY_DEDUCTIONS = {
    "critical": 20,
    "high": 10,
    "medium": 4,
    "low": 1,
    "info": 0.25,
}

CATEGORY_WEIGHTS = {
    "security": 0.25,
    "maintainability": 0.20,
    "architecture": 0.25,
    "dependencies": 0.15,
    "change_risk": 0.15,
}


def _bounded(value):
    return max(0, min(100, round(value)))


def _findings(issues_report, category):
    return [
        finding
        for findings in (issues_report or {}).get("by_file", {}).values()
        for finding in findings
        if finding.get("category") == category
    ]


def _score_findings(findings, label):
    deductions = []
    total = 0.0
    counts = {}
    for finding in findings:
        severity = finding.get("severity", "low")
        counts[severity] = counts.get(severity, 0) + 1
        total += SEVERITY_DEDUCTIONS.get(severity, 1)
    for severity, count in sorted(counts.items()):
        amount = round(SEVERITY_DEDUCTIONS.get(severity, 1) * count, 2)
        deductions.append({
            "reason": f"{count} {severity} {label} finding(s)",
            "points": amount,
        })
    return {"score": _bounded(100 - total), "deductions": deductions}


def calculate_health_score(
    issues_report,
    dependency_report,
    architecture_report,
    dead_code_report,
    hotspots_report,
):
    security = _score_findings(_findings(issues_report, "security"), "security")
    maintainability = _score_findings(_findings(issues_report, "quality"), "quality")

    dead_count = (dead_code_report or {}).get("total_dead", 0)
    if dead_count:
        points = min(25, dead_count * 1.5)
        maintainability["score"] = _bounded(maintainability["score"] - points)
        maintainability["deductions"].append({
            "reason": f"{dead_count} potentially unreferenced symbol(s)",
            "points": points,
        })

    architecture_summary = (architecture_report or {}).get("summary", {})
    architecture_deductions = [
        {
            "reason": f"{architecture_summary.get('layer_violations', 0)} layer violation(s)",
            "points": architecture_summary.get("layer_violations", 0) * 6,
        },
        {
            "reason": f"{architecture_summary.get('circular_dependencies', 0)} dependency cycle(s)",
            "points": architecture_summary.get("circular_dependencies", 0) * 15,
        },
        {
            "reason": f"{architecture_summary.get('high_coupling_modules', 0)} highly coupled module(s)",
            "points": architecture_summary.get("high_coupling_modules", 0) * 3,
        },
    ]
    architecture = {
        "score": _bounded(100 - sum(item["points"] for item in architecture_deductions)),
        "deductions": [item for item in architecture_deductions if item["points"]],
    }

    vulnerable = (dependency_report or {}).get("vulnerable_count", 0)
    dependency_points = min(100, vulnerable * 12)
    dependencies = {
        "score": _bounded(100 - dependency_points),
        "deductions": ([{
            "reason": f"{vulnerable} vulnerable dependency/dependencies",
            "points": dependency_points,
        }] if vulnerable else []),
    }

    hotspots = (hotspots_report or {}).get("hotspots", [])
    risky_hotspots = [item for item in hotspots if item.get("churn", 0) >= 5]
    hotspot_points = min(40, sum(item["churn"] - 4 for item in risky_hotspots))
    change_risk = {
        "score": _bounded(100 - hotspot_points),
        "deductions": ([{
            "reason": f"{len(risky_hotspots)} high-churn file(s)",
            "points": hotspot_points,
        }] if risky_hotspots else []),
    }

    categories = {
        "security": security,
        "maintainability": maintainability,
        "architecture": architecture,
        "dependencies": dependencies,
        "change_risk": change_risk,
    }
    overall = _bounded(sum(
        categories[name]["score"] * weight
        for name, weight in CATEGORY_WEIGHTS.items()
    ))
    grade = "A" if overall >= 90 else "B" if overall >= 80 else "C" if overall >= 70 else "D" if overall >= 60 else "F"

    return {
        "overall": overall,
        "grade": grade,
        "categories": categories,
        "methodology": {
            "starting_score": 100,
            "weights": CATEGORY_WEIGHTS,
            "note": "Scores are deterministic deductions from static, dependency, graph, and Git analyses; no LLM generates them.",
        },
    }
