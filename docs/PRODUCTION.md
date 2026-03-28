# Production Deployment Guide

## Deployment Pattern
- API service behind API Gateway/WAF.
- Managed PostgreSQL (or HA cluster) with PITR and encrypted storage.
- Managed Redis with auth, TLS, persistence, replication.
- Frontend served as static bundle behind CDN/reverse proxy.
- Secrets from secret manager (not plaintext `.env` in repo).

## Required Environment Variables
- `DATABASE_URL` (use async driver, e.g. `postgresql+asyncpg://...`)
- `REDIS_URL`
- `JWT_SECRET_KEY`
- `JWT_REFRESH_SECRET_KEY`
- `JWT_ALGORITHM`
- `ACCESS_TOKEN_EXPIRE_MINUTES`
- `REFRESH_TOKEN_EXPIRE_MINUTES`
- `TOTP_ENCRYPTION_KEY`
- `AUTH_COOKIE_SECURE=true`
- `AUTH_COOKIE_SAMESITE` (`strict` or policy-driven choice)
- `SECURITY_ALERTS_ENABLED`
- `SECURITY_ALERT_EMAIL`
- `SECURITY_ALERT_EVENT_TYPES`

## Infrastructure Notes
- `utilsContainers/Postgre` and `utilsContainers/Redis` are optimized for local/dev.
- In production, replace volume mounts with managed data stores or hardened server paths.

## Security Baseline
- TLS enforced end-to-end.
- Principle of least privilege for DB and Redis accounts.
- Continuous dependency and container scanning.
- Centralized logs and audit trails.
- Alerting for failed auth spikes and suspicious token patterns.
- Strict CORS + hostname consistency for cookie-auth frontends.

## Operational Runbooks (Minimum)
- Key rotation procedure (JWT keys).
- Encryption key rotation procedure (`TOTP_ENCRYPTION_KEY`).
- Incident response for token compromise.
- Backup and restore drills.
- Rollback strategy for migrations.
