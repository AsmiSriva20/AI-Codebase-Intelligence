import unittest

from app.analysis.architecture_health import analyze_architecture_health
from app.analysis.change_impact import analyze_change_impact
from app.analysis.health_score import calculate_health_score
from app.analysis.retriever import retrieval_confidence


class ArchitectureHealthTests(unittest.TestCase):
    def test_finds_layer_violations_and_cycles(self):
        report = analyze_architecture_health({
            "nodes": [
                "app/routers/users.py",
                "app/repositories/users.py",
            ],
            "edges": [
                {"from": "app/routers/users.py", "to": "app/repositories/users.py"},
                {"from": "app/repositories/users.py", "to": "app/routers/users.py"},
            ],
        })

        self.assertEqual(report["summary"]["layer_violations"], 2)
        self.assertEqual(report["summary"]["circular_dependencies"], 1)
        self.assertEqual(report["circular_dependencies"][0]["size"], 2)


class ChangeImpactTests(unittest.TestCase):
    def test_traverses_callers_modules_endpoints_and_tests(self):
        graph = {
            "app/service.py::validate": {
                "calls": [],
                "called_by": ["app/routers/auth.py::login"],
            },
            "app/routers/auth.py::login": {
                "calls": [{"name": "validate", "resolved": "app/service.py::validate"}],
                "called_by": ["tests/test_auth.py::test_login"],
            },
            "tests/test_auth.py::test_login": {
                "calls": [{"name": "login", "resolved": "app/routers/auth.py::login"}],
                "called_by": [],
            },
        }
        architecture = {
            "nodes": ["app/service.py", "app/routers/auth.py", "tests/test_auth.py"],
            "edges": [
                {"from": "app/routers/auth.py", "to": "app/service.py"},
                {"from": "tests/test_auth.py", "to": "app/routers/auth.py"},
            ],
        }
        definitions = {
            "app/service.py::validate": {"decorators": [], "line": 4},
            "app/routers/auth.py::login": {"decorators": ["post"], "line": 10},
            "tests/test_auth.py::test_login": {"decorators": [], "line": 7},
        }

        result = analyze_change_impact(
            "app/service.py::validate",
            graph,
            architecture,
            definitions,
        )

        self.assertTrue(result["found"])
        self.assertEqual(result["direct_callers"], ["app/routers/auth.py::login"])
        self.assertEqual(len(result["affected_endpoints"]), 1)
        self.assertEqual(len(result["affected_tests"]), 1)
        self.assertEqual(result["dependent_modules"][0]["depth"], 1)


class HealthScoreTests(unittest.TestCase):
    def test_score_is_deterministic_and_explains_deductions(self):
        issues = {
            "by_file": {
                "app.py": [
                    {"category": "security", "severity": "high"},
                    {"category": "quality", "severity": "low"},
                ],
            },
        }
        score = calculate_health_score(
            issues,
            {"vulnerable_count": 1},
            {"summary": {
                "layer_violations": 1,
                "circular_dependencies": 0,
                "high_coupling_modules": 0,
            }},
            {"total_dead": 2},
            {"hotspots": [{"path": "app.py", "churn": 8}]},
        )

        self.assertLess(score["overall"], 100)
        self.assertEqual(score["categories"]["security"]["score"], 90)
        self.assertTrue(score["categories"]["architecture"]["deductions"])
        self.assertIn("weights", score["methodology"])


class ConfidenceTests(unittest.TestCase):
    def test_confidence_reports_retrieval_signals(self):
        confidence = retrieval_confidence([{
            "text": "def validate(): pass",
            "metadata": {
                "retrieval_methods": ["semantic", "lexical"],
                "retrieval_score": 1,
                "exact_match": True,
            },
        }])

        self.assertGreaterEqual(confidence["score"], 50)
        self.assertIn("lexical", confidence["rationale"])


if __name__ == "__main__":
    unittest.main()
