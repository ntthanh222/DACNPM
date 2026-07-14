"""Safe development defaults used when environment settings are incomplete."""

from .settings import Settings


def build_fallback_settings() -> Settings:
    return Settings(
        supabase_url="",
        supabase_key="",
        supabase_service_role_key="",
        api_host="0.0.0.0",
        api_port=8000,
        api_debug=False,
        cors_origins="http://localhost:3000,http://localhost:8000",
        environment="development",
        rasa_server_host="localhost",
        rasa_server_port=5005,
        rasa_action_server_port=5055,
        rasa_websocket_url="ws://localhost:5005/websocket",
    )
