import os

from dotenv import load_dotenv

load_dotenv(override=True)

class Settings:
    APP_NAME = "Ichiba Merchant Support Assistant"
    GROQ_API_KEY = os.getenv("GROQ_API_KEY", "demo-key")
    GROQ_API_BASE = os.getenv("GROQ_API_BASE", "https://api.groq.com/openai/v1")
    MODEL_NAME = os.getenv("MODEL_NAME", "llama-3.3-70b-versatile")
    SYNTHESIZER_TEMPERATURE = float(os.getenv("SYNTHESIZER_TEMPERATURE", "0.3"))
    SYNTHESIZER_MAX_TOKENS = int(os.getenv("SYNTHESIZER_MAX_TOKENS", "600"))
    PINECONE_API_KEY = os.getenv("PINECONE_API_KEY", "")
    PINECONE_ENV = os.getenv("PINECONE_ENV", "us-east-1")
    PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "ichiba-support-docs")
    COHERE_API_KEY = os.getenv("COHERE_API_KEY", "")
    COHERE_EMBED_MODEL = os.getenv("COHERE_EMBED_MODEL", "embed-english-v3.0")
    DATABASE_URL = os.getenv(
        "DATABASE_URL", "postgresql://ichiba:ichiba_dev_pw@localhost:5432/ichiba"
    )
    LISTING_API_BASE_URL = os.getenv("LISTING_API_BASE_URL", "http://127.0.0.1:8100")
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    ENV = os.getenv("ENV", "dev")

settings = Settings()