"""Pydantic schemas for tool library and profile tools APIs."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ToolLibraryBase(BaseModel):
    """Base schema for tool library items."""

    tool_type: str = Field(
        description="Tool type: genie_space, vector_index, mcp_server, uc_function"
    )
    name: str = Field(description="Unique tool name", max_length=100)
    description: Optional[str] = Field(None, description="Description for LLM tool binding")
    config: dict = Field(description="Type-specific configuration")


class ToolLibraryCreate(ToolLibraryBase):
    """Schema for creating a new tool."""

    pass


class ToolLibraryUpdate(BaseModel):
    """Schema for updating an existing tool."""

    name: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    config: Optional[dict] = None


class ToolLibraryResponse(ToolLibraryBase):
    """Schema for tool library response."""

    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    created_by: Optional[str] = None

    model_config = {"from_attributes": True}


class ProfileToolBase(BaseModel):
    """Base schema for profile tool assignments."""

    tool_id: int = Field(description="ID of tool from library")
    is_enabled: bool = Field(True, description="Whether tool is enabled for this profile")
    description_override: Optional[str] = Field(
        None, description="Profile-specific description override"
    )
    priority: int = Field(0, description="Tool ordering (lower = first)")


class ProfileToolCreate(ProfileToolBase):
    """Schema for adding a tool to a profile."""

    pass


class ProfileToolUpdate(BaseModel):
    """Schema for updating a profile tool assignment."""

    is_enabled: Optional[bool] = None
    description_override: Optional[str] = None
    priority: Optional[int] = None


class ProfileToolResponse(ProfileToolBase):
    """Schema for profile tool response."""

    id: int
    profile_id: int
    created_at: datetime

    # Include tool details
    tool_name: str
    tool_type: str
    tool_description: Optional[str] = None
    tool_config: dict

    model_config = {"from_attributes": True}


class ToolReorderRequest(BaseModel):
    """Schema for reordering tools."""

    tool_ids: list[int] = Field(description="Tool IDs in desired order")


class ToolValidateRequest(BaseModel):
    """Schema for validating tool configuration."""

    tool_type: str
    config: dict


class ToolValidateResponse(BaseModel):
    """Schema for tool validation response."""

    valid: bool
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
