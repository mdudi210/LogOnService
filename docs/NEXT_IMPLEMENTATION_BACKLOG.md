# Next Implementation Backlog

Last updated: March 28, 2026

This is the actionable engineering backlog for the next iterations.

## P0 (Start Immediately)

1. Backend-driven Admin Feature Configuration
- Goal: replace frontend local-storage feature toggles with real backend persistence.
- Scope:
  - Add config model/table (feature flags + metadata).
  - Add admin APIs (`GET/PUT /admin/config`).
  - Enforce RBAC + MFA for updates.
  - Wire frontend `Admin Config` page to these APIs.
- Files likely touched:
  - `app/models/*`, `app/repositories/*`, `app/api/routes/*`, `frontend/src/features/admin/*`

2. CI Quality Gates (beyond tests)
- Goal: prevent regressions before merge.
- Scope:
  - Add `ruff` lint job.
  - Add `mypy` type-check job.
  - Add dependency vulnerability scan.
  - Keep migration/test job as required gate.
- Files likely touched:
  - `.github/workflows/*`, `requirements.txt`, potential tool config files.

3. Security Event Dashboards + Alert Policy
- Goal: production-grade observability.
- Scope:
  - Define alert thresholds for `TOKEN_REUSE_DETECTED`, repeated login failures, repeated MFA failures.
  - Add runbook for on-call responses.
  - Add optional webhook/Slack integration (if approved).
- Files likely touched:
  - `app/services/security_event_service.py`, docs runbooks.

## P1 (Next Iteration)

4. Production Secret Rotation Runbooks
- Goal: secure key lifecycle operations.
- Scope:
  - Document and script rotation for:
    - `JWT_SECRET_KEY`
    - `JWT_REFRESH_SECRET_KEY`
    - `TOTP_ENCRYPTION_KEY`
  - Add staged rollout + rollback path.

5. Concurrency / Abuse Security Tests
- Goal: verify behavior under race and attack patterns.
- Scope:
  - Parallel refresh replay attempts.
  - CSRF edge/mismatch scenarios.
  - Session revoke race windows.
  - High-rate auth attempts.
- Files likely touched:
  - `app/tests/*` (new integration test modules).

6. Frontend UX hardening for auth edge cases
- Goal: resilient operator UX.
- Scope:
  - Explicit 401/403 route handling with guided re-auth.
  - Session-expired modal/redirect flow.
  - Admin event filters + pagination.
- Files likely touched:
  - `frontend/src/features/*`, `frontend/src/app/*`.

## P2 (Strategic Extensions)

7. OAuth/OIDC provider integrations
- Add enterprise IdP connectors (Google/Microsoft/etc.) with secure callback handling.

8. Policy management and tenant readiness
- Password/MFA/session policies by org/tenant.
- Audit export and retention controls.

9. SLO/SLA operationalization
- Service-level objectives for auth latency/error rates.
- Error budgets and reliability reporting.

## Suggested Sprint Plan

Sprint 1:
- P0-1 (Admin config APIs + frontend integration)
- P0-2 (CI quality gates)

Sprint 2:
- P0-3 (alert policy/runbooks)
- P1-4 (secret rotation)

Sprint 3:
- P1-5 (security concurrency tests)
- P1-6 (frontend auth UX hardening)

