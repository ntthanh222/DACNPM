"""
Rasa Client Service for CyberSec Assistant

Handles all communication with Rasa NLU server.
Provides interface for message processing and intent detection.

SECURITY NOTICE: This service handles user input and must sanitize
all data before sending to Rasa server.
"""

import httpx
import logging
from typing import Dict, Any, Optional
from uuid import UUID
from backend.core.config import settings

logger = logging.getLogger(__name__)


class RasaClient:
    """Client for Rasa NLU server communication"""

    def __init__(self):
        self.rasa_url = f"http://{settings.rasa_server_host}:{settings.rasa_server_port}"
        self.timeout = 10.0

    async def send_message(self, message: str, sender_id: str) -> Optional[str]:
        """
        Send message to Rasa and get response text.

        Args:
            message: User message to process
            sender_id: User/session identifier for conversation tracking

        Returns:
            Rasa response text or None if communication fails
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.rasa_url}/webhooks/rest/webhook",
                    json={
                        "sender": sender_id,
                        "message": message
                    }
                )

                if response.status_code == 200:
                    data = response.json()
                    if data and len(data) > 0:
                        return data[0].get('text', 'Xin lỗi, tôi không hiểu.')
                    else:
                        logger.warning("Empty response from Rasa")
                        return None
                else:
                    logger.error(f"Rasa returned HTTP {response.status_code}")
                    return None

        except httpx.TimeoutException:
            logger.error(f"Timeout connecting to Rasa server at {self.rasa_url}")
            return None
        except httpx.RequestError as e:
            logger.error(f"Failed to connect to Rasa: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error communicating with Rasa: {e}")
            return None

    async def get_intent(self, message: str) -> Dict[str, Any]:
        """
        Get intent classification from Rasa for a message.

        Args:
            message: User message to classify

        Returns:
            Dictionary with intent name, confidence, and entities
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.rasa_url}/model/parse",
                    json={"text": message}
                )

                if response.status_code == 200:
                    data = response.json()
                    return {
                        'intent': data.get('intent', {}).get('name', 'nlu_fallback'),
                        'confidence': data.get('intent', {}).get('confidence', 0.0),
                        'entities': data.get('entities', [])
                    }
                else:
                    logger.error(f"Intent parsing failed with HTTP {response.status_code}")
                    return {'intent': 'nlu_fallback', 'confidence': 0.0, 'entities': []}

        except Exception as e:
            logger.error(f"Error getting intent from Rasa: {e}")
            return {'intent': 'nlu_fallback', 'confidence': 0.0, 'entities': []}

    def is_available(self) -> bool:
        """
        Check if Rasa server is available (basic connectivity check).

        Returns:
            True if Rasa server is reachable, False otherwise
        """
        try:
            import socket
            host = settings.rasa_server_host
            port = settings.rasa_server_port
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex((host, port))
            sock.close()
            return result == 0
        except Exception as e:
            logger.warning(f"Rasa availability check failed: {e}")
            return False


# Global Rasa client instance
_rasa_client: Optional[RasaClient] = None


def get_rasa_client() -> RasaClient:
    """Get global Rasa client instance (singleton pattern)"""
    global _rasa_client
    if _rasa_client is None:
        _rasa_client = RasaClient()
        logger.info("Rasa client initialized")
    return _rasa_client
