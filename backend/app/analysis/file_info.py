import os

from app import state
from app.parsers import language_for_path


def get_file_info(full_path, relative_path):
    ext = os.path.splitext(full_path)[1].lower()
    lang_name = language_for_path(full_path)

    if lang_name is None:
        return {
            "path": relative_path,
            "language": ext.lstrip(".") or "unknown",
            "functions": [],
            "classes": [],
            "imports": [],
            "docstring": None,
            "unsupported": True,
        }

    analysis = state.get_file_analysis(full_path)
    if analysis is None:
        return None

    return {
        "path": relative_path,
        "language": lang_name,
        "functions": sorted({fn["name"] for fn in analysis.get("functions", [])}),
        "classes": sorted(set(analysis.get("classes", []))),
        "imports": sorted(set(analysis.get("imports", []))),
        "docstring": None,
        **{key: analysis[key] for key in ("stages", "instructions", "services") if key in analysis},
    }
