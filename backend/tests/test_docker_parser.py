from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from app.analysis.architecture import generate_architecture
from app.analysis.chunker import chunk_file
from app.analysis.indexer import build_index
from app.parsers import language_for_path, parser_for_path


class DockerParserTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)

    def parse(self, name, source):
        path = Path(self.directory.name, name)
        path.write_text(source, encoding="utf-8")
        return parser_for_path(path).analyze_file(path)

    def test_filename_detection_and_existing_languages(self):
        for name in ("Dockerfile", "Dockerfile.dev", "api.Dockerfile", "Containerfile", "C:\\repo\\Dockerfile.prod"):
            self.assertEqual(language_for_path(name), "dockerfile")
        for name in ("compose.yaml", "compose.override.yml", "docker-compose.yml", "docker-compose.prod.yaml"):
            self.assertEqual(language_for_path(name), "docker-compose")
        self.assertEqual(language_for_path("src/APP.PY"), "python")
        self.assertIsNone(language_for_path("settings.yaml"))
        self.assertIsNone(language_for_path("Dockerfile-notes.md"))

    def test_multistage_dependencies_exclude_internal_stages_and_scratch(self):
        result = self.parse("Dockerfile", """# syntax=docker/dockerfile:1
ARG BASE=python:3.11-slim
FROM --platform=$BUILDPLATFORM ${BASE} AS builder
RUN pip install requests
FROM builder AS test
FROM scratch
COPY --from=builder /app /app
COPY --from=0 /other /other
COPY --from=busybox:1.36 /bin/busybox /bin/busybox
""")
        self.assertEqual(result["imports"], ["${BASE}", "busybox:1.36"])
        self.assertEqual([stage["name"] for stage in result["stages"]], ["builder", "test", None])
        self.assertEqual(result["functions"], [])
        self.assertEqual(result["graph"], {})
        index = build_index([{"path": "Dockerfile", "analysis": result}])
        self.assertEqual(index["imports"]["${BASE}"], ["Dockerfile"])

    def test_continuations_comments_and_source_lines(self):
        source = "FROM alpine\nRUN apk add \\\n  # build tools\n  git \\\n  curl\nCMD [\"sh\"]\n"
        result = self.parse("Dockerfile", source)
        run = result["instructions"][1]
        self.assertEqual(run["start_line"], 2)
        self.assertEqual(run["end_line"], 5)
        self.assertIn("curl", run["value"])
        self.assertNotIn("build tools", run["value"])
        chunks = chunk_file("Dockerfile", result)
        run_chunk = next(chunk for chunk in chunks if chunk["metadata"]["name"].startswith("RUN "))
        self.assertEqual(run_chunk["metadata"]["start_line"], 2)
        self.assertEqual(run_chunk["text"], "\n".join(source.splitlines()[1:5]))

    def test_escape_directive_and_lowercase_instructions(self):
        result = self.parse("Dockerfile.windows", "# escape=`\nfrom base AS build\nRUN echo one `\n  && echo two\n")
        self.assertEqual(len(result["instructions"]), 2)
        self.assertEqual(result["instructions"][1]["end_line"], 4)
        self.assertEqual(result["imports"], ["base"])

    def test_heredoc_body_is_not_parsed_as_instructions(self):
        result = self.parse("Dockerfile", "FROM alpine\nCOPY <<'EOF' /config\nFROM not-an-image\nEOF\nRUN <<-SCRIPT\n\techo hello\n\tSCRIPT\nCMD [\"sh\"]\n")
        self.assertEqual(result["imports"], ["alpine"])
        self.assertEqual([item["instruction"] for item in result["instructions"]], ["FROM", "COPY", "RUN", "CMD"])
        self.assertEqual(result["instructions"][1]["end_line"], 4)
        self.assertEqual(result["instructions"][2]["end_line"], 7)

    def test_compose_services_anchors_build_and_dependency_forms(self):
        result = self.parse("compose.yaml", """x-defaults: &defaults
  image: python:3.11-slim
services:
  api:
    <<: *defaults
    build:
      context: ./backend
      dockerfile: Dockerfile.dev
    depends_on:
      db:
        condition: service_healthy
    ports: ["8000:8000"]
  worker:
    image: python:3.11-slim
    depends_on: [api]
  db:
    image: postgres:16-alpine
volumes:
  data: {}
""")
        self.assertEqual(result["imports"], ["python:3.11-slim", "postgres:16-alpine"])
        self.assertEqual(result["services"][0]["build"]["dockerfile"], "Dockerfile.dev")
        self.assertEqual(result["services"][0]["depends_on"], ["db"])
        self.assertEqual(result["services"][1]["depends_on"], ["api"])
        blocks = result["blocks"]
        self.assertEqual(blocks[0]["start_line"], 4)
        self.assertNotIn("worker:", blocks[0]["code"])
        chunks = chunk_file("compose.yaml", result)
        self.assertEqual(len([c for c in chunks if c["metadata"]["type"] == "docker_service"]), 3)
        self.assertTrue(any("x-defaults" in c["text"] for c in chunks))

    def test_quoted_heredoc_text_does_not_swallow_following_instructions(self):
        result = self.parse("Dockerfile", "FROM alpine\nRUN echo '<<EOF'\nRUN cat <<<word\nCMD [\"sh\"]\n")
        self.assertEqual([item["instruction"] for item in result["instructions"]], ["FROM", "RUN", "RUN", "CMD"])

    def test_invalid_yaml_and_non_service_documents_remain_searchable(self):
        for source in ("services: [broken", "- list\n- item", "services: null", "services: {api: null}"):
            with self.subTest(source=source):
                result = self.parse("compose.yml", source)
                self.assertEqual(result["services"], [])
                self.assertTrue(chunk_file("compose.yml", result))

    def test_binary_dockerfile_is_rejected(self):
        with self.assertRaises(ValueError):
            self.parse("Dockerfile", "FROM alpine\x00")

    def test_docker_files_appear_in_architecture_with_folder_scope(self):
        files = [
            {"path": "backend/Dockerfile", "extension": "", "full_path": "unused"},
            {"path": "compose.yaml", "extension": ".yaml", "full_path": "unused"},
        ]
        self.assertEqual(generate_architecture(files)["nodes"], ["backend/Dockerfile", "compose.yaml"])
        self.assertEqual(generate_architecture(files, folder="backend")["nodes"], ["backend/Dockerfile"])

    def test_state_file_info_and_dependencies_use_filename_dispatch(self):
        with patch.dict("os.environ", {
            "DATABASE_URL": "postgresql://test:test@localhost/test",
            "QDRANT_URL": "http://localhost:6333", "QDRANT_API_KEY": "",
            "OPENAI_API_KEY": "test",
        }):
            from app import state
            from app.analysis.file_info import get_file_info
            from app.analysis.dependency import get_dependencies
        path = Path(self.directory.name, "Dockerfile.dev")
        path.write_text("FROM python:3.11-slim\n", encoding="utf-8")
        self.assertEqual(state.parse_file(path)["imports"], ["python:3.11-slim"])
        info = get_file_info(path, "Dockerfile.dev")
        self.assertEqual(info["language"], "dockerfile")
        self.assertEqual(info["stages"][0]["base_image"], "python:3.11-slim")
        with patch.object(state, "REPO_PATH", self.directory.name):
            self.assertEqual(get_dependencies("Dockerfile.dev"), ["python:3.11-slim"])


if __name__ == "__main__":
    unittest.main()
