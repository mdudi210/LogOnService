from fastapi import APIRouter

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/health")
def users_health() -> dict[str, str]:
    return {"status": "ok", "module": "users"}


@router.get("/me")
def me_placeholder() -> dict[str, str]:
    return {"message": "User profile route scaffolded. Implement auth dependency next."}
