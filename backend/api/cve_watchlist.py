from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4
from fastapi import APIRouter, Depends, HTTPException

from backend.database.models import CVEWatchlist, CVEWatchlistCreate
from backend.database.connection import supabase, supabase_admin, DATABASE_AVAILABLE
from backend.api.deps import require_current_user_id
from backend.services.audit_service import log_audit_event

router = APIRouter()

# Fallback memory storage
_in_memory_watchlist: Dict[str, Dict[str, Any]] = {}

def get_watchlist_client():
    return supabase_admin if supabase_admin else supabase

@router.get("/", response_model=List[CVEWatchlist])
async def list_watchlist(
    user_id: UUID = Depends(require_current_user_id)
):
    client = get_watchlist_client()
    if DATABASE_AVAILABLE and client:
        try:
            response = client.table("cve_watchlist").select("*").eq("user_id", str(user_id)).execute()
            return [CVEWatchlist(**r) for r in (response.data or [])]
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Database query failed: {e}")

    # Fallback
    return [CVEWatchlist(**v) for v in _in_memory_watchlist.values() if v.get("user_id") == str(user_id)]

@router.post("/", response_model=CVEWatchlist)
async def watch_cve(
    watchlist_in: CVEWatchlistCreate,
    user_id: UUID = Depends(require_current_user_id)
):
    client = get_watchlist_client()
    watchlist_id = uuid4()
    now = datetime.now().isoformat()
    
    watchlist_data = watchlist_in.model_dump()
    watchlist_data.update({
        "id": str(watchlist_id),
        "user_id": str(user_id),
        "created_at": now
    })

    if DATABASE_AVAILABLE and client:
        try:
            # Check unique constraint user_id + cve_id + asset_id
            query = client.table("cve_watchlist").select("*").eq("user_id", str(user_id)).eq("cve_id", watchlist_in.cve_id)
            if watchlist_in.asset_id:
                query = query.eq("asset_id", str(watchlist_in.asset_id))
            else:
                query = query.is_("asset_id", "null")
            
            existing = query.execute()
            if existing.data:
                raise HTTPException(status_code=400, detail="CVE already watched for this asset.")

            response = client.table("cve_watchlist").insert(watchlist_data).execute()
            if response.data:
                log_audit_event(str(user_id), "watch_cve", "cve_watchlist", str(watchlist_id), "success")
                return CVEWatchlist(**response.data[0])
        except HTTPException:
            raise
        except Exception as e:
            log_audit_event(str(user_id), "watch_cve", "cve_watchlist", str(watchlist_id), "failure", metadata={"error": str(e)})
            raise HTTPException(status_code=500, detail=f"Database insert failed: {e}")

    # Local fallback
    _in_memory_watchlist[str(watchlist_id)] = watchlist_data
    log_audit_event(str(user_id), "watch_cve", "cve_watchlist", str(watchlist_id), "success", metadata={"storage": "in-memory"})
    return CVEWatchlist(**watchlist_data)

@router.delete("/{id}")
async def unwatch_cve(
    id: UUID,
    user_id: UUID = Depends(require_current_user_id)
):
    client = get_watchlist_client()
    if DATABASE_AVAILABLE and client:
        try:
            response = client.table("cve_watchlist").delete().eq("id", str(id)).eq("user_id", str(user_id)).execute()
            if response.data:
                log_audit_event(str(user_id), "unwatch_cve", "cve_watchlist", str(id), "success")
                return {"status": "success", "message": "CVE unwatched successfully."}
            raise HTTPException(status_code=404, detail="Watchlist entry not found")
        except HTTPException:
            raise
        except Exception as e:
            log_audit_event(str(user_id), "unwatch_cve", "cve_watchlist", str(id), "failure", metadata={"error": str(e)})
            raise HTTPException(status_code=500, detail=f"Database delete failed: {e}")

    # Local fallback
    if str(id) in _in_memory_watchlist and _in_memory_watchlist[str(id)].get("user_id") == str(user_id):
        del _in_memory_watchlist[str(id)]
        log_audit_event(str(user_id), "unwatch_cve", "cve_watchlist", str(id), "success", metadata={"storage": "in-memory"})
        return {"status": "success", "message": "CVE unwatched successfully."}
    raise HTTPException(status_code=404, detail="Watchlist entry not found")
