import logging
from datetime import datetime
from typing import Dict, Any, Optional
from uuid import UUID
from backend.database.connection import supabase, supabase_admin, DATABASE_AVAILABLE

logger = logging.getLogger(__name__)

# Cache/log fallback
_in_memory_audit_logs = []

def log_audit_event(
    actor: str,
    action: str,
    resource_type: str,
    resource_id: Optional[str] = None,
    result: str = "success",
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    request_id: Optional[str] = None,
    trace_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Log an audit event to the database with a robust fallback to logging system.
    """
    import uuid
    event_data = {
        "id": str(uuid.uuid4()),
        "actor": actor,
        "action": action,
        "resource_type": resource_type,
        "resource_id": str(resource_id) if resource_id else None,
        "timestamp": datetime.now().isoformat(),
        "result": result,
        "ip_address": ip_address,
        "user_agent": user_agent,
        "request_id": request_id,
        "trace_id": trace_id,
        "metadata": metadata or {}
    }

    # Redact metadata of sensitive keys if any
    for sensitive_key in ["password", "token", "secret", "key"]:
        if sensitive_key in event_data["metadata"]:
            event_data["metadata"][sensitive_key] = "[REDACTED]"

    logger.info(f"AUDIT_LOG: {action} by {actor} on {resource_type}/{resource_id} -> {result}")

    client = supabase_admin if supabase_admin else supabase
    if DATABASE_AVAILABLE and client:
        try:
            response = client.table("audit_logs").insert(event_data).execute()
            if response.data:
                return response.data[0]
        except Exception as e:
            logger.error(f"Failed to persist audit log: {e}")

    # Fallback to memory list
    _in_memory_audit_logs.append(event_data)
    if len(_in_memory_audit_logs) > 1000:
        _in_memory_audit_logs.pop(0)
    return event_data

def get_audit_logs(limit: int = 100, offset: int = 0) -> list:
    """Retrieve audit logs."""
    client = supabase_admin if supabase_admin else supabase
    if DATABASE_AVAILABLE and client:
        try:
            response = client.table("audit_logs").select("*").order("timestamp", desc=True).range(offset, offset + limit - 1).execute()
            return response.data
        except Exception as e:
            logger.error(f"Failed to query audit logs: {e}")
    
    # Fallback to sorting memory logs
    sorted_logs = sorted(_in_memory_audit_logs, key=lambda x: x["timestamp"], reverse=True)
    return sorted_logs[offset:offset + limit]
