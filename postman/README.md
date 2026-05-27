# Postman Testing Pack

These files are for API testing only and do not modify runtime behavior:
- `postman/LogOnService.postman_collection.json`
- `postman/LogOnService.local.postman_environment.json`
- `postman/LogOnService.e2e_single_run.postman_collection.json`

## Import
1. Open Postman.
2. Import the collection JSON.
3. Import the environment JSON.
4. Select environment `LogOnService Local`.

## Environment Variables (Dummy Defaults)
All variables in `LogOnService.local.postman_environment.json` now include dummy values so the flow imports cleanly:

| Variable | Dummy Value |
|---|---|
| `base_url` | `http://127.0.0.1:8000` |
| `login_identifier` | `admin@logonservices.local` |
| `login_password` | `Admin@12345` |
| `new_password` | `Admin@12345New` |
| `new_user_email` | `new.user+1@logonservices.local` |
| `new_user_username` | `new_user_1` |
| `new_user_password` | `NewUser@12345` |
| `csrf_token` | `dummy_csrf_token_replace_after_login` |
| `access_token` | `dummy_access_token_replace_after_login` |
| `refresh_token` | `dummy_refresh_token_replace_after_login` |
| `mfa_token` | `dummy_mfa_token_replace_after_login` |
| `totp_code` | `123456` |
| `totp_secret` | `DUMMYTOTPSECRETBASE32` |
| `session_jti` | `dummy-session-jti-from-sessions-endpoint` |
| `current_user_id` | `00000000-0000-0000-0000-000000000000` |

Notes:
- Cookie and token dummy values are placeholders; collection scripts automatically overwrite them after login/refresh responses.
- For MFA flows, replace `totp_code` with your current authenticator code.

## Recommended Flow
1. `GET /health`
2. `POST /auth/login`
3. If response says `mfa_required=true`:
   - `POST /auth/login/mfa`
4. `GET /users/me`
5. `GET /users/me/sessions`
6. `POST /auth/refresh`
7. `POST /auth/logout` or `POST /auth/logout-all`

## Single-Run E2E Flow
If you want one-click execution, import:
- `postman/LogOnService.e2e_single_run.postman_collection.json`

Then run only this request:
- `RUN E2E FLOW`

It executes internally in sequence:
1. `POST /auth/login`
2. `GET /users/me`
3. `GET /users/me/sessions`
4. `POST /auth/refresh`
5. `POST /auth/logout`

Requirements:
- Use a non-MFA test user in environment values:
  - `login_identifier`
  - `login_password`
- `base_url` must point to your running API.

## CSRF Handling
- Collection-level pre-request script auto-adds `X-CSRF-Token` for mutating requests (`POST/PUT/PATCH/DELETE`) using:
  - Cookie `csrf_token` (preferred)
  - Environment fallback `csrf_token`
- Collection-level test script captures values from `Set-Cookie` and stores:
  - `csrf_token`
  - `access_token`
  - `refresh_token`

## Notes
- Cookie-based auth is handled by Postman cookie jar.
- For `DELETE /users/me/sessions/:jti`, run `GET /users/me/sessions` first to auto-populate `session_jti`.
- Set `totp_code` manually from your authenticator app when testing MFA.
