import os
import unittest
from unittest.mock import Mock, patch

from app.config import LLM_MODEL_NAME
from app.llm.client import OPENAI_CHAT_COMPLETIONS_URL, ask_llm, ask_llm_json


class LlmClientTests(unittest.TestCase):
    @patch("app.llm.client.requests.post")
    def test_ask_llm_uses_openai_chat_completions(self, post):
        response = Mock()
        response.json.return_value = {
            "choices": [{"message": {"content": "Repository answer"}}]
        }
        post.return_value = response

        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            result = ask_llm("What does this do?", context="def example(): pass")

        self.assertEqual(result, "Repository answer")
        response.raise_for_status.assert_called_once_with()
        args, kwargs = post.call_args
        self.assertEqual(args[0], OPENAI_CHAT_COMPLETIONS_URL)
        self.assertEqual(kwargs["headers"]["Authorization"], "Bearer test-key")
        self.assertEqual(kwargs["json"]["model"], LLM_MODEL_NAME)
        self.assertEqual(kwargs["json"]["messages"][0]["role"], "system")

    @patch("app.llm.client.requests.post")
    def test_ask_llm_json_requests_and_parses_json_mode(self, post):
        response = Mock()
        response.json.return_value = {
            "choices": [{"message": {"content": '{"purpose": "test"}'}}]
        }
        post.return_value = response

        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            result = ask_llm_json("Summarize this repository")

        self.assertEqual(result, {"purpose": "test"})
        self.assertEqual(
            post.call_args.kwargs["json"]["response_format"],
            {"type": "json_object"},
        )

    @patch("app.llm.client.requests.post")
    def test_missing_api_key_fails_before_request(self, post):
        with patch("builtins.print"), patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(
                RuntimeError,
                "OPENAI_API_KEY is not configured",
            ):
                ask_llm("Hello")

        post.assert_not_called()


if __name__ == "__main__":
    unittest.main()
