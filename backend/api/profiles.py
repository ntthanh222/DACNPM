from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from uuid import UUID
from backend.repositories.profiles import (
    get_profile,
    get_profile_by_username,
    create_profile,
    update_profile,
    delete_profile
)
from backend.database.models import Profile, ProfileCreate, ProfileUpdate
from backend.api.deps import get_current_user_id, get_optional_user_id, require_current_user_id

router = APIRouter()

@router.post("/", response_model=Profile, status_code=201)
def create_new_profile(profile: ProfileCreate):
    """Create a new user profile"""
    existing = get_profile_by_username(profile.username)
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")
    return create_profile(profile)

# Fixed route ordering: specific routes before parameterized routes (Bug 6)
@router.get("/username/{username}", response_model=Profile)
def read_profile_by_username(username: str):
    """Get a profile by username"""
    profile = get_profile_by_username(username)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile

@router.get("/{profile_id}", response_model=Profile)
def read_profile(
    profile_id: UUID,
    current_user_id: UUID = Depends(require_current_user_id)
):
    """Get a profile by ID - users can only access their own profile"""
    if profile_id != current_user_id:
        raise HTTPException(status_code=403, detail="Access denied. You can only view your own profile.")
    profile = get_profile(profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile

@router.put("/{profile_id}", response_model=Profile)
def update_user_profile(
    profile_id: UUID,
    profile_update: ProfileUpdate,
    current_user_id: UUID = Depends(require_current_user_id)
):
    """Update a profile - users can only update their own profile"""
    if profile_id != current_user_id:
        raise HTTPException(status_code=403, detail="Access denied. You can only update your own profile.")
    profile = update_profile(profile_id, profile_update)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile

@router.delete("/{profile_id}")
def delete_user_profile(
    profile_id: UUID,
    current_user_id: UUID = Depends(require_current_user_id)
):
    """Delete a profile - users can only delete their own profile"""
    if profile_id != current_user_id:
        raise HTTPException(status_code=403, detail="Access denied. You can only delete your own profile.")
    success = delete_profile(profile_id)
    if not success:
        raise HTTPException(status_code=404, detail="Profile not found")
    return {"message": "Profile deleted successfully"}
