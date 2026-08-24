"""Request/response models for HMS Web authentication."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.access import UserPermissionRead, UserRoleRead


class LoginRequest(BaseModel):
    """HMS Web login. `username` is `app_user.user_name`, the only unique
    login identifier in the schema (13/13 distinct in the seeded data)."""

    username: str = Field(min_length=1, max_length=100, examples=["arjun.menon"])
    password: str = Field(min_length=1, max_length=256)

    # Keep the password out of tracebacks and logs.
    model_config = ConfigDict(json_schema_extra={"example": {
        "username": "arjun.menon", "password": "<provisioned-password>"
    }})

    def __repr__(self) -> str:  # pragma: no cover - defensive
        return f"LoginRequest(username={self.username!r}, password='***')"

    __str__ = __repr__


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = Field(default="bearer", examples=["bearer"])
    expires_in: int = Field(description="Seconds until the token expires")


class CurrentUser(BaseModel):
    """The authenticated HMS Web user.

    Role and permission data is read from PostgreSQL on every request, never
    from the token.
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_name: str | None = None
    first_name: str
    last_name: str | None = None
    email: str | None = None
    is_staff: int | None = None
    platform: str = Field(examples=["hms_web"])
    role_types: list[str] = Field(examples=[["admin"]])
    roles: list[UserRoleRead]
    facility_ids: list[uuid.UUID]
    permissions: list[UserPermissionRead]
