"""Tool library model for app-level tool definitions."""

from datetime import datetime
from enum import Enum

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import relationship

from src.core.database import Base


class ToolType(str, Enum):
    """Supported tool types."""

    GENIE_SPACE = "genie_space"
    VECTOR_INDEX = "vector_index"
    MCP_SERVER = "mcp_server"
    UC_FUNCTION = "uc_function"


class ToolLibrary(Base):
    """
    App-level tool library.

    Defines available tools that can be assigned to profiles. Each tool has
    a type and type-specific configuration stored as JSON.

    Config schemas by type:
    - genie_space: {"space_id": "...", "space_name": "..."}
    - vector_index: {"endpoint_name": "...", "index_name": "...", "num_results": 5}
    - mcp_server: {"connection_name": "..."} (Unity Catalog connection name)
    - uc_function: {"catalog": "...", "schema": "...", "function_name": "..."}
    """

    __tablename__ = "tool_library"

    id = Column(Integer, primary_key=True)
    tool_type = Column(String(50), nullable=False)  # ToolType enum value
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text)  # Used in LLM tool description
    config = Column(JSON, nullable=False)  # Type-specific configuration
    is_active = Column(Boolean, default=True, nullable=False)  # Soft delete

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    created_by = Column(String(255))

    # Relationship to profiles via junction table
    profile_tools = relationship("ProfileTool", back_populates="tool", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<ToolLibrary(id={self.id}, name='{self.name}', type='{self.tool_type}')>"
