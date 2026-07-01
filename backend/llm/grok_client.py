import os

from langchain_openai import ChatOpenAI


def get_grok_llm():
    api_key = os.getenv("XAI_API_KEY", "")
    model = os.getenv("GROK_MODEL", "grok-3-mini")
    return ChatOpenAI(
        model=model,
        api_key=api_key,
        base_url="https://api.x.ai/v1",
        temperature=0.1,
    )


def check_grok_health() -> dict:
    try:
        llm = get_grok_llm()
        llm.invoke("ping")
        return {
            "available": True,
            "model": os.getenv("GROK_MODEL", "grok-3-mini"),
            "message": "Grok is reachable",
        }
    except Exception as e:
        return {
            "available": False,
            "model": os.getenv("GROK_MODEL", "grok-3-mini"),
            "message": str(e),
        }
