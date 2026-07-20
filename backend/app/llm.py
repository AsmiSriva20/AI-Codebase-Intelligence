import os
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

client = Groq(
    api_key=os.getenv("GROQ_API_KEY")
)

def ask_llm(prompt: str, context: str = None) -> str:
    """
    Sends a prompt (and optional context) to Groq's LLaMA 3.3 model.
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

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"❌ Groq API Error: {e}")
        raise e


if __name__ == "__main__":
    test_prompt = "What does the function create_app do?"
    test_context = "Function: create_app\nCreates and configures the Flask application instance."
    
    print("--- Single Prompt Test ---")
    print(ask_llm(test_prompt))
    
    print("\n--- Context Prompt Test ---")
    print(ask_llm(test_prompt, context=test_context))