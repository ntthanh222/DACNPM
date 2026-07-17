from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4
from fastapi import APIRouter, Depends, HTTPException

from backend.database.models import Incident, IncidentCreate, IncidentUpdate
from backend.database.connection import supabase, supabase_admin, DATABASE_AVAILABLE
from backend.api.deps import require_current_user_id, require_admin_or_analyst
from backend.services.audit_service import log_audit_event

router = APIRouter()

# Fallback memory storage
_in_memory_incidents: Dict[str, Dict[str, Any]] = {}

def get_incidents_client():
    return supabase_admin if supabase_admin else supabase

@router.get("/", response_model=List[Incident])
async def list_incidents(
    status: Optional[str] = None,
    severity: Optional[str] = None,
    user_id: UUID = Depends(require_admin_or_analyst)
):
    client = get_incidents_client()
    if DATABASE_AVAILABLE and client:
        try:
            query = client.table("incidents").select("*")
            if status:
                query = query.eq("status", status)
            if severity:
                query = query.eq("severity", severity)
            response = query.order("created_at", desc=True).execute()
            return [Incident(**r) for r in (response.data or [])]
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Database query failed: {e}")

    # Fallback
    local_list = [Incident(**v) for v in _in_memory_incidents.values()]
    if status:
        local_list = [i for i in local_list if i.status == status]
    if severity:
        local_list = [i for i in local_list if i.severity == severity]
    return sorted(local_list, key=lambda x: x.created_at, reverse=True)

@router.post("/", response_model=Incident)
async def create_incident(
    incident_in: IncidentCreate,
    user_id: UUID = Depends(require_admin_or_analyst)
):
    client = get_incidents_client()
    incident_id = uuid4()
    now = datetime.now().isoformat()
    
    incident_data = incident_in.model_dump()
    # Add initial timeline event
    initial_event = {
        "timestamp": now,
        "event": "Incident created",
        "actor": str(user_id)
    }
    incident_data.update({
        "id": str(incident_id),
        "owner_id": str(user_id) if not incident_data.get("owner_id") else str(incident_data["owner_id"]),
        "timeline": [initial_event],
        "created_at": now,
        "updated_at": now,
        "closed_at": None
    })

    if DATABASE_AVAILABLE and client:
        try:
            response = client.table("incidents").insert(incident_data).execute()
            if response.data:
                log_audit_event(str(user_id), "create_incident", "incident", str(incident_id), "success")
                return Incident(**response.data[0])
        except Exception as e:
            log_audit_event(str(user_id), "create_incident", "incident", str(incident_id), "failure", metadata={"error": str(e)})
            raise HTTPException(status_code=500, detail=f"Database insert failed: {e}")

    # Local fallback
    _in_memory_incidents[str(incident_id)] = incident_data
    log_audit_event(str(user_id), "create_incident", "incident", str(incident_id), "success", metadata={"storage": "in-memory"})
    return Incident(**incident_data)

@router.get("/{id}", response_model=Incident)
async def get_incident(
    id: UUID,
    user_id: UUID = Depends(require_admin_or_analyst)
):
    client = get_incidents_client()
    if DATABASE_AVAILABLE and client:
        try:
            response = client.table("incidents").select("*").eq("id", str(id)).execute()
            if response.data:
                return Incident(**response.data[0])
            raise HTTPException(status_code=404, detail="Incident not found")
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Database query failed: {e}")

    # Local fallback
    if str(id) in _in_memory_incidents:
        return Incident(**_in_memory_incidents[str(id)])
    raise HTTPException(status_code=404, detail="Incident not found")

@router.put("/{id}", response_model=Incident)
async def update_incident(
    id: UUID,
    incident_in: IncidentUpdate,
    user_id: UUID = Depends(require_admin_or_analyst)
):
    client = get_incidents_client()
    existing = await get_incident(id, user_id)
    update_data = incident_in.model_dump(exclude_unset=True)
    update_data["updated_at"] = datetime.now().isoformat()

    # If status is changing to closed, set closed_at
    if "status" in update_data and update_data["status"] == "closed" and existing.status != "closed":
        update_data["closed_at"] = datetime.now().isoformat()
    elif "status" in update_data and update_data["status"] != "closed":
        update_data["closed_at"] = None

    # Handle appending timeline events if status changed
    timeline = list(existing.timeline)
    if "status" in update_data and update_data["status"] != existing.status:
        timeline.append({
            "timestamp": datetime.now().isoformat(),
            "event": f"Status updated to: {update_data['status']}",
            "actor": str(user_id)
        })
        update_data["timeline"] = timeline

    if DATABASE_AVAILABLE and client:
        try:
            response = client.table("incidents").update(update_data).eq("id", str(id)).execute()
            if response.data:
                log_audit_event(str(user_id), "update_incident", "incident", str(id), "success")
                return Incident(**response.data[0])
            raise HTTPException(status_code=404, detail="Incident not found")
        except HTTPException:
            raise
        except Exception as e:
            log_audit_event(str(user_id), "update_incident", "incident", str(id), "failure", metadata={"error": str(e)})
            raise HTTPException(status_code=500, detail=f"Database update failed: {e}")

    # Local fallback
    if str(id) in _in_memory_incidents:
        _in_memory_incidents[str(id)].update(update_data)
        log_audit_event(str(user_id), "update_incident", "incident", str(id), "success", metadata={"storage": "in-memory"})
        return Incident(**_in_memory_incidents[str(id)])
    raise HTTPException(status_code=404, detail="Incident not found")

@router.post("/{id}/timeline", response_model=Incident)
async def append_timeline_event(
    id: UUID,
    event_text: str,
    user_id: UUID = Depends(require_admin_or_analyst)
):
    existing = await get_incident(id, user_id)
    timeline = list(existing.timeline)
    timeline.append({
        "timestamp": datetime.now().isoformat(),
        "event": event_text,
        "actor": str(user_id)
    })
    
    update_data = {
        "timeline": timeline,
        "updated_at": datetime.now().isoformat()
    }
    client = get_incidents_client()
    if DATABASE_AVAILABLE and client:
        try:
            response = client.table("incidents").update(update_data).eq("id", str(id)).execute()
            if response.data:
                return Incident(**response.data[0])
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to append timeline event: {e}")

    # Local fallback
    if str(id) in _in_memory_incidents:
        _in_memory_incidents[str(id)].update(update_data)
        return Incident(**_in_memory_incidents[str(id)])
    raise HTTPException(status_code=404, detail="Incident not found")
