# Architecture

## Service Goal
Authentication and identity core for enterprise/fintech systems with strong security defaults.

## Stack
- API: FastAPI
- ORM: SQLAlchemy 2.x async (`sqlalchemy.ext.asyncio`)
- DB: PostgreSQL
- Cache/session store: Redis
- Frontend: React + TypeScript (isolated in `frontend/`)
- Migration: Alembic
- Password hashing: Argon2id + explicit per-user salt field
- Auth tokens: JWT (access + refresh)

## Key Layers
- `app/api`: HTTP routes and dependencies
- `app/services`: business logic (auth, token)
- `app/repositories`: DB access abstraction (async)
- `app/models`: SQLAlchemy models
- `app/core`: config, DB engine/session, security helpers
- `app/schemas`: request/response contracts
- `frontend/*`: user/admin web console module

## Auth Flow (Current)
1. Client sends `POST /auth/login` with credentials.
2. Service loads user by email/username.
3. Service verifies status (`active`, not soft-deleted).
4. Service verifies password using `password_salt + plaintext` against Argon2 hash.
5. Service creates JWT access + refresh tokens.
6. Tokens are set as HttpOnly cookies.
7. CSRF cookie issued and verified on mutating operations.

## Token Flow (Current)
- Access token used for route auth (`get_current_user`).
- Refresh token used to rotate both tokens via `POST /auth/refresh`.
- Refresh token state tracked in Redis by `jti` metadata.
- Replay detection triggers revoke-all behavior.
- Logout clears cookies via `POST /auth/logout`.

## Authorization
- `get_current_user` validates cookie token + DB user state + role consistency.
- `require_roles(...)` enforces RBAC checks on endpoints.
- Admin-sensitive paths enforce MFA claim in token.

## Observability
- Audit events persisted in `audit_logs`.
- Structured security logs emitted.
- Optional SMTP alerting for configured security event types.
