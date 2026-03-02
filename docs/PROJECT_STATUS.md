# Project Status

## Implemented
- Async SQLAlchemy infrastructure (`create_async_engine`, `async_sessionmaker`, async dependency injection).
- PostgreSQL + Redis dockerized local infrastructure with generic env-based configuration.
- SQLAlchemy models for core auth domain.
- Alembic migrations:
  - `20260227_0001` initial schema.
  - `20260302_0002` add `password_salt`.
- Salted password hashing workflow using Argon2id.
- JWT access/refresh token generation + verification.
- HttpOnly cookie-based token delivery.
- Auth routes:
  - `POST /auth/login`
  - `POST /auth/refresh`
  - `POST /auth/logout`
- `get_current_user` JWT dependency.
- Role-based authorization dependency `require_roles(...)`.
- Protected route examples:
  - `GET /users/me`
  - `GET /users/admin/health` (admin-only)
- Test suite covering login, token flow, logout, protected routes, and authorization boundaries.

## Seed Users (Dev Only)
- Admin: `admin@test.local` / `Admin@12345`
- User: `user@test.local` / `User@12345`

## Known Placeholders (Not Yet Implemented)
- Redis-backed refresh token persistence and reuse detection.
- Session table integration with token lifecycle.
- MFA challenge/enrollment implementation.
- Encryption provider implementation (`app/utils/encryption.py`).
- Production observability and audit middleware runtime wiring.
