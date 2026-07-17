"""
User Management API for CyberSec Assistant

Provides endpoints for user CRUD operations, role management, and activity tracking.

SECURITY NOTICE: All admin endpoints must use get_admin_client() dependency
instead of the global supabase_admin client. This ensures admin role verification
before accessing the service role client that bypasses RLS.
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from uuid import UUID
from datetime import datetime
import logging

from backend.api.deps import require_admin, get_admin_client
from backend.repositories.users import get_user, _update_cache

logger = logging.getLogger(__name__)

router = APIRouter()


def _active_super_admin_count(admin_client) -> int:
    response = admin_client.table('users').select('id').eq('role', 'super_admin').eq('is_active', True).execute()
    return len(response.data or [])


# ============================================================================
# Pydantic Models
# ============================================================================

class UserListResponse(BaseModel):
    """Response model for user list"""
    users: List[Dict[str, Any]]
    total: int
    page: int
    page_size: int


class UserRoleUpdate(BaseModel):
    """Request model for updating user role"""
    role: str  # 'user', 'admin', 'security_analyst'


class UserStatusUpdate(BaseModel):
    """Request model for updating user status"""
    is_active: bool


class UserActivityResponse(BaseModel):
    """Response model for user activity"""
    user_id: str
    username: str
    chat_history_count: int
    security_scans_count: int
    recent_activity: List[Dict[str, Any]]


# ============================================================================
# User Management Endpoints
# ============================================================================

@router.get("/users", response_model=UserListResponse)
async def get_all_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    role: Optional[str] = None,
    admin_id: UUID = Depends(require_admin),
    admin_client = Depends(get_admin_client)  # SECURE: Admin client with role verification
):
    """
    Get all users with pagination, search, and filter.

    Requires admin role.
    """
    try:
        offset = (page - 1) * page_size

        # Build query using secured admin client
        query = admin_client.table('users').select('*', count='exact')

        # Apply filters
        if search:
            # Sanitize: strip PostgREST filter operators to prevent filter injection
            safe = search.replace(',', ' ').replace('.', ' ').replace('(', '').replace(')', '').strip()
            query = query.or_(f"username.ilike.%{safe}%,full_name.ilike.%{safe}%,email.ilike.%{safe}%")

        if role:
            query = query.eq('role', role)

        # Apply pagination and get data with single execution
        response = query.range(offset, offset + page_size - 1).execute()
        total = response.count if hasattr(response, 'count') else len(response.data)

        users = []
        for user in response.data:
            # Sanitize sensitive data
            user_data = {
                'id': user.get('id'),
                'username': user.get('username'),
                'full_name': user.get('full_name'),
                'email': user.get('email'),
                'role': user.get('role'),
                'is_active': user.get('is_active'),
                'created_at': user.get('created_at'),
                'last_security_scan': user.get('last_security_scan'),
                'avatar_url': user.get('avatar_url')
            }
            users.append(user_data)

        return UserListResponse(
            users=users,
            total=total,
            page=page,
            page_size=page_size
        )

    except Exception as e:
        logger.error(f"Error getting users: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve users")


@router.get("/users/{user_id}")
async def get_user_details(
    user_id: UUID,
    admin_id: UUID = Depends(require_admin),
    admin_client = Depends(get_admin_client)  # SECURE: Admin client with role verification
):
    """
    Get detailed information about a specific user.

    Requires admin role.
    """
    try:
        response = admin_client.table('users').select('*').eq('id', str(user_id)).execute()

        if not response.data:
            raise HTTPException(status_code=404, detail="User not found")

        user = response.data[0]

        # Get user statistics
        chat_count_response = admin_client.table('chat_history').select('id', count='exact').eq('user_id', str(user_id)).execute()
        scans_count_response = admin_client.table('security_scans').select('id', count='exact').eq('user_id', str(user_id)).execute()

        # Sanitize sensitive data
        return {
            'id': user.get('id'),
            'username': user.get('username'),
            'full_name': user.get('full_name'),
            'email': user.get('email'),
            'role': user.get('role'),
            'is_active': user.get('is_active'),
            'created_at': user.get('created_at'),
            'updated_at': user.get('updated_at'),
            'last_security_scan': user.get('last_security_scan'),
            'avatar_url': user.get('avatar_url'),
            'security_context': user.get('security_context'),
            'statistics': {
                'chat_messages_count': chat_count_response.count if hasattr(chat_count_response, 'count') else len(chat_count_response.data),
                'security_scans_count': scans_count_response.count if hasattr(scans_count_response, 'count') else len(scans_count_response.data)
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user details: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve user details")


@router.put("/users/{user_id}/role")
async def update_user_role(
    user_id: UUID,
    role_update: UserRoleUpdate,
    admin_id: UUID = Depends(require_admin),
    admin_client = Depends(get_admin_client)  # SECURE: Admin client with role verification
):
    """
    Update a user's role.

    Requires admin role. Logs action to admin_audit_log.
    """
    try:
        # Validate role
        valid_roles = ['user', 'admin', 'security_analyst', 'super_admin']
        if role_update.role not in valid_roles:
            raise HTTPException(status_code=400, detail=f"Invalid role. Must be one of: {valid_roles}")

        # Get current user data
        current_user = get_user(user_id)
        if not current_user:
            raise HTTPException(status_code=404, detail="User not found")
        old_role = current_user.role
        actor = get_user(admin_id)
        if not actor:
            raise HTTPException(status_code=403, detail="Admin user not found")

        if str(user_id) == str(admin_id):
            raise HTTPException(status_code=400, detail="Cannot change your own role")

        if role_update.role == 'super_admin' and actor.role != 'super_admin':
            raise HTTPException(status_code=403, detail="Only a super admin can grant super admin role")

        if old_role == 'super_admin' and actor.role != 'super_admin':
            raise HTTPException(status_code=403, detail="Only a super admin can modify another super admin")

        if old_role == 'super_admin' and role_update.role != 'super_admin' and current_user.is_active:
            if _active_super_admin_count(admin_client) <= 1:
                raise HTTPException(status_code=400, detail="Cannot remove the last active super admin")

        # Update user role
        response = admin_client.table('users').update({
            'role': role_update.role,
            'updated_at': datetime.now().isoformat()
        }).eq('id', str(user_id)).execute()

        if not response.data:
            raise HTTPException(status_code=404, detail="Failed to update user role")

        # Update cache with new role
        current_user.role = role_update.role
        _update_cache(current_user)

        # Log admin action
        admin_client.table('admin_audit_log').insert({
            'admin_user_id': str(admin_id),
            'action_type': 'user_role_change',
            'target_type': 'user',
            'target_id': str(user_id),
            'action_details': {
                'old_role': old_role,
                'new_role': role_update.role,
                'username': current_user.username
            },
            'timestamp': datetime.now().isoformat()
        }).execute()

        logger.info(f"Admin {admin_id} changed role of user {user_id} to {role_update.role}")

        return {"message": "User role updated successfully", "new_role": role_update.role}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating user role: {e}")
        raise HTTPException(status_code=500, detail="Failed to update user role")


@router.put("/users/{user_id}/status")
async def update_user_status(
    user_id: UUID,
    status_update: UserStatusUpdate,
    admin_id: UUID = Depends(require_admin),
    admin_client = Depends(get_admin_client)  # SECURE: Admin client with role verification
):
    """
    Update a user's active status (activate/ban).

    Requires admin role. Logs action to admin_audit_log.
    """
    try:
        # Get current user data
        current_user = get_user(user_id)
        if not current_user:
            raise HTTPException(status_code=404, detail="User not found")
        old_status = current_user.is_active

        # Prevent admins from banning themselves
        if str(user_id) == str(admin_id) and not status_update.is_active:
            raise HTTPException(status_code=400, detail="Cannot ban yourself")

        actor = get_user(admin_id)
        if not actor:
            raise HTTPException(status_code=403, detail="Admin user not found")

        if current_user.role == 'super_admin' and actor.role != 'super_admin':
            raise HTTPException(status_code=403, detail="Only a super admin can modify another super admin")

        if current_user.role == 'super_admin' and current_user.is_active and not status_update.is_active:
            if _active_super_admin_count(admin_client) <= 1:
                raise HTTPException(status_code=400, detail="Cannot deactivate the last active super admin")

        # Update user status
        response = admin_client.table('users').update({
            'is_active': status_update.is_active,
            'updated_at': datetime.now().isoformat()
        }).eq('id', str(user_id)).execute()

        if not response.data:
            raise HTTPException(status_code=404, detail="Failed to update user status")

        # Update cache with new status
        current_user.is_active = status_update.is_active
        _update_cache(current_user)

        # Log admin action
        action_type = 'user_activate' if status_update.is_active else 'user_ban'
        admin_client.table('admin_audit_log').insert({
            'admin_user_id': str(admin_id),
            'action_type': action_type,
            'target_type': 'user',
            'target_id': str(user_id),
            'action_details': {
                'old_status': old_status,
                'new_status': status_update.is_active,
                'username': current_user.username
            },
            'timestamp': datetime.now().isoformat()
        }).execute()

        logger.info(f"Admin {admin_id} {'activated' if status_update.is_active else 'banned'} user {user_id}")

        return {"message": f"User {'activated' if status_update.is_active else 'banned'} successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating user status: {e}")
        raise HTTPException(status_code=500, detail="Failed to update user status")


@router.get("/users/{user_id}/activity", response_model=UserActivityResponse)
async def get_user_activity(
    user_id: UUID,
    admin_id: UUID = Depends(require_admin),
    admin_client = Depends(get_admin_client)  # SECURE: Admin client with role verification
):
    """
    Get user activity including chat history and security scans.

    Requires admin role.
    """
    try:
        # Get user info
        user = get_user(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Get recent chat history
        chat_response = admin_client.table('chat_history').select('*').eq('user_id', str(user_id)).order('created_at', desc=True).limit(10).execute()

        # Get recent security scans
        scans_response = admin_client.table('security_scans').select('*').eq('user_id', str(user_id)).order('scan_timestamp', desc=True).limit(10).execute()

        # Combine recent activity
        recent_activity = []

        for chat in chat_response.data[:5]:
            recent_activity.append({
                'type': 'chat',
                'timestamp': chat.get('created_at'),
                'details': {
                    'intent': chat.get('intent'),
                    'user_message': chat.get('user_message', '')[:100] + '...' if len(chat.get('user_message', '')) > 100 else chat.get('user_message', '')
                }
            })

        for scan in scans_response.data[:5]:
            recent_activity.append({
                'type': 'scan',
                'timestamp': scan.get('scan_timestamp'),
                'details': {
                    'scan_type': scan.get('scan_type'),
                    'status': scan.get('status'),
                    'risk_score': scan.get('risk_score')
                }
            })

        # Sort by timestamp
        recent_activity.sort(key=lambda x: x['timestamp'], reverse=True)

        return UserActivityResponse(
            user_id=str(user_id),
            username=user.username,
            chat_history_count=len(chat_response.data),
            security_scans_count=len(scans_response.data),
            recent_activity=recent_activity[:10]
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user activity: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve user activity")
