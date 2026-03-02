from pydantic import BaseModel


class UserSummary(BaseModel):
    id: str
    email: str
    username: str
    role: str
    is_active: bool
