"""
Configuration settings for the LLM Document Processing System
"""

import os
from typing import Optional


class Settings:
    # LLM Provider Configuration
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "gemini")  # "openai" or "gemini"

    # OpenAI Configuration
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")

    # Google Gemini Configuration
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")

    # Database Configuration
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./documents.db")
    VECTOR_DB_PATH: str = os.getenv("VECTOR_DB_PATH", "./vector_db")

    # Application Configuration
    APP_HOST: str = os.getenv("APP_HOST", "0.0.0.0")
    APP_PORT: int = int(os.getenv("APP_PORT", "8000"))
    DEBUG: bool = os.getenv("DEBUG", "True").lower() == "true"

    # LLM Configuration
    LLM_MODEL: str = os.getenv("LLM_MODEL", "gemini-1.5-flash")  # Default to Gemini
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "models/text-embedding-004")  # Gemini embedding
    MAX_TOKENS: int = int(os.getenv("MAX_TOKENS", "2000"))
    TEMPERATURE: float = float(os.getenv("TEMPERATURE", "0.1"))
    
    # Document Processing
    MAX_CHUNK_SIZE: int = int(os.getenv("MAX_CHUNK_SIZE", "1000"))
    CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", "200"))
    MAX_DOCUMENTS: int = int(os.getenv("MAX_DOCUMENTS", "1000"))
    
    # Search Configuration
    SIMILARITY_THRESHOLD: float = float(os.getenv("SIMILARITY_THRESHOLD", "0.7"))
    MAX_RESULTS: int = int(os.getenv("MAX_RESULTS", "10"))
    
    def __init__(self):
        # Load from .env file if it exists
        if os.path.exists('.env'):
            from dotenv import load_dotenv
            load_dotenv()
            # Reload the environment variables
            self.LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini")
            self.OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
            self.GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
            self.DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./documents.db")
            self.VECTOR_DB_PATH = os.getenv("VECTOR_DB_PATH", "./vector_db")
            self.APP_HOST = os.getenv("APP_HOST", "0.0.0.0")
            self.APP_PORT = int(os.getenv("APP_PORT", "8000"))
            self.DEBUG = os.getenv("DEBUG", "True").lower() == "true"
            self.LLM_MODEL = os.getenv("LLM_MODEL", "gemini-1.5-flash")
            self.EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "models/text-embedding-004")
            self.MAX_TOKENS = int(os.getenv("MAX_TOKENS", "2000"))
            self.TEMPERATURE = float(os.getenv("TEMPERATURE", "0.1"))
            self.MAX_CHUNK_SIZE = int(os.getenv("MAX_CHUNK_SIZE", "1000"))
            self.CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "200"))
            self.MAX_DOCUMENTS = int(os.getenv("MAX_DOCUMENTS", "1000"))
            self.SIMILARITY_THRESHOLD = float(os.getenv("SIMILARITY_THRESHOLD", "0.7"))
            self.MAX_RESULTS = int(os.getenv("MAX_RESULTS", "10"))


settings = Settings()
