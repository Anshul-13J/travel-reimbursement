import os
import time
from pathlib import Path

from dotenv import load_dotenv
from langchain_groq import ChatGroq

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env", override=False)

MAX_RETRIES = 3
BASE_WAIT_SECONDS = 2


def _get_groq_settings() -> tuple[str, str]:
    api_key = (os.getenv("GROQ_API_KEY") or os.getenv("XAI_API_KEY") or "").strip()
    model = (os.getenv("GROQ_MODEL") or os.getenv("GROK_MODEL") or "llama-3.3-70b-versatile").strip()
    return api_key, model


def get_groq_llm():
    api_key, model = _get_groq_settings()
    if not api_key:
        raise ValueError("GROQ_API_KEY is not set. Add it to the project .env file or your shell environment.")
    return ChatGroq(
        model=model,
        api_key=api_key,
        temperature=0.1,
    )


def invoke_with_retry(llm, messages: list, step_name: str = "call"):
    """Invoke LLM with exponential backoff retry for rate limits."""
    for attempt in range(MAX_RETRIES):
        try:
            return llm.invoke(messages)
        except Exception as exc:
            error_msg = str(exc)
            # Check for rate limit errors (429, 413, etc.)
            is_rate_limit = any(code in error_msg for code in ["429", "413", "rate_limit", "Rate limit"])
            
            if is_rate_limit and attempt < MAX_RETRIES - 1:
                wait_time = BASE_WAIT_SECONDS * (2 ** attempt)  # exponential backoff
                print(f"[workflow] Rate limited on {step_name}, retrying in {wait_time}s (attempt {attempt + 1}/{MAX_RETRIES})")
                time.sleep(wait_time)
                continue
            else:
                # Not a rate limit, or final attempt - raise immediately
                raise


def check_groq_health() -> dict:
    try:
        llm = get_groq_llm()
        llm.invoke("ping")
        api_key, model = _get_groq_settings()
        return {
            "available": bool(api_key),
            "model": model,
            "message": "Groq is reachable",
        }
    except Exception as e:
        api_key, model = _get_groq_settings()
        return {
            "available": False,
            "model": model,
            "message": str(e),
        }
