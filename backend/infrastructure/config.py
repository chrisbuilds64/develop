"""
Application Configuration

Zentrale Stelle für alle Einstellungen und Environment-Variablen.
"""
import os
from dataclasses import dataclass


@dataclass
class Config:
    """Application configuration"""

    # Environment
    ENV: str = os.getenv("ENV", "development")
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"

    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT: str = os.getenv("LOG_FORMAT", "json")  # json | human

    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./dev.db")

    # Auth
    CLERK_SECRET_KEY: str = os.getenv("CLERK_SECRET_KEY", "")
    SUPERTOKENS_CONNECTION_URI: str = os.getenv("SUPERTOKENS_CONNECTION_URI", "")

    # AI
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")


# Singleton instance
config = Config()
