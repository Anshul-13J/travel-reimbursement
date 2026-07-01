try:
    from .groq_client import check_groq_health, get_groq_llm
except ImportError:  # pragma: no cover - fallback for direct script execution
    from backend.llm.groq_client import check_groq_health, get_groq_llm


def get_grok_llm():
    return get_groq_llm()


def check_grok_health() -> dict:
    return check_groq_health()
