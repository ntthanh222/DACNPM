import os
import logging
from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import field_validator, Field, model_validator, AliasChoices
from typing import Optional

# Configure logging
logger = logging.getLogger(__name__)

# Get the directory where this file is located
# Note: since this file is now in backend/config/settings.py, parent is backend/config and parent.parent is backend/
BASE_DIR = Path(__file__).parent.parent.absolute()
PROJECT_ROOT = BASE_DIR.parent
ENV_FILE = PROJECT_ROOT / ".env"

class Settings(BaseSettings):
    # Project Paths
    BASE_DIR: Path = BASE_DIR
    PROJECT_ROOT: Path = PROJECT_ROOT

    # Supabase Configuration
    supabase_url: str
    supabase_key: str
    supabase_service_role_key: str
    supabase_secret: str = ""
    supabase_publishable_key: str = ""

    # JWT Configuration
    jwt_secret: str = "change-this-to-a-secure-random-key-in-production"
    access_token_expire_minutes: int = 1440

    # Database Connection (for direct PostgreSQL connections)
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "postgres"
    db_user: str = "postgres"
    db_password: str = ""

    # API Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_debug: bool = os.getenv("API_DEBUG", "False").lower() == "true"

    # CORS Configuration
    cors_origins: str = "http://localhost:3000,http://localhost:8000"

    # Official Server-Side Role Mapping
    # Cấu hình chính thức để phân quyền super_admin mà không cần bypass constraint database
    super_admin_ids: str = Field(
        default="", 
        description="Comma-separated UUIDs for super_admin users"
    )

    def get_super_admin_ids(self) -> list[str]:
        if not self.super_admin_ids:
            return []
        return [uid.strip() for uid in self.super_admin_ids.split(',')]

    def get_cors_origins(self) -> list[str]:
        """Parse CORS origins from comma-separated string"""
        if isinstance(self.cors_origins, str):
            origins = [origin.strip() for origin in self.cors_origins.split(",")]

            # Add common development origins if in development mode
            if self.is_development():
                origins.append("http://localhost:3000")
                origins.append("http://localhost:8000")
                origins.append("http://localhost:5005")
                origins.append("http://127.0.0.1:3000")
                origins.append("http://127.0.0.1:8000")
                origins.append("http://127.0.0.1:5005")

            return list(set(origins))  # Remove duplicates
        return self.cors_origins

    # External APIs - loaded from .env with warnings for missing keys
    virustotal_api_key: str = Field(default="", description="VirusTotal API key for URL scanning")
    nist_nvd_api_key: str = Field(default="", description="NIST NVD API key for CVE lookup")

    # LLM Configuration
    llm_provider: str = Field(default="gemini", description="LLM provider: gemini, openai, claude")
    llm_model: str = Field(default="gemini-2.5-flash", description="Model name")
    llm_api_key: str = Field(
        default="",
        description="LLM API key",
        validation_alias=AliasChoices("LLM_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY"),
    )
    llm_max_tokens: int = Field(default=2048, description="Maximum tokens in response")
    llm_temperature: float = Field(default=0.7, description="Response creativity (0-1)")
    llm_memory_window: int = Field(default=5, description="Number of recent messages to include")

    # Rasa Configuration
    rasa_server_host: str = "localhost"
    rasa_server_port: int = 5005
    rasa_action_server_port: int = 5055
    rasa_websocket_url: str = "ws://localhost:5005/websocket"
    rasa_url: Optional[str] = None

    @model_validator(mode='after')
    def parse_rasa_url(self) -> 'Settings':
        if self.rasa_url:
            try:
                from urllib.parse import urlparse
                parsed = urlparse(self.rasa_url)
                if parsed.hostname:
                    self.rasa_server_host = parsed.hostname
                if parsed.port:
                    self.rasa_server_port = parsed.port
                self.rasa_websocket_url = f"ws://{self.rasa_server_host}:{self.rasa_server_port}/websocket"
            except Exception as e:
                logger.warning(f"Failed to parse rasa_url {self.rasa_url}: {e}")
        return self

    # Environment Configuration
    environment: str = "development"

    @field_validator('virustotal_api_key', 'nist_nvd_api_key', 'llm_api_key')
    @classmethod
    def validate_api_keys(cls, v: str, info) -> str:
        """Validate API key format - warn but don't fail for optional keys"""
        if v and not isinstance(v, str):
            raise ValueError('API key must be a string')
        # Basic validation: API keys should not be too short
        if v and len(v) < 10:
            logger.warning(f'API key appears to be invalid (too short): {info.field_name}')
        return v

    @field_validator('environment')
    @classmethod
    def validate_environment(cls, v: str) -> str:
        """Validate environment setting"""
        # Also map APP_ENV to environment if it's set in the env
        v = os.getenv("APP_ENV", v)
        allowed = ['development', 'production', 'staging', 'test', 'qa']
        if v not in allowed:
            raise ValueError(f'Environment must be one of {allowed}')
        return v

    def is_production(self) -> bool:
        """Check if running in production"""
        return self.environment == 'production'

    def is_development(self) -> bool:
        return self.environment == 'development'

    def is_test(self) -> bool:
        return self.environment == 'test'

    def is_qa(self) -> bool:
        return self.environment == 'qa'

    @model_validator(mode='after')
    def validate_security(self) -> 'Settings':
        if self.environment == 'production':
            if self.jwt_secret == "change-this-to-a-secure-random-key-in-production":
                raise ValueError("Must set a secure JWT_SECRET in production!")
            if self.api_debug:
                raise ValueError("API_DEBUG must be false in production!")
        
        # Prevent destructive QA/test operations on production URLs.
        if self.environment in {'test', 'qa'}:
            if 'aivvorhfsxjpfeqpcxxh' in self.supabase_url: # The known production project ID
                raise ValueError("Test/QA environment must not connect to the production Supabase database.")
        return self

    model_config = {
        "env_file": [
            str(ENV_FILE),
            str(BASE_DIR / ".env"),
            str(PROJECT_ROOT / ".env")
        ],  # Check backend directory and project root
        "env_file_encoding": "utf-8",
        "extra": "allow"
    }

@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Load settings once and fall back to safe development defaults."""
    try:
        return Settings()
    except Exception as exc:
        logger.warning("Could not load environment settings; using development defaults: %s", exc)
        from .fallback import build_fallback_settings

        return build_fallback_settings()


# Compatibility export for existing modules; new code should call get_settings().
settings = get_settings()
