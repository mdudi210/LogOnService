from typing import Dict

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.auth import LoginRequest, LoginResponse, LoginUser
from app.services.auth_service import AuthService, InactiveUserError, InvalidCredentialsError

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/health")
def auth_health() -> Dict[str, str]:
    return {"status": "ok", "module": "auth"}


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> LoginResponse:
    auth_service = AuthService(db)

    try:
        user = auth_service.login(
            email_or_username=payload.email_or_username,
            password=payload.password,
        )
    except InvalidCredentialsError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email/username or password",
        )
    except InactiveUserError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )

    return LoginResponse(
        message="Login successful",
        user=LoginUser(
            id=str(user.id),
            email=user.email,
            username=user.username,
            role=user.role,
            is_verified=user.is_verified,
        ),
    )
