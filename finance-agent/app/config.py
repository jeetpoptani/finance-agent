import os
from dotenv import load_dotenv


load_dotenv()


class Settings:
    groq_api_key = os.getenv("GROQ_API_KEY", "")
    groq_model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    groq_base_url = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
    llm_timeout_seconds = float(os.getenv("LLM_TIMEOUT_SECONDS", "12"))


settings = Settings()
