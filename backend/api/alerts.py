from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4
from fastapi import APIRouter, Depends, HTTPException

from backend.database.models import SecurityAlert, SecurityAlertCreate
from backend.database.connection import supabase, supabase_admin, DATABASE_AVAILABLE
from backend.api.deps import require_current_user_id, require_admin_or_analyst
from backend.services.audit_service import log_audit_event

router = APIRouter()

# Fallback memory storage
_in_memory_alerts: Dict[str, Dict[str, Any]] = {}

def get_alerts_client():
    return supabase_admin if supabase_admin else supabase

@router.get("/", response_model=List[SecurityAlert])
async def list_alerts(
    status: Optional[str] = None,
    severity: Optional[str] = None,
    user_id: UUID = Depends(require_admin_or_analyst)
):
    client = get_alerts_client()
    if DATABASE_AVAILABLE and client:
        try:
            query = client.table("security_alerts").select("*")
            if status:
                query = query.eq("status", status)
            if severity:
                query = query.eq("severity", severity)
            
            response = query.order("created_at", desc=True).execute()
            return [SecurityAlert(**r) for r in (response.data or [])]
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Database query failed: {e}")

    # Local fallback
    local_list = [SecurityAlert(**v) for v in _in_memory_alerts.values()]
    if status:
        local_list = [a for a in local_list if a.status == status]
    if severity:
        local_list = [a for a in local_list if a.severity == severity]
    return sorted(local_list, key=lambda x: x.created_at, reverse=True)

@router.post("/", response_model=SecurityAlert)
async def create_alert(
    alert_in: SecurityAlertCreate,
    user_id: UUID = Depends(require_admin_or_analyst)
):
    client = get_alerts_client()
    alert_id = uuid4()
    now = datetime.now().isoformat()
    
    alert_data = alert_in.model_dump()
    alert_data.update({
        "id": str(alert_id),
        "created_at": now,
        "resolved_at": None
    })

    if DATABASE_AVAILABLE and client:
        try:
            response = client.table("security_alerts").insert(alert_data).execute()
            if response.data:
                return SecurityAlert(**response.data[0])
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Database insert failed: {e}")

    # Local fallback
    _in_memory_alerts[str(alert_id)] = alert_data
    return SecurityAlert(**alert_data)

@router.put("/{id}/acknowledge", response_model=SecurityAlert)
async def acknowledge_alert(
    id: UUID,
    user_id: UUID = Depends(require_admin_or_analyst)
):
    client = get_alerts_client()
    update_data = {"status": "acknowledged"}

    if DATABASE_AVAILABLE and client:
        try:
            response = client.table("security_alerts").update(update_data).eq("id", str(id)).execute()
            if response.data:
                log_audit_event(str(user_id), "acknowledge_alert", "security_alert", str(id), "success")
                return SecurityAlert(**response.data[0])
            raise HTTPException(status_code=404, detail="Alert not found")
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Database update failed: {e}")

    # Local fallback
    if str(id) in _in_memory_alerts:
        _in_memory_alerts[str(id)].update(update_data)
        log_audit_event(str(user_id), "acknowledge_alert", "security_alert", str(id), "success")
        return SecurityAlert(**_in_memory_alerts[str(id)])
    raise HTTPException(status_code=404, detail="Alert not found")

@router.put("/{id}/resolve", response_model=SecurityAlert)
async def resolve_alert(
    id: UUID,
    user_id: UUID = Depends(require_admin_or_analyst)
):
    client = get_alerts_client()
    update_data = {
        "status": "resolved",
        "resolved_at": datetime.now().isoformat()
    }

    if DATABASE_AVAILABLE and client:
        try:
            response = client.table("security_alerts").update(update_data).eq("id", str(id)).execute()
            if response.data:
                log_audit_event(str(user_id), "resolve_alert", "security_alert", str(id), "success")
                return SecurityAlert(**response.data[0])
            raise HTTPException(status_code=404, detail="Alert not found")
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Database update failed: {e}")

    # Local fallback
    if str(id) in _in_memory_alerts:
        _in_memory_alerts[str(id)].update(update_data)
        log_audit_event(str(user_id), "resolve_alert", "security_alert", str(id), "success")
        return SecurityAlert(**_in_memory_alerts[str(id)])
    raise HTTPException(status_code=404, detail="Alert not found")
