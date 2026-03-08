"""
KrishiMandal Platform - Configuration
Loads environment variables and provides configuration constants.
"""
import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    # ── AWS (only used when USE_DUMMY_DATA=false) ────────────────────────
    AWS_REGION: str = os.getenv("AWS_REGION", "ap-south-1")
    AWS_ACCESS_KEY_ID: str = os.getenv("AWS_ACCESS_KEY_ID", "")
    AWS_SECRET_ACCESS_KEY: str = os.getenv("AWS_SECRET_ACCESS_KEY", "")

    # ── Bedrock (only used when USE_DUMMY_DATA=false) ────────────────────
    BEDROCK_MODEL_ID: str = os.getenv("BEDROCK_MODEL_ID", "anthropic.claude-sonnet-4-5-20250514")
    BEDROCK_EMBEDDING_MODEL_ID: str = os.getenv("BEDROCK_EMBEDDING_MODEL_ID", "amazon.nova-embed-multimodal-v1:0")
    BEDROCK_GUARDRAIL_ID: str = os.getenv("BEDROCK_GUARDRAIL_ID", "")
    BEDROCK_GUARDRAIL_VERSION: str = os.getenv("BEDROCK_GUARDRAIL_VERSION", "DRAFT")
    BEDROCK_KNOWLEDGE_BASE_ID: str = os.getenv("BEDROCK_KNOWLEDGE_BASE_ID", "")

    # ── Groq LLM (always active — used in both dummy & production) ──────
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL_ID: str = os.getenv("GROQ_MODEL_ID", "llama-3.3-70b-versatile")
    GROQ_MAX_TOKENS: int = int(os.getenv("GROQ_MAX_TOKENS", "2048"))
    GROQ_TEMPERATURE: float = float(os.getenv("GROQ_TEMPERATURE", "0.3"))

    # ── Google Gemini Embeddings (always active) ────────────────────────
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_EMBEDDING_MODEL: str = os.getenv("GEMINI_EMBEDDING_MODEL", "text-embedding-004")

    # ── Pinecone Vector DB (always active) ──────────────────────────────
    PINECONE_API_KEY: str = os.getenv("PINECONE_API_KEY", "")
    PINECONE_INDEX_NAME: str = os.getenv("PINECONE_INDEX_NAME", "krishimandal-knowledge")
    PINECONE_ENVIRONMENT: str = os.getenv("PINECONE_ENVIRONMENT", "us-east-1")
    PINECONE_CLOUD: str = os.getenv("PINECONE_CLOUD", "aws")
    PINECONE_METRIC: str = os.getenv("PINECONE_METRIC", "cosine")
    PINECONE_DIMENSION: int = int(os.getenv("PINECONE_DIMENSION", "768"))

    # ── Sarvam AI ────────────────────────────────────────────────────────
    SARVAM_AI_API_KEY: str = os.getenv("SARVAM_AI_API_KEY", "")
    SARVAM_AI_BASE_URL: str = os.getenv("SARVAM_AI_BASE_URL", "https://api.sarvam.ai/v1")

    # ── Twilio ───────────────────────────────────────────────────────────
    TWILIO_ACCOUNT_SID: str = os.getenv("TWILIO_ACCOUNT_SID", "")
    TWILIO_AUTH_TOKEN: str = os.getenv("TWILIO_AUTH_TOKEN", "")
    TWILIO_PHONE_NUMBER: str = os.getenv("TWILIO_PHONE_NUMBER", "")
    TWILIO_WHATSAPP_NUMBER: str = os.getenv("TWILIO_WHATSAPP_NUMBER", "")

    # ── External APIs ────────────────────────────────────────────────────
    OPENWEATHERMAP_API_KEY: str = os.getenv("OPENWEATHERMAP_API_KEY", "")
    ENAM_API_BASE_URL: str = os.getenv("ENAM_API_BASE_URL", "https://enam.gov.in/web/dashboard/trade-data")
    AGRISTACK_API_KEY: str = os.getenv("AGRISTACK_API_KEY", "")
    AGRISTACK_BASE_URL: str = os.getenv("AGRISTACK_BASE_URL", "https://api.agristack.gov.in/v1")

    # ── Real Data Toggles ─────────────────────────────────────────────
    USE_REAL_WEATHER: bool = os.getenv("USE_REAL_WEATHER", "false").lower() == "true"
    CEDA_API_BASE_URL: str = os.getenv("CEDA_API_BASE_URL", "https://agmarknet.ceda.ashoka.edu.in")
    AGMARKNET_SCRAPE_ENABLED: bool = os.getenv("AGMARKNET_SCRAPE_ENABLED", "false").lower() == "true"

    # ── Scheduler ──────────────────────────────────────────────────────
    SCHEDULER_ENABLED: bool = os.getenv("SCHEDULER_ENABLED", "false").lower() == "true"

    # ── Database ───────────────────────────────────────────────────────
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./krishimandal.db")

    # ── Auth & Rate Limiting ──────────────────────────────────────────
    API_KEY_ENABLED: bool = os.getenv("API_KEY_ENABLED", "false").lower() == "true"
    API_KEYS: str = os.getenv("API_KEYS", "krishimandal-dev-key")
    RATE_LIMIT_PER_MINUTE: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "100"))
    CORS_ORIGINS: str = os.getenv("CORS_ORIGINS", "*")

    # ── File Uploads ─────────────────────────────────────────────────
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "./uploads")
    MAX_UPLOAD_SIZE_MB: int = int(os.getenv("MAX_UPLOAD_SIZE_MB", "10"))

    # ── Application ─────────────────────────────────────────────────────
    APP_ENV: str = os.getenv("APP_ENV", "development")
    APP_PORT: int = int(os.getenv("APP_PORT", "8000"))
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    # Dummy data mode — when True, agents return mock domain data
    # (farm profiles, prices, schemes) but LLM / Embeddings / RAG
    # still use real APIs (Groq, Gemini, Pinecone)
    USE_DUMMY_DATA: bool = os.getenv("USE_DUMMY_DATA", "true").lower() == "true"


settings = Settings()
