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
- TOTP secret encryption-at-rest with legacy plaintext compatibility upgrade path.
- Runtime audit middleware wiring for auth-sensitive mutating endpoints (fail-open).
- OAuth account linking/login endpoints and Google authorization-code callback flow.
- Adaptive risk-scoring engine + high-risk login block policy (when MFA is not enabled).
- Security alerting pipeline with optional email/webhook delivery.
- Admin security event observability endpoints (JSON + CSV export).
- Postman runner smoke collections for auth and admin-security workflows.

## Seed Users (Dev Only)
- Admin: `admin@test.local` / `Admin@12345`
- User: `user@test.local` / `User@12345`

## Known Placeholders (Not Yet Implemented)
- Additional OAuth providers (GitHub/enterprise OIDC beyond Google flow).
- SIEM-native integrations and alert routing playbooks.
- Session/device self-service management endpoints for end users/admins.
