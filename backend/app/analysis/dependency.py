import os

from app import state
from app.parsers import LANGUAGE_BY_EXT


def get_dependencies(path):
    ext = os.path.splitext(path)[1].lower()
    if ext not in LANGUAGE_BY_EXT:
        return []

    full_path = os.path.join(state.REPO_PATH, path)
    analysis = state.get_file_analysis(full_path, path)
    if analysis is None:
        return []

    return sorted(set(analysis.get("imports", [])))
