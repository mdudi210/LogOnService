from pydantic import BaseModel, Field


class MFASetupResponse(BaseModel):
    secret: str
    provisioning_uri: str


class MFAVerifyRequest(BaseModel):
    code: str = Field(min_length=6, max_length=8)


class MFAVerifyResponse(BaseModel):
    message: str


class MFAEmailSetupResponse(BaseModel):
    message: str
    expires_in_seconds: int


class MFAOptionsResponse(BaseModel):
    available_methods: list[str]
    enabled_methods: list[str]


class MFAEmailVerifyRequest(BaseModel):
    code: str = Field(min_length=6, max_length=8)
