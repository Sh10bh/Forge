# utils/llm_client.py
import os
import json
import time
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

# add all your groq keys in .env as GROQ_API_KEY_1 through GROQ_API_KEY_6
API_KEYS = [
    os.getenv("GROQ_API_KEY_1"),
    os.getenv("GROQ_API_KEY_2"),
    os.getenv("GROQ_API_KEY_3"),
    os.getenv("GROQ_API_KEY_4"),
    os.getenv("GROQ_API_KEY_5"),
    os.getenv("GROQ_API_KEY_6"),
]

# remove None values in case some keys aren't set yet
API_KEYS = [k for k in API_KEYS if k]

if not API_KEYS:
    raise ValueError("No Groq API keys found. Add GROQ_API_KEY_1 to .env")

current_key_index = 0


def call_llm(system_prompt: str, user_prompt: str, temperature: float = 0.0) -> str:
    """
    Call the LLM with automatic key rotation on rate limit errors.
    Tries every available key before giving up.
    """
    global current_key_index

    last_error = None

    for attempt in range(len(API_KEYS)):
        try:
            client = Groq(api_key=API_KEYS[current_key_index])
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user",   "content": user_prompt}
                ],
                temperature=temperature,
                max_tokens=4096,
            )
            return response.choices[0].message.content

        except Exception as e:
            error_str = str(e)
            last_error = e

            if "429" in error_str or "rate_limit" in error_str.lower():
                print(f"  Key {current_key_index + 1} exhausted, switching...")
                current_key_index = (current_key_index + 1) % len(API_KEYS)
                time.sleep(1)  # small pause before trying next key
                continue

            # non-rate-limit error — don't retry
            raise e

    raise Exception(
        f"All {len(API_KEYS)} API keys exhausted. "
        f"Last error: {last_error}. "
        f"Please add more keys or wait for daily reset."
    )


def call_llm_json(system_prompt: str, user_prompt: str) -> dict:
    """
    Call the LLM and parse the response as JSON.
    Strips markdown code fences before parsing.
    """
    raw = call_llm(system_prompt, user_prompt)
    raw = raw.strip()

    # strip markdown fences if present
    if raw.startswith("```json"):
        raw = raw[7:]
    if raw.startswith("```"):
        raw = raw[3:]
    if raw.endswith("```"):
        raw = raw[:-3]

    return json.loads(raw.strip())