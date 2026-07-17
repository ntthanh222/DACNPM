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
import secrets
import time

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

STREAM_TICKET_TTL_SECONDS = int(os.environ.get("STREAM_TICKET_TTL_SECONDS", "60"))
_stream_tickets: Dict[str, tuple[UUID, float]] = {}


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


class StreamTicketResponse(BaseModel):
    stream_ticket: str
    expires_in: int


class PhishingCheckRequest(BaseModel):
    url: str


class PasswordStrengthRequest(BaseModel):
    password: str


# ============================================================================
# Router Setup
# ============================================================================

router = APIRouter()


def _issue_stream_ticket(user_id: UUID) -> str:
    now = time.time()
    expired = [
        ticket
        for ticket, (_, expires_at) in _stream_tickets.items()
        if expires_at <= now
    ]
    for ticket in expired:
        _stream_tickets.pop(ticket, None)

    ticket = secrets.token_urlsafe(32)
    _stream_tickets[ticket] = (user_id, now + STREAM_TICKET_TTL_SECONDS)
    return ticket


def _consume_stream_ticket(ticket: str) -> Optional[UUID]:
    ticket_data = _stream_tickets.pop(ticket, None)
    if not ticket_data:
        return None

    user_id, expires_at = ticket_data
    if expires_at <= time.time():
        return None
    return user_id


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

        # A session UUID identifies an anonymous browser session; it is not a
        # database user and must not route the request through the authenticated
        # Rasa/action path. Keep it only for validation/log correlation.
        user_id = None
        if current_user_id:
            user_id = current_user_id
            logger.info(f"Processing chat for authenticated user: {user_id}")
        else:
            # For anonymous users, validate the optional session_id but keep
            # user_id unset so the deterministic anonymous fallback is used.
            if x_session_id:
                try:
                    UUID(x_session_id)
                    logger.info(f"Processing chat for anonymous user with session: {x_session_id}")
                except ValueError:
                    logger.warning(f"Invalid session_id format: {x_session_id}")
                    raise HTTPException(status_code=400, detail="Invalid session ID format. Must be a valid UUID.")
            else:
                logger.info("Processing chat for anonymous user without a session ID")

        # Get response from chatbot service
        chatbot_service = get_chatbot_service()
        # Anonymous sessions do not have a row in public.users and therefore
        # must not be persisted to chat_history (the FK would reject them).
        response_data = await chatbot_service.process_message(
            sanitized_message,
            user_id,
            save_to_db=current_user_id is not None,
        )

        logger.info(
            "Chat processed for %s, message_length=%s",
            user_id if user_id else "anonymous",
            len(sanitized_message),
        )

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


@router.post("/chat/stream-ticket", response_model=StreamTicketResponse)
@limiter.limit("30/minute")
async def create_stream_ticket(
    request: Request,
    current_user_id: UUID = Depends(require_current_user_id),
):
    """Issue a short-lived ticket for EventSource without putting the JWT in the URL."""
    ticket = _issue_stream_ticket(current_user_id)
    return StreamTicketResponse(
        stream_ticket=ticket,
        expires_in=STREAM_TICKET_TTL_SECONDS,
    )


@router.get("/chat/stream")
@limiter.limit("30/minute")
async def chat_stream(
    request: Request,
    message: str,
    token: Optional[str] = None,
    stream_ticket: Optional[str] = None,
    session_id: Optional[str] = None,
    current_user_id: Optional[UUID] = Depends(get_optional_user_id),
    x_session_id: Optional[str] = Header(None)
):
    """
    Process chat message with Server-Sent Events streaming.

    Streams the response token by token for real-time user feedback.
    Includes DDoS protection via SSE connection limits.
    """
    if not current_user_id and stream_ticket:
        ticket_user_id = _consume_stream_ticket(stream_ticket)
        if ticket_user_id:
            current_user_id = ticket_user_id
            logger.info("Authenticated streaming client via short-lived ticket")
        else:
            logger.warning("Invalid or expired stream ticket")
            raise HTTPException(status_code=401, detail="Invalid or expired stream ticket.")

    # Legacy fallback for older clients. New frontend code uses stream_ticket.
    if not current_user_id and token:
        try:
            from backend.api.auth import verify_token
            token_data = verify_token(token)
            if token_data and token_data.user_id:
                current_user_id = UUID(token_data.user_id)
                logger.info("Authenticated streaming client via legacy query token")
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
                response_data = await chatbot_service.process_message(
                    sanitized_message,
                    user_id,
                    save_to_db=current_user_id is not None,
                )
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
