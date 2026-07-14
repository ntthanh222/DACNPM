"""
Chatbot API for CyberSec Assistant

Thin API wrapper endpoints for chatbot functionality.
Business logic is handled by the service layer.

SECURITY NOTICE: This API layer handles user input validation and
sanitization before passing to services.
"""

from fastapi import APIRouter, HTTPException, Header, Request, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any
import logging
from uuid import UUID, uuid4
import html
import os
import asyncio
import json

from backend.api.deps import get_optional_user_id, require_current_user_id, require_admin
from backend.services.chatbot_service import get_chatbot_service
from backend.utils.rate_limiter import check_sse_limit, release_sse_connection, get_sse_stats
from slowapi.util import get_remote_address
from slowapi import Limiter

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize rate limiter for chatbot endpoints
limiter = Limiter(key_func=get_remote_address)


def sanitize_html(text: str) -> str:
    """
    Sanitize user input to prevent XSS attacks.
    Escapes HTML special characters but allows safe markdown formatting.
    """
    if not text:
        return text

    # Escape HTML special characters
    return html.escape(text, quote=False)


# ============================================================================
# Pydantic Models
# ============================================================================

class ChatRequest(BaseModel):
    message: str
    context: Optional[Dict[str, Any]] = None


class ChatResponse(BaseModel):
    response: str
    intent: Optional[str] = None
    confidence: Optional[float] = None
    suggested_actions: Optional[list] = None


class PhishingCheckRequest(BaseModel):
    url: str


class PasswordStrengthRequest(BaseModel):
    password: str


# ============================================================================
# Router Setup
# ============================================================================

router = APIRouter()


# ============================================================================
# Chatbot Endpoints
# ============================================================================

@router.post("/chat", response_model=ChatResponse)
@limiter.limit("30/minute")
async def chat(
    request: Request,
    payload: ChatRequest,
    current_user_id: Optional[UUID] = Depends(get_optional_user_id),
    x_session_id: Optional[str] = Header(None)
):
    """Process chat message using service layer with per-user conversation history"""
    try:
        # Sanitize user input to prevent XSS
        sanitized_message = sanitize_html(payload.message)

        # Use authenticated user ID if available, otherwise use session_id
        user_id = None
        if current_user_id:
            user_id = current_user_id
            logger.info(f"Processing chat for authenticated user: {user_id}")
        else:
            # For anonymous users, use session_id (generate if missing)
            if x_session_id:
                try:
                    user_id = UUID(x_session_id)
                    logger.info(f"Processing chat for anonymous user with session: {user_id}")
                except ValueError:
                    logger.warning(f"Invalid session_id format: {x_session_id}")
                    raise HTTPException(status_code=400, detail="Invalid session ID format. Must be a valid UUID.")
            else:
                # Generate new session UUID for anonymous users
                user_id = uuid4()
                logger.info(f"Generated new session ID for anonymous user: {user_id}")

        # Get response from chatbot service
        chatbot_service = get_chatbot_service()
        response_data = await chatbot_service.process_message(sanitized_message, user_id)

        logger.info(f"Chat message: '{sanitized_message}', User: {user_id if user_id else 'anonymous'}")

        return ChatResponse(
            response=response_data['response'],
            intent=response_data.get('intent'),
            confidence=response_data.get('confidence'),
            suggested_actions=response_data.get('suggested_actions')
        )
    except ValueError as val_err:
        logger.warning(f"Validation error in chat: {val_err}")
        raise HTTPException(status_code=400, detail=str(val_err))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chat processing error: {e}")
        raise HTTPException(status_code=500, detail="Chat processing failed")


@router.get("/chat/stream")
@limiter.limit("30/minute")
async def chat_stream(
    request: Request,
    message: str,
    token: Optional[str] = None,
    session_id: Optional[str] = None,
    current_user_id: Optional[UUID] = Depends(get_optional_user_id),
    x_session_id: Optional[str] = Header(None)
):
    """
    Process chat message with Server-Sent Events streaming.

    Streams the response token by token for real-time user feedback.
    Includes DDoS protection via SSE connection limits.
    """
    # Fallback authentication/session via query parameters for EventSource compatibility
    if not current_user_id and token:
        try:
            from backend.api.auth import verify_token
            token_data = verify_token(token)
            if token_data and token_data.user_id:
                current_user_id = UUID(token_data.user_id)
                logger.info(f"Authenticated streaming client via query token: {current_user_id}")
        except Exception as e:
            logger.warning(f"Failed to authenticate streaming client via query token: {e}")

    if not x_session_id and session_id:
        x_session_id = session_id

    # Determine user ID (convert to string for connection tracking)
    user_id_str = None
    user_id = None
    if current_user_id:
        user_id = current_user_id
        user_id_str = str(current_user_id)
        logger.info(f"Processing streaming chat for authenticated user: {user_id}")
    else:
        if x_session_id:
            try:
                user_id = UUID(x_session_id)
                user_id_str = x_session_id
                logger.info(f"Processing streaming chat for anonymous user with session: {user_id}")
            except ValueError:
                logger.warning(f"Invalid session_id format: {x_session_id}")
                raise HTTPException(status_code=400, detail="Invalid session ID format.")
        else:
            user_id = uuid4()
            user_id_str = str(user_id)
            logger.info(f"Generated new session ID for anonymous streaming user: {user_id}")

    try:
        # SECURITY: Check SSE connection limit before starting stream
        await check_sse_limit(user_id_str)
        logger.debug(f"✅ SSE connection approved for user {user_id_str}")

        # Sanitize user input
        sanitized_message = sanitize_html(message)

        async def generate_stream():
            """Generate SSE stream with chunks of the response"""
            try:
                # Get response from chatbot service
                chatbot_service = get_chatbot_service()
                response_data = await chatbot_service.process_message(sanitized_message, user_id)
                response_text = response_data.get('response', '')

                # Send metadata first
                metadata = {
                    "type": "metadata",
                    "intent": response_data.get('intent'),
                    "confidence": response_data.get('confidence'),
                    "suggested_actions": response_data.get('suggested_actions', [])
                }
                yield f"data: {json.dumps(metadata)}\n\n"

                # Stream the response in chunks
                # Configure chunk size and delay via environment variables
                chunk_size = int(os.environ.get('STREAM_CHUNK_SIZE', 50))  # Default: 50 characters per chunk
                chunk_delay = float(os.environ.get('STREAM_CHUNK_DELAY', 0.01))  # Default: 10ms delay

                for i in range(0, len(response_text), chunk_size):
                    chunk = response_text[i:i+chunk_size]
                    chunk_data = {
                        "type": "chunk",
                        "content": chunk
                    }
                    yield f"data: {json.dumps(chunk_data)}\n\n"

                    # Configurable delay for typing effect (can be set to 0 for instant delivery)
                    if chunk_delay > 0:
                        await asyncio.sleep(chunk_delay)

                # Send completion signal
                complete_data = {
                    "type": "complete",
                    "full_response": response_text
                }
                yield f"data: {json.dumps(complete_data)}\n\n"

            except Exception as e:
                logger.error(f"Error in stream generation: {e}")
                error_data = {
                    "type": "error",
                    "message": str(e)
                }
                yield f"data: {json.dumps(error_data)}\n\n"
            finally:
                # SECURITY: Always release SSE connection on stream completion
                await release_sse_connection(user_id_str)
                logger.debug(f"🔽 SSE connection released for user {user_id_str}")

        return StreamingResponse(
            generate_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"  # Disable Nginx buffering
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        # Ensure connection is released on any error
        await release_sse_connection(user_id_str)
        logger.error(f"Error in streaming chat: {e}")
        raise HTTPException(status_code=500, detail="Failed to process streaming request")


@router.post("/reset")
async def reset_conversation(current_user_id: UUID = Depends(require_current_user_id)):
    """Reset conversation history for authenticated user by deleting their chat history from database"""
    try:
        # Delete user's chat history from database
        from backend.repositories.chat_history import delete_user_chat_history
        deleted_count = delete_user_chat_history(current_user_id)

        logger.info(f"Reset conversation history for user {current_user_id}, deleted {deleted_count} messages")
        return {
            "status": "success",
            "message": f"Conversation reset successfully. Deleted {deleted_count} messages.",
            "deleted_count": deleted_count
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to reset conversation: {e}")
        raise HTTPException(status_code=500, detail="Failed to reset conversation")


# ============================================================================
# Security Tools Endpoints
# ============================================================================

@router.post("/phishing-check")
@limiter.limit("20/minute")
async def check_phishing_url(
    request: Request,
    payload: PhishingCheckRequest,
    current_user_id: Optional[UUID] = Depends(get_optional_user_id)
):
    """
    Check if URL might be phishing using VirusTotal API

    Uses shared URL scanning utility for consistent behavior
    Falls back to basic pattern matching if API unavailable
    Now uses async httpx for non-blocking API calls.
    """
    try:
        from backend.utils.url_scanner import check_phishing_url_async as scan_url
        from backend.repositories.security_scans import create_security_scan
        from backend.database.models import SecurityScanCreate

        # Validate URL format and perform phishing check (async)
        result = await scan_url(payload.url)

        # Log URL scan to database for authenticated users
        if current_user_id:
            try:
                scan_record = SecurityScanCreate(
                    user_id=current_user_id,
                    scan_type="url_scan",
                    target=payload.url,
                    scan_result={
                        "risk_score": result.get("risk_score", 0),
                        "severity": result.get("severity", "unknown"),
                        "stats": result.get("stats", {})
                    },
                    status="completed"
                )
                create_security_scan(scan_record)
            except Exception as log_error:
                logger.warning(f"Failed to log URL scan: {log_error}")

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Phishing check error: {e}")
        raise HTTPException(status_code=500, detail="Phishing check failed")


@router.post("/password-strength")
@limiter.limit("20/minute")
async def check_password_strength(
    request: Request,
    payload: PasswordStrengthRequest,
    current_user_id: Optional[UUID] = Depends(get_optional_user_id)
):
    """
    Check password strength using shared password checking utility

    Combines entropy calculation with HaveIBeenPwned API (optional)
    Now uses async httpx for non-blocking API calls.
    """
    try:
        from backend.utils.password_checker import check_password_strength_async as check_pwd
        from backend.repositories.security_scans import create_security_scan
        from backend.database.models import SecurityScanCreate

        # Use shared password checking utility (async)
        result = await check_pwd(payload.password)

        # Log password scan (with password redacted) for security audit (only for authenticated users)
        if current_user_id:
            try:
                scan_record = SecurityScanCreate(
                    user_id=current_user_id,
                    scan_type="password_check",
                    target="PASSWORD_REDACTED",
                    scan_result={"strength": result.get("strength", "unknown"), "score": result.get("score", 0)},
                    status="completed"
                )
                create_security_scan(scan_record)
            except Exception as log_error:
                logger.warning(f"Failed to log password scan: {log_error}")

        return result

    except Exception as e:
        logger.error(f"Password strength check error: {e}")
        raise HTTPException(status_code=500, detail="Password strength check failed")


# ============================================================================
# Admin/Monitoring Endpoints
# ============================================================================

@router.get("/chat/sse-stats")
async def get_sse_connection_stats(admin_id: UUID = Depends(require_admin)):
    """
    Get SSE connection statistics (admin only).

    Requires admin role. Provides monitoring for DDoS protection systems.
    """
    try:
        stats = get_sse_stats()
        logger.info(f"Admin {admin_id} requested SSE stats: {stats}")
        return stats
    except Exception as e:
        logger.error(f"Error getting SSE stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve SSE statistics")
