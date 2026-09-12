import os

from app import state
from app.parsers import language_for_path


def get_dependencies(path):
    if language_for_path(path) is None:
        return []

    full_path = os.path.join(state.REPO_PATH, path)
    analysis = state.get_file_analysis(full_path)
    if analysis is None:
        return []

    return sorted(set(analysis.get("imports", [])))
