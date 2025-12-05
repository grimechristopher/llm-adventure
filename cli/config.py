"""
Configuration management for CLI app
"""
from pydantic import BaseModel, Field
from dotenv import load_dotenv
import os


class Config(BaseModel):
    """Application configuration loaded from .env file"""

    api_base_url: str = Field(default="http://127.0.0.1:5000")
    api_timeout: int = Field(default=30)
    stream_chunk_display: bool = Field(default=True)
    color_theme: str = Field(default="default")

    @classmethod
    def load(cls) -> "Config":
        """Load configuration from .env file with sensible defaults"""
        load_dotenv()
        return cls(
            api_base_url=os.getenv("API_BASE_URL", "http://127.0.0.1:5000"),
            api_timeout=int(os.getenv("API_TIMEOUT", "30")),
            stream_chunk_display=os.getenv("STREAM_CHUNK_DISPLAY", "true").lower()
            == "true",
            color_theme=os.getenv("COLOR_THEME", "default"),
        )
