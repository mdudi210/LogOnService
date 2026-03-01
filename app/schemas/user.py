from dataclasses import dataclass


@dataclass
class UserSummary:
    id: str
    email: str
    username: str
    role: str
    is_active: bool
