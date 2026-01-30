"""Profile-tool junction model for assigning tools to profiles."""

from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from src.core.database import Base


class ProfileTool(Base):
    """
    Junction table linking profiles to tools from the library.

    Allows:
    - Multiple tools per profile
    - Per-profile enable/disable toggle
    - Profile-specific description override for LLM
    - Tool ordering via priority field
    """

    __tablename__ = "profile_tools"

    id = Column(Integer, primary_key=True)
    profile_id = Column(
        Integer, ForeignKey("config_profiles.id", ondelete="CASCADE"), nullable=False
    )
    tool_id = Column(Integer, ForeignKey("tool_library.id", ondelete="CASCADE"), nullable=False)

    is_enabled = Column(Boolean, default=True, nullable=False)  # Per-profile toggle
    description_override = Column(Text)  # Optional profile-specific description
    priority = Column(Integer, default=0, nullable=False)  # Tool ordering

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    profile = relationship("ConfigProfile", back_populates="profile_tools")
    tool = relationship("ToolLibrary", back_populates="profile_tools")

    # Constraints and indexes
    __table_args__ = (
        UniqueConstraint("profile_id", "tool_id", name="uq_profile_tools_profile_tool"),
        Index("idx_profile_tools_profile", "profile_id"),
        Index("idx_profile_tools_tool", "tool_id"),
    )

    def __repr__(self):
        return f"<ProfileTool(profile_id={self.profile_id}, tool_id={self.tool_id}, enabled={self.is_enabled})>"
