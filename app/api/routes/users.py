from typing import Dict

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user, require_roles
from app.core.constants import ROLE_ADMIN
from app.models.user import User
from app.schemas.user import UserSummary

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/health")
def users_health() -> Dict[str, str]:
    return {"status": "ok", "module": "users"}


@router.get("/me", response_model=UserSummary)
async def me(current_user: User = Depends(get_current_user)) -> UserSummary:
    return UserSummary(
        id=str(current_user.id),
        email=current_user.email,
        username=current_user.username,
        role=current_user.role,
        is_active=current_user.is_active,
    )


@router.get("/admin/health")
async def admin_health(_: User = Depends(require_roles(ROLE_ADMIN))) -> Dict[str, str]:
    return {"status": "ok", "scope": "admin"}
