import json
import os

import requests
from dotenv import load_dotenv

from app.config import LLM_MODEL_NAME, LLM_REQUEST_TIMEOUT_SECONDS, LLM_TEMPERATURE

load_dotenv()

OPENAI_CHAT_COMPLETIONS_URL = "https://api.openai.com/v1/chat/completions"


def _api_key():
    key = os.environ.get("OPENAI_API_KEY") or os.environ.get("OpenAI_API_KEY")
    if not key:
        raise RuntimeError("OPENAI_API_KEY is not configured")
    return key


def ask_llm(prompt: str, context: str = None, temperature: float = LLM_TEMPERATURE, response_format: dict = None) -> str:
    """
    Send a prompt (and optional repository context) to OpenAI.

    temperature defaults low (0.2) — every use case here is "answer factually
    from given code/context," never creative writing. response_format is
    the Chat Completions format, e.g. {"type": "json_object"} for JSON mode.
    """
    messages = []

    if context:
        messages.append({
            "role": "system",
            "content": (
                "You are an expert AI Codebase Assistant. Answer only from the "
                "retrieved repository context. Cite factual code claims with the "
                "provided [file:line-line] labels. If the evidence is insufficient, "
                f"say so clearly.\n\n{context}"
            ),
        })

    messages.append({
        "role": "user",
        "content": prompt
    })

    payload = {"model": LLM_MODEL_NAME, "messages": messages, "temperature": temperature}
    if response_format:
        payload["response_format"] = response_format

    try:
        response = requests.post(
            OPENAI_CHAT_COMPLETIONS_URL,
            headers={
                "Authorization": f"Bearer {_api_key()}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=LLM_REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        if not content:
            raise RuntimeError("OpenAI returned an empty chat response")
        return content
    except Exception as e:
        print(f"OpenAI API Error: {e}")
        raise


def ask_llm_json(prompt: str, context: str = None, temperature: float = LLM_TEMPERATURE) -> dict:
    """
    Like ask_llm, but requests OpenAI's JSON mode and parses the result. Falls
    back to {"raw": <text>} if the model didn't return valid JSON — rare with
    response_format set, but not guaranteed, and callers/the frontend should
    treat "raw" as a signal to render plain text instead of structured fields.
    """
    text = ask_llm(prompt, context=context, temperature=temperature, response_format={"type": "json_object"})
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return {"raw": text}


if __name__ == "__main__":
    test_prompt = "What does the function create_app do?"
    test_context = "Function: create_app\nCreates and configures the Flask application instance."
    
    print("--- Single Prompt Test ---")
    print(ask_llm(test_prompt))
    
    print("\n--- Context Prompt Test ---")
    print(ask_llm(test_prompt, context=test_context))
