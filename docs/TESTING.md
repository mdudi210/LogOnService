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
- Logout cookie clearing.
- Protected route auth (`/users/me`).
- RBAC boundary checks (`/users/admin/health`).

## Test Files
- `app/tests/test_login.py`
- `app/tests/test_token_service.py`
- `app/tests/test_token_flow.py`
- `app/tests/test_auth_logout.py`
- `app/tests/test_users_me.py`
- `app/tests/test_authorization.py`

## What to Add Next
- Integration tests against real DB + Redis for refresh token persistence.
- MFA flow tests.
- Rate limiting tests.
- Session invalidation tests.
- Security regression tests (token replay, stale role, inactive account transitions).
