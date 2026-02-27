---

# 🔐 World-Class Authentication & Login Service

**Version:** 1.0
**Target:** Financial / Enterprise Grade
**Architecture Style:** Modular, Scalable, Zero-Trust Ready

---

# 1️⃣ System Overview

## Objective

Design a secure, scalable, modular authentication system that supports:

- Username + Password
- MFA (TOTP, Email OTP, WebAuthn)
- OAuth 2.1 (Third-Party Login)
- Refresh Token Rotation
- Session Age Enforcement
- Rate Limiting & Risk Detection
- Redis-backed session control
- Audit Logging
- Future passwordless compatibility

---

# 2️⃣ High-Level Architecture

```text
Client (Browser / Mobile App)
        ↓
CDN / WAF / Edge
        ↓
API Gateway
        ↓
Authentication Service
        ↓
User Service + Database
        ↓
Redis (Session + Tokens)
```

### Component Responsibilities

| Component    | Responsibility                            |
| ------------ | ----------------------------------------- |
| CDN/WAF      | TLS, DDoS protection, HSTS                |
| API Gateway  | Request validation, routing               |
| Auth Service | Login logic, token generation             |
| User Service | User retrieval, profile management        |
| Redis        | Token store, session store, rate limiting |
| DB           | User records                              |

---

# 3️⃣ Transport Layer Security

## Requirements

- TLS 1.3 only
- Strong cipher suites
- HSTS enabled

### HSTS Header

```http
Strict-Transport-Security: max-age=31536000; includeSubDomains; preload
```

This ensures:

- No HTTP fallback
- Protection against SSL stripping

---

# 4️⃣ Authentication Flow

## 4.1 Login Flow (Password Based)

```text
1. Client → POST /auth/login
2. API Gateway → Validate schema
3. Auth Service:
      - Rate limit check
      - Fetch user from DB
      - Verify password hash
      - Check account status
      - Risk evaluation
      - Trigger MFA if required
4. Issue tokens
5. Store refresh token in Redis
6. Return HttpOnly cookies
```

---

# 5️⃣ Password Security

## Hashing Algorithm

Use:

- Argon2id (recommended)
  OR
- bcrypt (minimum 12 rounds)

### Registration

1. Generate random salt
2. Hash password using Argon2
3. Store:

```json
{
  "user_id": "123",
  "password_hash": "...",
  "algorithm": "argon2id",
  "created_at": "timestamp"
}
```

### Login Verification

1. Retrieve stored hash
2. Hash incoming password
3. Constant-time comparison

---

# 6️⃣ Token Design

## 6.1 Access Token

- Type: JWT
- TTL: 15 minutes
- Stored in:
  - HttpOnly
  - Secure
  - SameSite=Strict cookie

### Claims

```json
{
  "sub": "user_id",
  "role": "admin",
  "iat": 123456,
  "exp": 123999,
  "session_id": "abc",
  "max_session_age": 24h
}
```

---

## 6.2 Refresh Token

- TTL: 6–24 hours (configurable)
- Stored in:
  - HttpOnly
  - Secure cookie

- Stored in Redis

### Redis Structure

```text
refresh_token:{token_id}
    user_id
    device_id
    fingerprint_hash
    issued_at
    expires_at
```

---

# 7️⃣ Refresh Token Rotation (Mandatory)

## Flow

```text
1. Client → POST /auth/refresh
2. Validate token in Redis
3. Issue NEW access + refresh token
4. Invalidate old refresh token
5. Store new refresh token
```

## Reuse Detection

If old refresh token is reused:

- Invalidate all sessions
- Force re-login
- Log suspicious activity
- Optional: alert user

---

# 8️⃣ Session Age Enforcement

Even if refresh token valid:

If:

```text
Current time - initial login > 24h
```

Then:

- Deny refresh
- Require full login

---

# 9️⃣ Redis Usage

Redis stores:

| Purpose         | Key Example      |
| --------------- | ---------------- |
| Refresh Tokens  | refresh:{id}     |
| Rate Limit      | ratelimit:{ip}   |
| Login Attempts  | attempts:{user}  |
| MFA OTP         | otp:{user}       |
| Device Sessions | session:{device} |

Redis is NOT accessible from frontend.

---

# 🔟 Multi-Factor Authentication (MFA)

## Supported Methods

### TOTP

![Image](https://i.sstatic.net/5auWv.png)

![Image](https://pcf.gallery/assets/images/totp-qr-generator.jpg)

![Image](https://www.auckland.ac.nz/content/auckland/en/about-us/about-the-university/identity-and-access-management/two-factor-authentication/download-authy/_jcr_content/leftpar/imagecomponent_1658681660/image.img.480.low.jpg/1750903973013.png)

![Image](https://www.binghamton.edu/offices/uctd/authy2.png)

- RFC 6238 compliant
- 30-second rotating code
- Stored secret encrypted in DB

---

### WebAuthn / Passkeys (Future-Proof)

![Image](https://curity.io/images/resources/architect/mfa/passkeys/passkeys-entry-screen.jpg?v=20250630)

![Image](https://mintlify.s3.us-west-1.amazonaws.com/auth0/docs/images/cdy7uua7fh8z/4DkewyodXBQ3gncybz7KPI/873d6a3eafb644ee605daa209006d1b3/Docs_Login.png)

![Image](https://m.media-amazon.com/images/I/61aQ0hp1WJL.jpg)

![Image](https://m.media-amazon.com/images/I/51f4b0vrzCL.jpg)

- Passwordless support
- Phishing-resistant
- Public-key based

---

## MFA Flow

```text
1. Password verified
2. If MFA enabled:
       - Generate challenge
       - Store temporary challenge in Redis
3. Verify OTP
4. Issue tokens
```

---

# 1️⃣1️⃣ OAuth 2.1 Integration

Supported Providers:

- Google
- Microsoft
- Facebook
- GitHub

## Flow

Authorization Code Flow + PKCE

```text
1. Redirect to provider
2. User consents
3. Provider returns code
4. Backend exchanges code for token
5. Validate provider token
6. Create or link local user
7. Issue internal JWT
```

Never use implicit flow.

---

# 1️⃣2️⃣ Rate Limiting & Brute Force Protection

## Strategy

- 5 failed attempts → 5-minute lock
- Progressive backoff
- IP + account-based tracking
- Stored in Redis

---

# 1️⃣3️⃣ Risk Engine (Adaptive Authentication)

Check:

- New device
- New country
- VPN detection
- Abnormal login time

If risk high:

- Force MFA
- Deny login
- Notify user

---

# 1️⃣4️⃣ Cookie Security Configuration

All auth cookies:

```http
Set-Cookie: access_token=...
HttpOnly
Secure
SameSite=Strict
Path=/
```

---

# 1️⃣5️⃣ Audit Logging

Log all:

```text
LOGIN_SUCCESS
LOGIN_FAILURE
TOKEN_REFRESH
TOKEN_REUSE_DETECTED
MFA_ENABLED
PASSWORD_CHANGED
ACCOUNT_LOCKED
DEVICE_ADDED
```

Logs must:

- Be immutable
- Sent to SIEM
- Stored for compliance period

---

# 1️⃣6️⃣ Account Lock Strategy

Soft Lock:

- After 5 failed attempts

Hard Lock:

- After 20 failures
- Manual admin unlock required

---

# 1️⃣7️⃣ Extensibility Design

All auth methods must implement:

```text
interface AuthStrategy {
    authenticate(request)
    validate()
    issueToken()
}
```

This allows adding:

- Passwordless
- Hardware tokens
- Enterprise SSO
- Biometric

Without changing core logic.

---

# 1️⃣8️⃣ Threat Model Summary

Protect against:

- MITM
- Replay attacks
- CSRF
- Token theft
- Refresh token replay
- Credential stuffing
- Brute force
- Session fixation

---

# 1️⃣9️⃣ Compliance Ready

Supports:

- PCI DSS
- SOC 2
- ISO 27001
- GDPR

---

# 🔥 Final Architecture Maturity Level

If implemented as above:

Security Level: Enterprise / FinTech Grade
Scalability: Horizontal
Stateless: Yes
Zero Trust Compatible: Yes
Passwordless Ready: Yes

---
