# Testing Guide

## Run All Tests
```bash
cd /Users/manishdudi/Desktop/LogOnService
source .venv/bin/activate
python -m pytest -q app/tests
```

## Current Coverage Areas
- Login success/failure behavior.
- Token issuance and token-type validation.
- Refresh flow and cookie rotation.
- Refresh replay/reuse detection behavior.
- Logout cookie clearing.
- Protected route auth (`/users/me`).
- RBAC boundary checks (`/users/admin/health`).
- CSRF enforcement on protected mutating routes.
- Session management endpoints (`/users/me/sessions*`).
- MFA login/setup/verify behavior.
- Encryption utility behavior.
- Admin security event endpoint.

## Test Files
- `app/tests/test_login.py`
- `app/tests/test_token_service.py`
- `app/tests/test_token_flow.py`
- `app/tests/test_auth_logout.py`
- `app/tests/test_users_me.py`
- `app/tests/test_authorization.py`
- `app/tests/test_mfa.py`
- `app/tests/test_user_sessions.py`
- `app/tests/test_security_events.py`
- `app/tests/test_encryption_utils.py`

## CI
- Workflow: `.github/workflows/ci.yml`
- Trigger: push + pull_request
- Action: install deps, verify Docker, run `pytest -q app/tests`

## What to Add Next
- Lint and static typing gates in CI (`ruff`, `mypy`).
- Security scan jobs.
- Concurrency stress tests for replay windows.
