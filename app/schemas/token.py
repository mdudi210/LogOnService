from dataclasses import dataclass
from datetime import datetime


@dataclass
class TokenPayload:
    sub: str
    role: str
    session_id: str
    exp: datetime
