import os
import sys
from dotenv import load_dotenv
import ollama
from google import genai

load_dotenv()

GOOGLE_MODELS = {"gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-3-flash-preview"}


def prompt_model(model: str, prompt: str) -> str:
    try:
        if model in GOOGLE_MODELS:
            api_key = os.getenv("GOOGLE_API_KEY")
            if not api_key:
                return "[Config Error] GOOGLE_API_KEY not found in environment"

            client = genai.Client(api_key=api_key)
            response = client.models.generate_content(
                model=model,
                contents=prompt,
            )
            return response.text

        else:
            response = ollama.chat(
                model=model,
                messages=[{"role": "user", "content": prompt}],
            )
            return response["message"]["content"]

    except Exception as e:
        return f"[Error] {type(e).__name__}: {e}"


def main():
    if len(sys.argv) >= 3:
        model = sys.argv[1]
        prompt = " ".join(sys.argv[2:])
    else:
        model = "llama3.1"
        prompt = "tell me one malaysian joke"

    result = prompt_model(model, prompt)
    print("\n--- RESPONSE ---\n")
    print(result)


if __name__ == "__main__":
    main()