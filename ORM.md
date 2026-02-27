Perfect.
Now we design **production-grade SQLAlchemy models for PostgreSQL**, aligned with the architecture we defined.

We will:

- Use **PostgreSQL UUID type**
- Use `JSONB`
- Use proper indexing
- Use secure defaults
- Add relationships
- Prepare for migrations (Alembic-ready)
- Avoid security mistakes

This will be written for:

- SQLAlchemy 2.x style
- Async-ready compatible
- Clean modular design

---

# 📦 0️⃣ Dependencies

```bash
pip install sqlalchemy psycopg2-binary
```

If async:

```bash
pip install asyncpg
```

---

# 🏗 1️⃣ Base Setup

```python
# models/base.py

import uuid
from datetime import datetime
from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.dialects.postgresql import UUID

# Naming convention for migrations
convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s"
}

metadata = MetaData(naming_convention=convention)

class Base(DeclarativeBase):
    metadata = metadata


def generate_uuid():
    return uuid.uuid4()
```

---

# 👤 2️⃣ User Model

```python
# models/user.py

from sqlalchemy import String, Boolean, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
from .base import Base, generate_uuid

class User(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=generate_uuid
    )

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False
    )

    username: Mapped[str] = mapped_column(
        String(150),
        unique=True,
        index=True,
        nullable=False
    )

    role: Mapped[str] = mapped_column(
        String(50),
        default="user"
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True
    )

    is_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    deleted_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=True
    )

    # Relationships
    credentials = relationship("UserCredential", back_populates="user", uselist=False)
    devices = relationship("UserDevice", back_populates="user")
    sessions = relationship("Session", back_populates="user")
    mfa_methods = relationship("UserMFA", back_populates="user")
    oauth_accounts = relationship("OAuthAccount", back_populates="user")
```

---

# 🔐 3️⃣ UserCredential Model

```python
# models/user_credentials.py

from sqlalchemy import ForeignKey, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
from .base import Base, generate_uuid

class UserCredential(Base):
    __tablename__ = "user_credentials"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=generate_uuid
    )

    user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True
    )

    password_hash: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )

    hash_algorithm: Mapped[str] = mapped_column(
        Text,
        default="argon2id"
    )

    password_changed_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow
    )

    user = relationship("User", back_populates="credentials")
```

---

# 📱 4️⃣ UserDevice Model

```python
# models/user_device.py

from sqlalchemy import ForeignKey, String, Boolean, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
from .base import Base, generate_uuid

class UserDevice(Base):
    __tablename__ = "user_devices"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=generate_uuid
    )

    user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE")
    )

    device_name: Mapped[str] = mapped_column(String(255))
    device_fingerprint: Mapped[str] = mapped_column(String(255), index=True)
    user_agent_hash: Mapped[str] = mapped_column(String(255))
    ip_address: Mapped[str] = mapped_column(String(50))

    is_trusted: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_used_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="devices")
```

---

# 🎟 5️⃣ Session Model

```python
# models/session.py

from sqlalchemy import ForeignKey, Boolean, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
from .base import Base, generate_uuid

class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=generate_uuid
    )

    user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True
    )

    device_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("user_devices.id", ondelete="SET NULL"),
        nullable=True
    )

    session_started_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow
    )

    session_expires_at: Mapped[datetime] = mapped_column(
        DateTime
    )

    is_revoked: Mapped[bool] = mapped_column(
        Boolean,
        default=False
    )

    revoked_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=True
    )

    user = relationship("User", back_populates="sessions")
```

---

# 🔐 6️⃣ UserMFA Model

```python
# models/user_mfa.py

from sqlalchemy import ForeignKey, String, Boolean, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
from .base import Base, generate_uuid

class UserMFA(Base):
    __tablename__ = "user_mfa"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=generate_uuid
    )

    user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE")
    )

    mfa_type: Mapped[str] = mapped_column(String(50))
    secret_encrypted: Mapped[str] = mapped_column(Text)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="mfa_methods")
```

---

# 🌐 7️⃣ OAuthAccount Model

```python
# models/oauth_account.py

from sqlalchemy import ForeignKey, String, DateTime, Text, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
from .base import Base, generate_uuid

class OAuthAccount(Base):
    __tablename__ = "oauth_accounts"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=generate_uuid
    )

    user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE")
    )

    provider: Mapped[str] = mapped_column(String(50))
    provider_user_id: Mapped[str] = mapped_column(String(255))

    access_token_encrypted: Mapped[str] = mapped_column(Text, nullable=True)
    refresh_token_encrypted: Mapped[str] = mapped_column(Text, nullable=True)

    linked_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="oauth_accounts")

    __table_args__ = (
        Index("ix_provider_provider_user_id", "provider", "provider_user_id", unique=True),
    )
```

---

# 📜 8️⃣ AuditLog Model (Postgres JSONB)

```python
# models/audit_log.py

from sqlalchemy import ForeignKey, String, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB
from datetime import datetime
from .base import Base, generate_uuid

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=generate_uuid
    )

    user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    event_type: Mapped[str] = mapped_column(String(100))
    ip_address: Mapped[str] = mapped_column(String(50))
    metadata: Mapped[dict] = mapped_column(JSONB)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
```

---

# 🏆 Final Result

This model set is:

- PostgreSQL optimized
- ORM clean
- Security aligned
- MFA ready
- OAuth ready
- Device aware
- Session aware
- Audit compliant
- Migration safe

---

If you want next:

- I can build Alembic migration structure
- Add async SQLAlchemy setup
- Build repository layer
- Implement login service logic
- Add multi-tenant support
- Add row-level security (Postgres RLS)

Tell me what we build next.
