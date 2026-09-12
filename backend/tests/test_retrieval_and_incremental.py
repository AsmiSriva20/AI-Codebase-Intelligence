from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from dotenv import load_dotenv
from git import Actor, Repo

load_dotenv()

from app.state import _git_changes  # noqa: E402
from app.storage.vectordb import _hybrid_shape, _lexical_rank, _tokenize  # noqa: E402


def _point(identifier, path, name, text, score=0.5):
    return SimpleNamespace(
        id=identifier,
        score=score,
        payload={
            "branch_id": "branch",
            "path": path,
            "name": name,
            "type": "function",
            "text": text,
        },
    )


class HybridRetrievalTests(unittest.TestCase):
    def test_tokenizer_splits_camel_case_identifiers(self):
        self.assertEqual(_tokenize("validateToken"), ["validate", "token"])

    @patch("app.storage.vectordb._scroll_branch")
    def test_lexical_rank_prefers_exact_symbol(self, scroll_branch):
        exact = _point("1", "auth.py", "validateToken", "validate a bearer token")
        other = _point("2", "user.py", "validateUser", "validate a user")
        scroll_branch.return_value = [other, exact]

        ranked = _lexical_rank("validateToken", "branch", limit=2)

        self.assertEqual(ranked[0][0].id, "1")
        self.assertTrue(ranked[0][2])

    def test_rrf_rewards_results_found_by_both_channels(self):
        shared = _point("1", "auth.py", "validate", "shared")
        dense_only = _point("2", "tokens.py", "decode", "dense")
        lexical_only = _point("3", "middleware.py", "auth", "lexical")

        result = _hybrid_shape(
            [shared, dense_only],
            [(shared, 4.0, True), (lexical_only, 3.0, False)],
            3,
        )

        self.assertEqual(result["metadatas"][0][0]["name"], "validate")
        self.assertEqual(
            result["metadatas"][0][0]["retrieval_methods"],
            ["lexical", "semantic"],
        )


class IncrementalGitTests(unittest.TestCase):
    def test_git_changes_reports_modified_added_and_deleted_paths(self):
        actor = Actor("Test User", "test@example.com")
        with tempfile.TemporaryDirectory() as directory:
            repo = Repo.init(directory)
            first_file = Path(directory, "first.py")
            deleted_file = Path(directory, "deleted.py")
            first_file.write_text("value = 1\n", encoding="utf-8")
            deleted_file.write_text("remove = True\n", encoding="utf-8")
            repo.index.add(["first.py", "deleted.py"])
            old_commit = repo.index.commit("initial", author=actor, committer=actor).hexsha

            first_file.write_text("value = 2\n", encoding="utf-8")
            deleted_file.unlink()
            Path(directory, "added.py").write_text("added = True\n", encoding="utf-8")
            repo.index.add(["first.py", "added.py"])
            repo.index.remove(["deleted.py"])
            new_commit = repo.index.commit("change", author=actor, committer=actor).hexsha

            changed, deleted = _git_changes(directory, old_commit, new_commit)
            repo.close()

        self.assertEqual(changed, {"first.py", "added.py"})
        self.assertEqual(deleted, {"deleted.py"})


if __name__ == "__main__":
    unittest.main()
