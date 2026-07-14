from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, Dict, Any
import logging
from datetime import datetime, timedelta
from backend.repositories.cve_lookups import get_cached_cve_with_fallback, create_cve_lookup
from backend.utils.cve_lookup import validate_cve_id, async_check_cve
from backend.utils.cve_translator import translate_cve_response
from backend.config import settings
from backend.database.models import CVELookupCreate

from uuid import UUID
from backend.api.deps import get_current_user_id

router = APIRouter()
logger = logging.getLogger(__name__)

class CVERequest(BaseModel):
    cve_id: str

class CVEResponse(BaseModel):
    cve_id: str
    response_data: Dict[str, Any]
    cvss_score: Optional[str] = None
    severity: Optional[str] = None
    is_cached: bool
    message: Optional[str] = None

@router.post("/lookup", response_model=Dict[str, Any])
async def lookup_cve_endpoint(request: CVERequest):
    """
    Lookup CVE information from NIST NVD API with caching

    Uses shared CVE lookup utility with existing caching layer
    """
    try:
        cve_id = request.cve_id.upper()

        # Validate CVE ID format
        if not validate_cve_id(cve_id):
            raise HTTPException(
                status_code=400,
                detail="Invalid CVE ID format. Expected format: CVE-YYYY-NNNN"
            )

        # Check cache first
        cached_result = get_cached_cve_with_fallback(cve_id)

        if cached_result.get('is_cached'):
            logger.info(f"Using cached CVE data for {cve_id}")
            # Translate even cached results to Vietnamese
            translated_result = translate_cve_response(cached_result, cve_id)
            return {
                **translated_result,
                "message": "Data retrieved from cache"
            }

        # Use shared CVE lookup utility (handles fallback to public endpoint automatically)
        api_result = await async_check_cve(cve_id)

        # Check if API call was successful
        if 'error' in api_result:
            return {
                **api_result,
                "message": api_result.get('message', 'API lookup failed')
            }

        # Cache the result
        cve_lookup_data = CVELookupCreate(
            cve_id=cve_id,
            query_data={"query": cve_id},
            response_data=api_result.get('response_data', {}),
            cache_expires_at=datetime.now() + timedelta(hours=24)
        )
        create_cve_lookup(cve_lookup_data)

        # Translate description to Vietnamese
        translated_result = translate_cve_response(api_result, cve_id)

        return {
            **translated_result,
            "message": "Data retrieved from NIST NVD API"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"CVE lookup error: {e}")
        raise HTTPException(status_code=500, detail=f"CVE lookup failed: {str(e)}")

@router.get("/stats")
def get_cve_stats(current_user_id: UUID = Depends(get_current_user_id)):
    """Get CVE lookup statistics - requires authentication"""
    from backend.repositories.cve_lookups import get_cache_statistics
    stats = get_cache_statistics()
    if stats:
        return stats
    else:
        return {"message": "No CVE data available yet", "total_entries": 0}
