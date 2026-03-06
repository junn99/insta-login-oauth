"""Configuration management for urlinsta."""

import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Application configuration from environment variables."""

    INSTAGRAM_APP_ID: str = os.getenv("INSTAGRAM_APP_ID", "")
    INSTAGRAM_APP_SECRET: str = os.getenv("INSTAGRAM_APP_SECRET", "")
    OAUTH_REDIRECT_URI: str = os.getenv("OAUTH_REDIRECT_URI", "")
    CONTACT_EMAIL: str = os.getenv("CONTACT_EMAIL", "")

    # Supabase
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")

    # Instagram API
    INSTAGRAM_API_BASE_URL: str = "https://graph.instagram.com"
    INSTAGRAM_OAUTH_URL: str = "https://api.instagram.com"

    # Rate limiting
    RATE_LIMIT_REQUESTS: int = 180  # Conservative limit (Instagram allows 200/hour)
    RATE_LIMIT_WINDOW: int = 3600  # 1 hour in seconds

    @classmethod
    def validate(cls) -> list[str]:
        """Validate required configuration. Returns list of missing keys."""
        required = [
            "INSTAGRAM_APP_ID",
            "INSTAGRAM_APP_SECRET",
            "OAUTH_REDIRECT_URI",
            "CONTACT_EMAIL",
            "SUPABASE_URL",
            "SUPABASE_KEY",
        ]
        missing = [key for key in required if not getattr(cls, key)]
        return missing


config = Config()
