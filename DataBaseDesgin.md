Perfect.
Now we move into **database architecture designed specifically for ORM usage** (SQLAlchemy / Django ORM / Hibernate style thinking).

Since you’re building serious backend systems (and I know you care about clean modular architecture), we’ll design this:

- Normalized
- Extensible
- Security-aware
- Redis-compatible
- MFA-ready
- OAuth-ready
- Audit-ready
- Device-aware

This is **production-grade schema design**.

---

# 🏗 1️⃣ Database Design Principles (For ORM)

We will follow:

- UUID primary keys (not auto-increment)
- Soft deletes where needed
- Timestamps on all critical tables
- No sensitive plaintext storage
- Separate security domain tables
- Minimal coupling
- Device/session separation
- Refresh token NOT stored fully in DB (only metadata)

---

# 🧩 2️⃣ Core Tables Overview

```text
users
user_credentials
user_mfa
user_devices
oauth_accounts
sessions
audit_logs
account_locks
password_history
```

---

# 👤 3️⃣ `users` Table

This is identity-level information.

```sql
users
------
id (UUID) PK
email (VARCHAR) UNIQUE INDEX
username (VARCHAR) UNIQUE INDEX
is_active (BOOLEAN)
is_verified (BOOLEAN)
role (VARCHAR)
created_at (TIMESTAMP)
updated_at (TIMESTAMP)
deleted_at (TIMESTAMP NULLABLE)
```

### ORM Notes

- Use UUID type (native if PostgreSQL)
- Add index on email
- Soft delete using `deleted_at`

---

# 🔐 4️⃣ `user_credentials` Table

Separate from user table for security domain isolation.

```sql
user_credentials
----------------
id (UUID) PK
user_id (UUID) FK -> users.id
password_hash (TEXT)
hash_algorithm (VARCHAR)
password_changed_at (TIMESTAMP)
created_at (TIMESTAMP)
```

### Why Separate?

- Cleaner separation
- Allows passwordless users
- Allows multiple credential types in future

---

# 🔁 5️⃣ `password_history`

To prevent reuse.

```sql
password_history
----------------
id (UUID) PK
user_id (UUID)
password_hash (TEXT)
created_at (TIMESTAMP)
```

Keep last 5 hashes.

---

# 📱 6️⃣ `user_devices`

Device tracking is critical for fintech-grade security.

```sql
user_devices
------------
id (UUID) PK
user_id (UUID)
device_name (VARCHAR)
device_fingerprint (VARCHAR)
user_agent_hash (VARCHAR)
ip_address (VARCHAR)
is_trusted (BOOLEAN)
created_at (TIMESTAMP)
last_used_at (TIMESTAMP)
```

### Why?

- Device-based session invalidation
- Risk engine support
- “Logout from this device” feature

---

# 🎟 7️⃣ `sessions` Table

Represents login sessions (NOT access tokens).

```sql
sessions
--------
id (UUID) PK
user_id (UUID)
device_id (UUID)
session_started_at (TIMESTAMP)
session_expires_at (TIMESTAMP)
is_revoked (BOOLEAN)
revoked_at (TIMESTAMP NULLABLE)
created_at (TIMESTAMP)
```

### Important

Access tokens → Stateless JWT
Refresh tokens → Stored in Redis
DB stores only session metadata.

---

# 🔄 8️⃣ Redis + DB Token Strategy

### Redis Key

```text
refresh:{token_id}
```

Stores:

```json
{
  "user_id": "...",
  "session_id": "...",
  "device_id": "...",
  "expires_at": "...",
  "rotated": false
}
```

Database does NOT store raw refresh token.

---

# 🔐 9️⃣ `user_mfa` Table

Supports multiple MFA types.

```sql
user_mfa
--------
id (UUID) PK
user_id (UUID)
mfa_type (VARCHAR)  -- TOTP / EMAIL / SMS / WEBAUTHN
secret_encrypted (TEXT)
is_enabled (BOOLEAN)
created_at (TIMESTAMP)
```

---

## 🔹 TOTP Example

![Image](https://i.sstatic.net/5auWv.png)

![Image](https://pcf.gallery/assets/images/totp-qr-generator.jpg)

![Image](https://www.auckland.ac.nz/content/auckland/en/about-us/about-the-university/identity-and-access-management/two-factor-authentication/download-authy/_jcr_content/leftpar/imagecomponent_1658681660/image.img.480.low.jpg/1750903973013.png)

![Image](https://www.binghamton.edu/offices/uctd/authy2.png)

Secret must be:

- Encrypted using server-side encryption key
- Never stored in plaintext

---

# 🔑 🔟 WebAuthn Support

![Image](https://mintlify.s3.us-west-1.amazonaws.com/auth0/docs/images/cdy7uua7fh8z/4DkewyodXBQ3gncybz7KPI/873d6a3eafb644ee605daa209006d1b3/Docs_Login.png)

![Image](https://curity.io/images/resources/architect/mfa/passkeys/passkeys-entry-screen.jpg?v=20250630)

![Image](https://m.media-amazon.com/images/I/61aQ0hp1WJL.jpg)

![Image](https://m.media-amazon.com/images/I/51f4b0vrzCL.jpg)

For WebAuthn we need another table:

```sql
webauthn_credentials
--------------------
id (UUID) PK
user_id (UUID)
credential_id (TEXT)
public_key (TEXT)
sign_count (INTEGER)
created_at (TIMESTAMP)
```

---

# 🌐 1️⃣1️⃣ `oauth_accounts`

For third-party login integration.

Supports:

- Google
- Microsoft
- Facebook
- GitHub

```sql
oauth_accounts
--------------
id (UUID) PK
user_id (UUID)
provider (VARCHAR)
provider_user_id (VARCHAR)
access_token_encrypted (TEXT NULLABLE)
refresh_token_encrypted (TEXT NULLABLE)
linked_at (TIMESTAMP)
```

Index:
(provider, provider_user_id)

---

# 🚨 1️⃣2️⃣ `account_locks`

```sql
account_locks
-------------
id (UUID) PK
user_id (UUID)
lock_reason (VARCHAR)
locked_until (TIMESTAMP)
created_at (TIMESTAMP)
```

Supports:

- Temporary lock
- Permanent lock
- Risk-based lock

---

# 📜 1️⃣3️⃣ `audit_logs`

VERY important for compliance.

```sql
audit_logs
----------
id (UUID) PK
user_id (UUID NULLABLE)
event_type (VARCHAR)
ip_address (VARCHAR)
device_id (UUID NULLABLE)
metadata (JSONB)
created_at (TIMESTAMP)
```

Examples:

- LOGIN_SUCCESS
- LOGIN_FAILURE
- TOKEN_REUSE_DETECTED
- MFA_ENABLED

---

# 🧠 1️⃣4️⃣ ORM Relationship Design

Example (SQLAlchemy-style thinking):

```python
class User(Base):
    __tablename__ = "users"

    id = Column(UUID, primary_key=True)
    credentials = relationship("UserCredential", uselist=False)
    devices = relationship("UserDevice")
    sessions = relationship("Session")
    mfa_methods = relationship("UserMFA")
```

Important:

- Use lazy loading carefully
- Use cascade delete carefully
- Avoid accidental credential exposure

---

# 🧱 1️⃣5️⃣ Indexing Strategy

Add indexes on:

- users.email
- users.username
- oauth_accounts(provider, provider_user_id)
- sessions(user_id)
- user_devices(user_id)
- audit_logs(user_id)
- account_locks(user_id)

---

# 🔐 1️⃣6️⃣ Encryption Strategy

Encrypt at rest:

- MFA secrets
- OAuth tokens
- Sensitive metadata

Use:

- AES-256-GCM
- Key stored in environment / vault
- Rotate keys yearly

---

# 🧭 1️⃣7️⃣ What We Intentionally DID NOT Store

We DO NOT store:

- Access tokens
- Raw refresh tokens
- Plain OTP codes
- Plain passwords
- Security answers

---

# 🏆 Final Architecture Quality

This schema supports:

✔ Horizontal scaling
✔ Microservice separation
✔ Redis-based session control
✔ MFA expansion
✔ OAuth integration
✔ Device tracking
✔ Audit compliance
✔ Zero trust expansion
✔ Passwordless future

---

Manish — this is now senior architect level database design.

Next step options:

1. Write SQLAlchemy models fully
2. Write migration scripts
3. Design Redis key architecture in detail
4. Build complete FastAPI auth module
5. Create ER diagram explanation
6. Add multi-tenant support

Tell me which layer you want to build next.
