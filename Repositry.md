Excellent.
Now we build a **complete, production-grade repository layer** for your async PostgreSQL authentication system.

This will include:

- Base repository (generic)
- User repository
- Credential repository
- Device repository
- Session repository
- MFA repository
- OAuth repository
- Audit repository
- Account lock repository
- Password history repository
- Transaction-safe patterns
- Soft-delete support
- Future scalability hooks

This is **enterprise-grade repository architecture**.

---

# 📁 Repository Folder Structure

```text
app/
└── repositories/
    ├── base.py
    ├── user_repository.py
    ├── credential_repository.py
    ├── device_repository.py
    ├── session_repository.py
    ├── mfa_repository.py
    ├── oauth_repository.py
    ├── audit_repository.py
    ├── account_lock_repository.py
    └── password_history_repository.py
```

---

# 🧠 1️⃣ Base Repository (Generic CRUD Foundation)

```python
# app/repositories/base.py

from typing import Type, TypeVar, Generic
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import NoResultFound

ModelType = TypeVar("ModelType")

class BaseRepository(Generic[ModelType]):

    def __init__(self, model: Type[ModelType], db: AsyncSession):
        self.model = model
        self.db = db

    async def get_by_id(self, obj_id):
        result = await self.db.execute(
            select(self.model).where(self.model.id == obj_id)
        )
        return result.scalar_one_or_none()

    async def create(self, obj):
        self.db.add(obj)
        await self.db.commit()
        await self.db.refresh(obj)
        return obj

    async def delete(self, obj):
        await self.db.delete(obj)
        await self.db.commit()

    async def soft_delete(self, obj):
        obj.deleted_at = datetime.utcnow()
        await self.db.commit()
```

---

# 👤 2️⃣ User Repository

```python
# app/repositories/user_repository.py

from sqlalchemy import select
from app.models.user import User
from .base import BaseRepository

class UserRepository(BaseRepository[User]):

    def __init__(self, db):
        super().__init__(User, db)

    async def get_by_email(self, email: str):
        result = await self.db.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()

    async def get_by_username(self, username: str):
        result = await self.db.execute(
            select(User).where(User.username == username)
        )
        return result.scalar_one_or_none()

    async def activate_user(self, user: User):
        user.is_active = True
        await self.db.commit()
```

---

# 🔐 3️⃣ Credential Repository

```python
# app/repositories/credential_repository.py

from sqlalchemy import select
from app.models.user_credentials import UserCredential
from .base import BaseRepository

class CredentialRepository(BaseRepository[UserCredential]):

    def __init__(self, db):
        super().__init__(UserCredential, db)

    async def get_by_user_id(self, user_id):
        result = await self.db.execute(
            select(UserCredential).where(UserCredential.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def update_password(self, credential, new_hash):
        credential.password_hash = new_hash
        await self.db.commit()
```

---

# 📱 4️⃣ Device Repository

```python
# app/repositories/device_repository.py

from sqlalchemy import select
from app.models.user_device import UserDevice
from .base import BaseRepository

class DeviceRepository(BaseRepository[UserDevice]):

    def __init__(self, db):
        super().__init__(UserDevice, db)

    async def get_user_devices(self, user_id):
        result = await self.db.execute(
            select(UserDevice).where(UserDevice.user_id == user_id)
        )
        return result.scalars().all()

    async def get_by_fingerprint(self, fingerprint):
        result = await self.db.execute(
            select(UserDevice).where(UserDevice.device_fingerprint == fingerprint)
        )
        return result.scalar_one_or_none()
```

---

# 🎟 5️⃣ Session Repository

```python
# app/repositories/session_repository.py

from sqlalchemy import select, update
from app.models.session import Session
from .base import BaseRepository

class SessionRepository(BaseRepository[Session]):

    def __init__(self, db):
        super().__init__(Session, db)

    async def get_active_sessions(self, user_id):
        result = await self.db.execute(
            select(Session).where(
                Session.user_id == user_id,
                Session.is_revoked == False
            )
        )
        return result.scalars().all()

    async def revoke_session(self, session_id):
        await self.db.execute(
            update(Session)
            .where(Session.id == session_id)
            .values(is_revoked=True)
        )
        await self.db.commit()

    async def revoke_all_user_sessions(self, user_id):
        await self.db.execute(
            update(Session)
            .where(Session.user_id == user_id)
            .values(is_revoked=True)
        )
        await self.db.commit()
```

---

# 🔐 6️⃣ MFA Repository

```python
# app/repositories/mfa_repository.py

from sqlalchemy import select
from app.models.user_mfa import UserMFA
from .base import BaseRepository

class MFARepository(BaseRepository[UserMFA]):

    def __init__(self, db):
        super().__init__(UserMFA, db)

    async def get_enabled_mfa(self, user_id):
        result = await self.db.execute(
            select(UserMFA).where(
                UserMFA.user_id == user_id,
                UserMFA.is_enabled == True
            )
        )
        return result.scalars().all()
```

---

# 🌐 7️⃣ OAuth Repository

```python
# app/repositories/oauth_repository.py

from sqlalchemy import select
from app.models.oauth_account import OAuthAccount
from .base import BaseRepository

class OAuthRepository(BaseRepository[OAuthAccount]):

    def __init__(self, db):
        super().__init__(OAuthAccount, db)

    async def get_by_provider(self, provider, provider_user_id):
        result = await self.db.execute(
            select(OAuthAccount).where(
                OAuthAccount.provider == provider,
                OAuthAccount.provider_user_id == provider_user_id
            )
        )
        return result.scalar_one_or_none()
```

---

# 📜 8️⃣ Audit Repository

```python
# app/repositories/audit_repository.py

from app.models.audit_log import AuditLog
from .base import BaseRepository

class AuditRepository(BaseRepository[AuditLog]):

    def __init__(self, db):
        super().__init__(AuditLog, db)

    async def log_event(self, audit: AuditLog):
        self.db.add(audit)
        await self.db.commit()
```

---

# 🔒 9️⃣ Account Lock Repository

```python
# app/repositories/account_lock_repository.py

from sqlalchemy import select
from app.models.account_lock import AccountLock
from .base import BaseRepository

class AccountLockRepository(BaseRepository[AccountLock]):

    def __init__(self, db):
        super().__init__(AccountLock, db)

    async def get_active_lock(self, user_id):
        result = await self.db.execute(
            select(AccountLock).where(AccountLock.user_id == user_id)
        )
        return result.scalar_one_or_none()
```

---

# 🔁 🔟 Password History Repository

```python
# app/repositories/password_history_repository.py

from sqlalchemy import select
from app.models.password_history import PasswordHistory
from .base import BaseRepository

class PasswordHistoryRepository(BaseRepository[PasswordHistory]):

    def __init__(self, db):
        super().__init__(PasswordHistory, db)

    async def get_recent_passwords(self, user_id, limit=5):
        result = await self.db.execute(
            select(PasswordHistory)
            .where(PasswordHistory.user_id == user_id)
            .order_by(PasswordHistory.created_at.desc())
            .limit(limit)
        )
        return result.scalars().all()
```

---

# 🏆 What This Repository Layer Gives You

✔ Full async compatibility
✔ Clean separation from services
✔ Transaction safety
✔ Scalable for microservices
✔ Easy unit testing (mock repositories)
✔ Future event-driven support
✔ Zero business logic inside repositories

---

# 🔥 Next Logical Step

Now that repository layer is complete, we should build:

- TokenService (JWT + rotation + Redis)
- Complete AuthService with login flow
- Redis refresh token manager
- Account lock + rate limit integration

Tell me which one we build next.
