from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime
from uuid import UUID
from typing import Optional
from backend.repositories.stats import (
    get_vulnerability_distribution,
    get_chat_statistics,
    get_system_health_stats
)
from backend.database.models import VulnerabilityStats, SystemHealth
from backend.api.deps import get_current_user_id, get_optional_user_id, require_current_user_id

router = APIRouter()


@router.get("/vulnerabilities", response_model=VulnerabilityStats)
def get_vulnerability_stats(
    current_user_id: UUID = Depends(require_current_user_id)
):
    """
    Get vulnerability type distribution from chat history
    Analyzes intent/entity patterns from user conversations

    Returns vulnerability statistics including:
    - injection: SQL injection, command injection, LDAP injection
    - cross_site_scripting: XSS vulnerabilities
    - authentication: Authentication, authorization, session management
    - remote_code_execution: RCE vulnerabilities
    - memory_corruption: Buffer overflow, memory corruption
    - csrf: Cross-site request forgery
    - other: Other vulnerability types
    """
    try:
        distribution = get_vulnerability_distribution()
        distribution['last_updated'] = datetime.now()
        return distribution
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch vulnerability stats: {str(e)}")


@router.get("/chat/statistics")
def get_chat_statistics_endpoint(
    limit: int = 1000,
    current_user_id: UUID = Depends(require_current_user_id)
):
    """
    Get aggregate statistics from chat history

    Parameters:
    - limit: Number of recent messages to analyze (default: 1000)

    Returns:
    - total_conversations: Total number of chat messages
    - unique_intents: Number of unique intents detected
    - top_intents: Most common intents with counts
    - average_message_length: Average user message length
    """
    try:
        return get_chat_statistics(limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch chat statistics: {str(e)}")


@router.get("/system/health", response_model=SystemHealth)
def get_system_health_endpoint(
    current_user_id: UUID = Depends(require_current_user_id)
):
    """
    Get system health metrics

    Returns:
    - database_status: Database connection status (healthy/error)
    - database_latency_ms: Database query latency in milliseconds
    - rasa_status: Rasa service status (unknown/healthy/error)
    - timestamp: Current timestamp
    """
    try:
        return get_system_health_stats()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch system health: {str(e)}")
