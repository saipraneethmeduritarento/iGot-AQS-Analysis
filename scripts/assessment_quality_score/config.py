"""
Configuration module for Assessment Quality Score system.

Uses Pydantic BaseSettings for environment variable management.
"""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables or .env file."""
    
    # Google Cloud / Vertex AI Configuration
    google_project_id: str  # Maps to GOOGLE_PROJECT_ID
    google_project_location: str = "us-central1"  # Maps to GOOGLE_PROJECT_LOCATION
    
    # Gemini Model Configuration
    gemini_model_name: str = "gemini-2.0-flash"  # Maps to GEMINI_MODEL_NAME
    
    # Data paths
    data_dir: Optional[str] = None
    prompts_dir: Optional[str] = None
    output_dir: Optional[str] = None
    
    class Config:
        """Pydantic configuration."""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"  # Ignore extra environment variables


# Global settings instance
settings = Settings()

