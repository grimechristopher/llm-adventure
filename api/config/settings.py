# config/settings.py
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import SecretStr, Field

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False
    )

    # Database
    database_url: str = Field(..., description="PostgreSQL connection URL")
    db_pool_size: int = Field(default=20)
    db_max_overflow: int = Field(default=10)

    # Application
    secret_key: SecretStr = Field(..., description="Secret key for sessions")
    log_level: str = Field(default="INFO")
    log_to_console: bool = Field(default=True)
    environment: str = Field(default="development")

    # WebSocket
    ws_max_connections: int = Field(default=1000)
    ws_heartbeat_interval: int = Field(default=30)
    ws_message_max_size: int = Field(default=1048576)

    # Security
    allowed_origins: str = Field(default="http://localhost:3000")
    rate_limit_per_minute: int = Field(default=60)
    max_checkpoint_age_days: int = Field(default=30)

    # LLM Providers (optional)
    azure_openai_api_key: SecretStr | None = Field(default=None)
    azure_openai_endpoint: str | None = Field(default=None)
    azure_openai_api_version: str | None = Field(default=None)
    openai_api_key: SecretStr | None = Field(default=None)
    lm_studio_base_url: str | None = Field(default=None)

settings = Settings()
