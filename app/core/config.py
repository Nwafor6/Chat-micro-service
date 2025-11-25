"""Configuration module for application settings using Pydantic."""

from functools import lru_cache
from typing import List, Literal, Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    app_name: str = "Global Chat Service"
    app_description: str = "Real-time chat microservice with JWT authentication"
    app_version: str = "1.0.0"
    api_prefix: str = "/api/v1"
    base_url: str = "http://localhost:8080"

    env: str = "development"
    debug: bool = True

    # Database Configuration
    db_type: Literal["postgres", "mysql"] = "postgres"
    database_url: Optional[str] = None

    # Redis (for WebSocket session management and caching)
    redis_url: str = "redis://localhost:6379"
    redis_db: int = 0
    redis_password: str = ""

    # JWT Authentication (should match main server settings)
    jwt_secret_key: str  # Secret key for JWT authentication
    jwt_algorithm: str = "HS256"
    jwt_token_ttl: int = 10080
    crypto_algorithm: str = "argon2"

    # WebSocket Settings
    ws_heartbeat_interval: int = 30
    ws_connection_timeout: int = 300
    max_connections_per_user: int = 5

    # Chat Settings
    max_message_length: int = 2000
    message_history_limit: int = 100
    chat_room_member_limit: int = 100
    file_upload_max_size: int = 10485760  # 10MB

    # AWS S3 (for file uploads in chat)
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_default_region: str = "us-east-1"
    aws_bucket: str = "bildup-chat-files"
    aws_private_bucket: str = "bildup-chat-private"
    aws_region: str = ""

    # Email
    mail_driver: str = "smtp"
    mail_host: str = "smtp.gmail.com"
    mail_port: int = 465
    mail_username: str = ""
    mail_password: str = ""
    mail_from_address: str = ""
    mailgun_domain: str = ""
    mailgun_secret: str = ""

    # CORS Settings
    # allowed_origins: str = (
    #     "http://localhost:8080,http://localhost:8000,http://localhost:3001,https://bildup.ai"
    # )
    # allowed_methods: str = "GET,POST,PUT,DELETE,OPTIONS"
    # allowed_headers: str = "*"

    # Rate Limiting
    rate_limit_messages_per_minute: int = 60
    rate_limit_connections_per_minute: int = 10

    # Logging
    log_level: str = "INFO"
    log_file: str = "storage/logs/chat-service.log"

    # Health Check
    health_check_interval: int = 60

    # Admin Settings
    admin_email: str = "admin@bildup.ai"

    @property
    def allowed_origins_list(self) -> List[str]:
        """Convert comma-separated origins to list"""
        hosts = [origin.strip() for origin in self.allowed_origins.split(",")]
        print(f"These are the hosts: {hosts}")
        return hosts

    @property
    def allowed_methods_list(self) -> List[str]:
        """Convert comma-separated methods to list"""
        methods = [method.strip() for method in self.allowed_methods.split(",")]
        print(f"These are the methods: {methods}")
        return methods

    def get_database_url(self) -> str:
        """Get the database URL, either from env var or construct from components"""
        if not self.database_url:
            raise ValueError(f"Unsupported database type: {self.db_type}")
        return self.database_url

    class Config:
        """config files settings."""

        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

    @classmethod
    def get_base_url(cls) -> str:
        _settings = cls()
        return f"{_settings.base_url}{_settings.api_prefix}"


@lru_cache
def get_settings() -> Settings:
    """Retrieve the application settings."""
    return Settings()


# Initialize the settings object
settings: Settings = get_settings()
