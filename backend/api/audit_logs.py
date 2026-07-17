from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query

from backend.database.models import AuditLog
from backend.api.deps import require_admin
from backend.services.audit_service import get_audit_logs

router = APIRouter()

@router.get("/", response_model=List[AuditLog])
async def list_audit_logs(
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    user_id: UUID = Depends(require_admin)
):
    try:
        logs = get_audit_logs(limit=limit, offset=offset)
        return [AuditLog(**l) for l in logs]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch audit logs: {e}")
