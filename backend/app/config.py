"""InfraGen — Application configuration."""

from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # App
    app_name: str = "InfraGen"
    app_env: str = "development"
    debug: bool = Field(default=True)

    # Database
    database_url: str = "postgresql+asyncpg://infragen:infragen_local_dev@postgres:5432/infragen"

    # Redis
    redis_url: str = "redis://redis:6379/0"

    # JWT
    jwt_secret_key: str = "change-me-in-production-use-openssl-rand-hex-32"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7

    # GitHub OAuth
    github_client_id: str = ""
    github_client_secret: str = ""
    github_redirect_uri: str = "http://localhost:3000/auth/callback/github"

    # OpenAI
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"

    # S3 / MinIO
    s3_endpoint_url: str = "http://minio:9000"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_bucket_name: str = "infragen-artifacts"

    # CORS
    backend_cors_origins: list[str] = ["http://localhost:3000"]

    # Frontend
    frontend_url: str = "http://localhost:3000"

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
