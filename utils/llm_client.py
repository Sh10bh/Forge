# utils/llm_client.py
import os
import json
from groq import Groq
from dotenv import load_dotenv

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def call_llm(system_prompt: str, user_prompt: str, temperature: float = 0.0) -> str:
    """Call the LLM and return raw text response."""
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

def call_llm_json(system_prompt: str, user_prompt: str) -> dict:
    """Call the LLM and parse the result as JSON."""
    raw = call_llm(system_prompt, user_prompt)
    raw = raw.strip()
    if raw.startswith("```json"):
        raw = raw[7:]
    if raw.startswith("```"):
        raw = raw[3:]
    if raw.endswith("```"):
        raw = raw[:-3]
    return json.loads(raw.strip())