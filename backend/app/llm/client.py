import json
import os
from dotenv import load_dotenv
from groq import Groq

from app.config import LLM_MODEL_NAME, LLM_TEMPERATURE

load_dotenv()

client = Groq(
    api_key=os.getenv("GROQ_API_KEY")
)

def ask_llm(prompt: str, context: str = None, temperature: float = LLM_TEMPERATURE, response_format: dict = None) -> str:
    """
    Sends a prompt (and optional context) to Groq's LLaMA 3.3 model.

    temperature defaults low (0.2) — every use case here is "answer factually
    from given code/context," never creative writing. response_format is
    Groq/OpenAI-compatible, e.g. {"type": "json_object"} for structured output.
    """
    messages = []

    if context:
        messages.append({
            "role": "system",
            "content": f"You are an expert AI Codebase Assistant. Answer using the retrieved code context below:\n\n{context}"
        })

    messages.append({
        "role": "user",
        "content": prompt
    })

    kwargs = {"model": LLM_MODEL_NAME, "messages": messages, "temperature": temperature}
    if response_format:
        kwargs["response_format"] = response_format

    try:
        response = client.chat.completions.create(**kwargs)
        return response.choices[0].message.content
    except Exception as e:
        print(f"Groq API Error: {e}")
        raise e


def ask_llm_json(prompt: str, context: str = None, temperature: float = LLM_TEMPERATURE) -> dict:
    """
    Like ask_llm, but requests Groq's JSON mode and parses the result. Falls
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