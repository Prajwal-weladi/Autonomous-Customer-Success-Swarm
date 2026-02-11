"""
Configuration management for the Policy RAG Agent.
"""
import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # Project paths
    BASE_DIR: Path = Path(__file__).parent.parent.parent
    POLICIES_DIR: Path = BASE_DIR / "policies"
    RAW_POLICIES_DIR: Path = POLICIES_DIR / "raw"
    CLEANED_POLICIES_DIR: Path = POLICIES_DIR / "cleaned"
    DATA_DIR: Path = BASE_DIR / "data"
    CHUNKS_DIR: Path = DATA_DIR / "chunks"
    EMBEDDINGS_DIR: Path = DATA_DIR / "embeddings"
    
    # Ollama settings
    OLLAMA_BASE_URL: str = Field(default="http://localhost:11434", env="OLLAMA_BASE_URL")
    GENERATION_MODEL: str = Field(default="mistral:instruct", env="GENERATION_MODEL")
    RERANKING_MODEL: str = Field(default="llama3.2", env="RERANKING_MODEL")
    EMBEDDING_MODEL: str = Field(default="mxbai-embed-large", env="EMBEDDING_MODEL")
    
    # RAG parameters
    CHUNK_SIZE: int = Field(default=800, env="CHUNK_SIZE")
    CHUNK_OVERLAP: int = Field(default=200, env="CHUNK_OVERLAP")
    TOP_K_RETRIEVAL: int = Field(default=10, env="TOP_K_RETRIEVAL")
    TOP_K_RERANK: int = Field(default=3, env="TOP_K_RERANK")
    CONVERSATION_HISTORY_LENGTH: int = Field(default=5, env="CONVERSATION_HISTORY_LENGTH")
    
    # Generation parameters
    GENERATION_TEMPERATURE: float = Field(default=0.1, env="GENERATION_TEMPERATURE")
    RERANKING_TEMPERATURE: float = Field(default=0.1, env="RERANKING_TEMPERATURE")
    GENERATION_MAX_TOKENS: int = Field(default=512, env="GENERATION_MAX_TOKENS")
    RERANKING_MAX_TOKENS: int = Field(default=10, env="RERANKING_MAX_TOKENS")
    
    # API settings
    API_HOST: str = Field(default="0.0.0.0", env="API_HOST")
    API_PORT: int = Field(default=8000, env="API_PORT")
    API_RELOAD: bool = Field(default=False, env="API_RELOAD")
    
    # Logging
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    
    # Policy domains
    POLICY_DOMAINS: list[str] = [
        "returns",
        "refund",
        "shipping",
        "cancellation",
        "warranty",
        "general"
    ]
    
    # Scraping settings
    SCRAPE_TIMEOUT: int = Field(default=30, env="SCRAPE_TIMEOUT")
    SCRAPE_DELAY: float = Field(default=1.0, env="SCRAPE_DELAY")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


# Global settings instance
settings = Settings()


def ensure_directories() -> None:
    """Create necessary directories if they don't exist."""
    directories = [
        settings.RAW_POLICIES_DIR,
        settings.CLEANED_POLICIES_DIR,
        settings.CHUNKS_DIR,
        settings.EMBEDDINGS_DIR,
    ]
    
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)


# Initialize directories on import
ensure_directories()