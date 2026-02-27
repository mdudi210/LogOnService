app/
│
├── main.py
│
├── core/
│ ├── config.py
│ ├── database.py
│ ├── redis.py
│ ├── security.py
│ ├── constants.py
│
├── models/
│ ├── base.py
│ ├── user.py
│ ├── user_credentials.py
│ ├── user_device.py
│ ├── session.py
│ ├── user_mfa.py
│ ├── oauth_account.py
│ ├── audit_log.py
│
├── schemas/
│ ├── auth.py
│ ├── user.py
│ ├── token.py
│
├── repositories/
│ ├── user_repository.py
│ ├── session_repository.py
│ ├── audit_repository.py
│
├── services/
│ ├── auth_service.py
│ ├── token_service.py
│ ├── mfa_service.py
│ ├── oauth_service.py
│ ├── device_service.py
│ ├── risk_engine.py
│
├── api/
│ ├── deps.py
│ ├── routes/
│ │ ├── auth.py
│ │ ├── users.py
│
├── middlewares/
│ ├── rate_limiter.py
│ ├── audit_middleware.py
│
├── utils/
│ ├── encryption.py
│ ├── hashing.py
│ ├── otp.py
│
├── migrations/ (Alembic)
│
└── tests/
├── test_auth.py
├── test_mfa.py
