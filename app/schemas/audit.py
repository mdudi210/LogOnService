from typing import Any, List, Optional

from pydantic import BaseModel


class AuditEventSummary(BaseModel):
    id: str
    user_id: Optional[str]
    event_type: str
    ip_address: Optional[str]
    user_agent: Optional[str]
    metadata: dict[str, Any]
    created_at: str


class AuditEventsResponse(BaseModel):
    events: List[AuditEventSummary]

