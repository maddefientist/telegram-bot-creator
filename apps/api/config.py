"""Application configuration using pydantic-settings."""
from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    app_name: str = "Telegram Bot Creator"
    app_base_url: str = "http://localhost:3000"
    api_base_url: str = "http://localhost:8000"
    debug: bool = False
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    # Database
    database_url: str = Field(..., alias="DATABASE_URL")

    # Redis
    redis_url: str = Field(..., alias="REDIS_URL")

    # Auth
    jwt_secret: str = Field(..., min_length=32)
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 24
    csrf_secret: str = Field(..., min_length=32)

    # Encryption
    encryption_key: str = Field(..., description="Fernet key for encrypting sensitive data")

    # OpenRouter
    openrouter_api_key: str = Field(...)
    openrouter_model: str = "anthropic/claude-3.5-sonnet"
    openrouter_base_url: str = "https://openrouter.ai/api/v1"

    # Solana
    solana_rpc_url: str = Field(...)
    solana_treasury_address: str = Field(...)

    # Pricing
    pricing_min_sol: float = 0.01
    pricing_max_sol: float = 10.0
    default_price_sol: float = 0.1
    grace_days: int = 3

    # Rate limiting
    ai_generation_rate_limit: int = 10  # per hour per user
    api_rate_limit: int = 100  # per minute per IP

    # Bot containers
    bot_memory_limit: str = "256m"
    bot_cpu_limit: str = "0.5"
    runner_shared_secret: str = Field(..., min_length=32)
    runner_image: str = "botcreator-runner:latest"
    docker_network: str = "botcreator_default"
    docker_host: str | None = None  # e.g., tcp://docker-proxy:2375

    # Invoice settings
    invoice_expiry_hours: int = 24

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        if not v.startswith(("postgresql", "postgres")):
            raise ValueError("Only PostgreSQL databases are supported")
        return v

    @field_validator("solana_treasury_address")
    @classmethod
    def validate_treasury_address(cls, v: str) -> str:
        import base58
        try:
            decoded = base58.b58decode(v)
            if len(decoded) != 32:
                raise ValueError("Invalid Solana address length")
        except Exception as e:
            raise ValueError(f"Invalid Solana address: {e}")
        return v

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
