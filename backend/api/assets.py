import csv
import io
from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from fastapi.responses import StreamingResponse

from backend.database.models import Asset, AssetCreate, AssetUpdate
from backend.database.connection import supabase, supabase_admin, DATABASE_AVAILABLE
from backend.api.deps import require_current_user_id, require_admin_or_analyst, require_admin
from backend.services.audit_service import log_audit_event
from backend.services.matching_service import MatchingService

router = APIRouter()

# Fallback memory storage
_in_memory_assets: Dict[str, Dict[str, Any]] = {}

def get_asset_client():
    return supabase_admin if supabase_admin else supabase

@router.get("/", response_model=List[Asset])
async def list_assets(
    criticality: Optional[str] = None,
    internet_exposure: Optional[bool] = None,
    status: Optional[str] = None,
    asset_type: Optional[str] = None,
    q: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    user_id: UUID = Depends(require_admin_or_analyst)
):
    client = get_asset_client()
    if DATABASE_AVAILABLE and client:
        try:
            query = client.table("assets").select("*").eq("is_deleted", False)
            if criticality:
                query = query.eq("criticality", criticality)
            if internet_exposure is not None:
                query = query.eq("internet_exposure", internet_exposure)
            if status:
                query = query.eq("status", status)
            if asset_type:
                query = query.eq("asset_type", asset_type)
            
            response = query.order("created_at", desc=True).execute()
            results = response.data or []

            # Substring text search filter
            if q:
                q_low = q.lower()
                results = [
                    r for r in results 
                    if q_low in (r.get("name") or "").lower() or 
                       q_low in (r.get("hostname") or "").lower() or 
                       q_low in (r.get("ip_address") or "").lower()
                ]

            # Range/Pagination
            return [Asset(**r) for r in results[skip:skip+limit]]
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Database query failed: {e}")

    # Fallback local list
    local_list = [Asset(**v) for v in _in_memory_assets.values() if not v.get("is_deleted")]
    if criticality:
        local_list = [a for a in local_list if a.criticality == criticality]
    if internet_exposure is not None:
        local_list = [a for a in local_list if a.internet_exposure == internet_exposure]
    if status:
        local_list = [a for a in local_list if a.status == status]
    if asset_type:
        local_list = [a for a in local_list if a.asset_type == asset_type]
    if q:
        q_low = q.lower()
        local_list = [a for a in local_list if q_low in a.name.lower() or (a.hostname and q_low in a.hostname.lower())]
    return local_list[skip:skip+limit]

@router.post("/", response_model=Asset)
async def create_asset(
    asset_in: AssetCreate,
    user_id: UUID = Depends(require_admin_or_analyst)
):
    client = get_asset_client()
    asset_id = uuid4()
    now = datetime.now().isoformat()
    asset_data = asset_in.model_dump()
    asset_data.update({
        "id": str(asset_id),
        "created_at": now,
        "updated_at": now,
        "is_deleted": False
    })

    if DATABASE_AVAILABLE and client:
        try:
            response = client.table("assets").insert(asset_data).execute()
            if response.data:
                log_audit_event(str(user_id), "create_asset", "asset", str(asset_id), "success")
                return Asset(**response.data[0])
        except Exception as e:
            log_audit_event(str(user_id), "create_asset", "asset", str(asset_id), "failure", metadata={"error": str(e)})
            raise HTTPException(status_code=500, detail=f"Database insert failed: {e}")

    # Local storage
    _in_memory_assets[str(asset_id)] = asset_data
    log_audit_event(str(user_id), "create_asset", "asset", str(asset_id), "success", metadata={"storage": "in-memory"})
    return Asset(**asset_data)

@router.get("/{id}", response_model=Asset)
async def get_asset(
    id: UUID,
    user_id: UUID = Depends(require_admin_or_analyst)
):
    client = get_asset_client()
    if DATABASE_AVAILABLE and client:
        try:
            response = client.table("assets").select("*").eq("id", str(id)).eq("is_deleted", False).execute()
            if response.data:
                return Asset(**response.data[0])
            raise HTTPException(status_code=404, detail="Asset not found")
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Database query failed: {e}")

    # Local fallback
    if str(id) in _in_memory_assets and not _in_memory_assets[str(id)].get("is_deleted"):
        return Asset(**_in_memory_assets[str(id)])
    raise HTTPException(status_code=404, detail="Asset not found")

@router.put("/{id}", response_model=Asset)
async def update_asset(
    id: UUID,
    asset_in: AssetUpdate,
    user_id: UUID = Depends(require_admin_or_analyst)
):
    client = get_asset_client()
    update_data = asset_in.model_dump(exclude_unset=True)
    update_data["updated_at"] = datetime.now().isoformat()

    if DATABASE_AVAILABLE and client:
        try:
            response = client.table("assets").update(update_data).eq("id", str(id)).execute()
            if response.data:
                log_audit_event(str(user_id), "update_asset", "asset", str(id), "success")
                return Asset(**response.data[0])
            raise HTTPException(status_code=404, detail="Asset not found")
        except HTTPException:
            raise
        except Exception as e:
            log_audit_event(str(user_id), "update_asset", "asset", str(id), "failure", metadata={"error": str(e)})
            raise HTTPException(status_code=500, detail=f"Database update failed: {e}")

    # Local fallback
    if str(id) in _in_memory_assets and not _in_memory_assets[str(id)].get("is_deleted"):
        _in_memory_assets[str(id)].update(update_data)
        log_audit_event(str(user_id), "update_asset", "asset", str(id), "success", metadata={"storage": "in-memory"})
        return Asset(**_in_memory_assets[str(id)])
    raise HTTPException(status_code=404, detail="Asset not found")

@router.delete("/{id}")
async def delete_asset(
    id: UUID,
    user_id: UUID = Depends(require_admin)
):
    client = get_asset_client()
    update_data = {"is_deleted": True, "updated_at": datetime.now().isoformat()}

    if DATABASE_AVAILABLE and client:
        try:
            response = client.table("assets").update(update_data).eq("id", str(id)).execute()
            if response.data:
                log_audit_event(str(user_id), "delete_asset", "asset", str(id), "success")
                return {"status": "success", "message": "Asset deleted successfully"}
            raise HTTPException(status_code=404, detail="Asset not found")
        except HTTPException:
            raise
        except Exception as e:
            log_audit_event(str(user_id), "delete_asset", "asset", str(id), "failure", metadata={"error": str(e)})
            raise HTTPException(status_code=500, detail=f"Database deletion failed: {e}")

    # Local fallback
    if str(id) in _in_memory_assets and not _in_memory_assets[str(id)].get("is_deleted"):
        _in_memory_assets[str(id)].update(update_data)
        log_audit_event(str(user_id), "delete_asset", "asset", str(id), "success", metadata={"storage": "in-memory"})
        return {"status": "success", "message": "Asset deleted successfully"}
    raise HTTPException(status_code=404, detail="Asset not found")

@router.post("/import-csv")
async def import_assets_csv(
    file: UploadFile = File(...),
    user_id: UUID = Depends(require_admin_or_analyst)
):
    try:
        contents = await file.read()
        decoded = contents.decode("utf-8")
        reader = csv.DictReader(io.StringIO(decoded))
        
        imported_count = 0
        client = get_asset_client()

        for row in reader:
            asset_id = uuid4()
            now = datetime.now().isoformat()
            asset_data = {
                "id": str(asset_id),
                "name": row.get("name", "Unnamed Asset"),
                "asset_type": row.get("asset_type", "Unknown"),
                "hostname": row.get("hostname"),
                "ip_address": row.get("ip_address"),
                "os": row.get("os"),
                "vendor": row.get("vendor"),
                "product": row.get("product"),
                "version": row.get("version"),
                "cpe": row.get("cpe"),
                "owner": row.get("owner"),
                "department": row.get("department"),
                "environment": row.get("environment", "production"),
                "criticality": row.get("criticality", "medium"),
                "internet_exposure": row.get("internet_exposure", "false").lower() == "true",
                "status": row.get("status", "active"),
                "notes": row.get("notes"),
                "is_deleted": False,
                "created_at": now,
                "updated_at": now
            }

            if DATABASE_AVAILABLE and client:
                client.table("assets").insert(asset_data).execute()
            else:
                _in_memory_assets[str(asset_id)] = asset_data
            
            imported_count += 1

        log_audit_event(str(user_id), "import_assets_csv", "asset", None, "success", metadata={"count": imported_count})
        return {"status": "success", "message": f"Successfully imported {imported_count} assets."}
    except Exception as e:
        log_audit_event(str(user_id), "import_assets_csv", "asset", None, "failure", metadata={"error": str(e)})
        raise HTTPException(status_code=400, detail=f"Failed to parse CSV: {e}")

@router.get("/export-csv/download")
async def export_assets_csv(
    user_id: UUID = Depends(require_admin_or_analyst)
):
    client = get_asset_client()
    results = []
    if DATABASE_AVAILABLE and client:
        try:
            response = client.table("assets").select("*").eq("is_deleted", False).execute()
            results = response.data or []
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Database query failed: {e}")
    else:
        results = [v for v in _in_memory_assets.values() if not v.get("is_deleted")]

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "name", "asset_type", "hostname", "ip_address", "os", "vendor", "product", 
        "version", "cpe", "owner", "department", "environment", "criticality", 
        "internet_exposure", "status", "notes"
    ])
    
    for asset in results:
        writer.writerow([
            asset.get("name"), asset.get("asset_type"), asset.get("hostname"), 
            asset.get("ip_address"), asset.get("os"), asset.get("vendor"), 
            asset.get("product"), asset.get("version"), asset.get("cpe"), 
            asset.get("owner"), asset.get("department"), asset.get("environment"), 
            asset.get("criticality"), str(asset.get("internet_exposure")), 
            asset.get("status"), asset.get("notes")
        ])

    log_audit_event(str(user_id), "export_assets_csv", "asset", None, "success")
    output.seek(0)
    
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode("utf-8")),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=assets_inventory.csv"}
    )

@router.get("/{id}/matching-cves")
async def get_asset_matching_cves(
    id: UUID,
    user_id: UUID = Depends(require_admin_or_analyst)
):
    # Retrieve asset details
    asset = await get_asset(id, user_id=user_id)
    if not asset.cpe:
        return {"matches": []}

    client = get_asset_client()
    matches = []

    # Get cve_records from database
    cve_list = []
    if DATABASE_AVAILABLE and client:
        try:
            response = client.table("cve_records").select("*").execute()
            cve_list = response.data or []
        except Exception:
            pass

    # Compare asset CPE against all CVE records
    for cve in cve_list:
        cve_description = cve.get("description") or ""
        # Look for CPE references in description or database
        # For simplicity, extract product from description, or if CPE matches
        cve_id = cve.get("cve_id")
        cvss_score = float(cve.get("cvss_score") or 5.0)

        # Match vendor/product substrings in description as fallback
        match_detected = False
        confidence = 0.0
        reason = ""

        # CPE check
        if asset.vendor and asset.product:
            if asset.vendor.lower() in cve_description.lower() and asset.product.lower() in cve_description.lower():
                match_detected = True
                confidence = 0.7
                reason = f"Keyword match for {asset.vendor} {asset.product} in CVE description."

        if match_detected:
            # Calculate risk score
            risk = MatchingService.calculate_risk_score(
                cvss_score=cvss_score,
                criticality=asset.criticality,
                internet_exposure=asset.internet_exposure,
                known_exploited=False, # default fallback
                patch_available=True
            )
            matches.append({
                "cve_id": cve_id,
                "cvss_score": cvss_score,
                "confidence_score": confidence,
                "match_reason": reason,
                "risk_score": risk["score"],
                "risk_severity": risk["severity"],
                "risk_explanation": risk["explanation"]
            })

    return {"matches": matches}
