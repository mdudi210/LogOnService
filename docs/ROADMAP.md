# Roadmap

## Completed
- Async SQLAlchemy migration.
- JWT access/refresh token creation + verification.
- HttpOnly cookie-based auth transport.
- Salted Argon2 password verification.
- Auth and RBAC dependencies.
- Core auth boundary test coverage.

## Next Milestones
1. Refresh token persistence in Redis with rotation tracking and reuse detection.
2. Session table integration with token/session IDs.
3. MFA implementation (TOTP first).
4. Audit middleware integration.
5. Rate limiting middleware with Redis.
6. OAuth provider integration.
7. CI/CD hardening (lint, type check, security scans, migration checks).
