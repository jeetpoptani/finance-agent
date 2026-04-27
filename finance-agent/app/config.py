import os
from dotenv import load_dotenv

load_dotenv()


def _clean_groq_url(url: str) -> str:
    """
    Strip accidental duplicate /openai/v1 segments.
    e.g. https://api.groq.com/openai/v1/openai/v1 → https://api.groq.com/openai/v1
    """
    url = url.rstrip("/")
    # If the path appears twice, keep only up to the first occurrence
    marker = "/openai/v1"
    first = url.find(marker)
    if first != -1:
        second = url.find(marker, first + len(marker))
        if second != -1:
            url = url[:second]
    return url


class Settings:
    groq_api_key = os.getenv("GROQ_API_KEY", "")
    groq_model   = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    groq_base_url = _clean_groq_url(
        os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
    )
    llm_timeout_seconds = float(os.getenv("LLM_TIMEOUT_SECONDS", "12"))


settings = Settings()