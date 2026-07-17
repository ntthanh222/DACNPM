from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4
from fastapi import APIRouter, Depends, HTTPException

from backend.database.models import Notification, NotificationCreate
from backend.database.connection import supabase, supabase_admin, DATABASE_AVAILABLE
from backend.api.deps import require_current_user_id

router = APIRouter()

# Fallback memory storage
_in_memory_notifications: Dict[str, Dict[str, Any]] = {}

def get_notif_client():
    return supabase_admin if supabase_admin else supabase

@router.get("/", response_model=List[Notification])
async def list_notifications(
    user_id: UUID = Depends(require_current_user_id)
):
    client = get_notif_client()
    if DATABASE_AVAILABLE and client:
        try:
            response = client.table("notifications").select("*").eq("user_id", str(user_id)).execute()
            return [Notification(**r) for r in (response.data or [])]
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Database query failed: {e}")

    # Fallback
    local_list = [Notification(**v) for v in _in_memory_notifications.values() if v.get("user_id") == str(user_id)]
    return sorted(local_list, key=lambda x: x.created_at, reverse=True)

@router.post("/", response_model=Notification)
async def create_notification(
    notif_in: NotificationCreate,
    user_id: UUID = Depends(require_current_user_id)
):
    # Endpoint to allow creating notifications
    if notif_in.user_id != user_id:
        raise HTTPException(status_code=403, detail="Access denied. You can only create notifications for yourself.")

    client = get_notif_client()
    notif_id = uuid4()
    now = datetime.now().isoformat()
    
    notif_data = notif_in.model_dump()
    notif_data.update({
        "id": str(notif_id),
        "created_at": now
    })
    # Convert user_id to string
    notif_data["user_id"] = str(notif_data["user_id"])

    if DATABASE_AVAILABLE and client:
        try:
            response = client.table("notifications").insert(notif_data).execute()
            if response.data:
                return Notification(**response.data[0])
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Database insert failed: {e}")

    # Local fallback
    _in_memory_notifications[str(notif_id)] = notif_data
    return Notification(**notif_data)

@router.put("/{id}/read", response_model=Notification)
async def mark_read(
    id: UUID,
    user_id: UUID = Depends(require_current_user_id)
):
    client = get_notif_client()
    update_data = {"is_read": True}

    if DATABASE_AVAILABLE and client:
        try:
            response = client.table("notifications").update(update_data).eq("id", str(id)).eq("user_id", str(user_id)).execute()
            if response.data:
                return Notification(**response.data[0])
            raise HTTPException(status_code=404, detail="Notification not found")
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Database update failed: {e}")

    # Local fallback
    if str(id) in _in_memory_notifications and _in_memory_notifications[str(id)].get("user_id") == str(user_id):
        _in_memory_notifications[str(id)].update(update_data)
        return Notification(**_in_memory_notifications[str(id)])
    raise HTTPException(status_code=404, detail="Notification not found")

@router.put("/read-all")
async def mark_all_read(
    user_id: UUID = Depends(require_current_user_id)
):
    client = get_notif_client()
    update_data = {"is_read": True}

    if DATABASE_AVAILABLE and client:
        try:
            response = client.table("notifications").update(update_data).eq("user_id", str(user_id)).execute()
            return {"status": "success", "message": f"Successfully marked all read."}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Database update failed: {e}")

    # Local fallback
    for notif in _in_memory_notifications.values():
        if notif.get("user_id") == str(user_id):
            notif["is_read"] = True
    return {"status": "success", "message": f"Successfully marked all read."}
