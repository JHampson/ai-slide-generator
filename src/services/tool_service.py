"""Tool library and profile-tool assignment service."""

from typing import Optional

from sqlalchemy.orm import Session

from src.database.models import ConfigHistory, ProfileTool, ToolLibrary, ToolType


class ToolService:
    """
    Manage tool library and profile-tool assignments.

    The tool library contains app-level tool definitions that can be
    assigned to profiles. Each profile can have multiple tools enabled.
    """

    def __init__(self, db: Session):
        self.db = db

    # =========================================================================
    # Tool Library CRUD
    # =========================================================================

    def list_tools(self, include_inactive: bool = False) -> list[ToolLibrary]:
        """
        List all tools in the library.

        Args:
            include_inactive: Include soft-deleted tools

        Returns:
            List of ToolLibrary objects
        """
        query = self.db.query(ToolLibrary)
        if not include_inactive:
            query = query.filter(ToolLibrary.is_active == True)  # noqa: E712
        return query.order_by(ToolLibrary.name).all()

    def list_tools_by_type(
        self, tool_type: ToolType, include_inactive: bool = False
    ) -> list[ToolLibrary]:
        """List tools filtered by type."""
        query = self.db.query(ToolLibrary).filter(ToolLibrary.tool_type == tool_type)
        if not include_inactive:
            query = query.filter(ToolLibrary.is_active == True)  # noqa: E712
        return query.order_by(ToolLibrary.name).all()

    def get_tool(self, tool_id: int) -> Optional[ToolLibrary]:
        """Get a tool by ID."""
        return self.db.query(ToolLibrary).filter(ToolLibrary.id == tool_id).first()

    def get_tool_by_name(self, name: str) -> Optional[ToolLibrary]:
        """Get a tool by name."""
        return self.db.query(ToolLibrary).filter(ToolLibrary.name == name).first()

    def create_tool(
        self,
        tool_type: ToolType,
        name: str,
        config: dict,
        description: str = None,
        user: str = None,
    ) -> ToolLibrary:
        """
        Create a new tool in the library.

        Args:
            tool_type: Type of tool (genie_space, vector_index, etc.)
            name: Unique display name
            config: Type-specific configuration dict
            description: Optional description for LLM
            user: User creating the tool

        Returns:
            Created ToolLibrary object

        Raises:
            IntegrityError: If name already exists
        """
        tool = ToolLibrary(
            tool_type=tool_type.value if isinstance(tool_type, ToolType) else tool_type,
            name=name,
            description=description,
            config=config,
            is_active=True,
            created_by=user or "system",
        )
        self.db.add(tool)
        self.db.commit()
        self.db.refresh(tool)
        return tool

    def update_tool(
        self,
        tool_id: int,
        name: str = None,
        description: str = None,
        config: dict = None,
        user: str = None,
    ) -> ToolLibrary:
        """
        Update a tool in the library.

        Args:
            tool_id: Tool ID
            name: New name (optional)
            description: New description (optional)
            config: New config (optional)
            user: User making the change

        Returns:
            Updated ToolLibrary object

        Raises:
            ValueError: If tool not found
        """
        tool = self.get_tool(tool_id)
        if not tool:
            raise ValueError(f"Tool {tool_id} not found")

        if name is not None:
            tool.name = name
        if description is not None:
            tool.description = description
        if config is not None:
            tool.config = config

        self.db.commit()
        self.db.refresh(tool)
        return tool

    def delete_tool(self, tool_id: int, user: str = None) -> None:
        """
        Soft-delete a tool from the library.

        Args:
            tool_id: Tool ID
            user: User making the change

        Raises:
            ValueError: If tool not found
        """
        tool = self.get_tool(tool_id)
        if not tool:
            raise ValueError(f"Tool {tool_id} not found")

        tool.is_active = False
        self.db.commit()

    def hard_delete_tool(self, tool_id: int) -> None:
        """
        Permanently delete a tool and all profile assignments.

        Args:
            tool_id: Tool ID

        Raises:
            ValueError: If tool not found
        """
        tool = self.get_tool(tool_id)
        if not tool:
            raise ValueError(f"Tool {tool_id} not found")

        self.db.delete(tool)
        self.db.commit()

    # =========================================================================
    # Profile Tool Assignments
    # =========================================================================

    def get_profile_tools(self, profile_id: int) -> list[ProfileTool]:
        """
        Get all tools assigned to a profile.

        Args:
            profile_id: Profile ID

        Returns:
            List of ProfileTool objects with tool relationship loaded
        """
        return (
            self.db.query(ProfileTool)
            .filter(ProfileTool.profile_id == profile_id)
            .order_by(ProfileTool.priority)
            .all()
        )

    def get_enabled_profile_tools(self, profile_id: int) -> list[ProfileTool]:
        """
        Get only enabled tools for a profile.

        Args:
            profile_id: Profile ID

        Returns:
            List of enabled ProfileTool objects
        """
        return (
            self.db.query(ProfileTool)
            .join(ToolLibrary)
            .filter(
                ProfileTool.profile_id == profile_id,
                ProfileTool.is_enabled == True,  # noqa: E712
                ToolLibrary.is_active == True,  # noqa: E712
            )
            .order_by(ProfileTool.priority)
            .all()
        )

    def get_profile_tool(self, profile_id: int, tool_id: int) -> Optional[ProfileTool]:
        """Get a specific profile-tool assignment."""
        return (
            self.db.query(ProfileTool)
            .filter(
                ProfileTool.profile_id == profile_id,
                ProfileTool.tool_id == tool_id,
            )
            .first()
        )

    def add_tool_to_profile(
        self,
        profile_id: int,
        tool_id: int,
        is_enabled: bool = True,
        description_override: str = None,
        priority: int = 0,
        user: str = None,
    ) -> ProfileTool:
        """
        Assign a tool from the library to a profile.

        Args:
            profile_id: Profile ID
            tool_id: Tool ID from library
            is_enabled: Whether tool is enabled for this profile
            description_override: Optional profile-specific description
            priority: Tool ordering (lower = first)
            user: User making the change

        Returns:
            Created ProfileTool object

        Raises:
            ValueError: If tool not found
            IntegrityError: If assignment already exists
        """
        tool = self.get_tool(tool_id)
        if not tool:
            raise ValueError(f"Tool {tool_id} not found")

        profile_tool = ProfileTool(
            profile_id=profile_id,
            tool_id=tool_id,
            is_enabled=is_enabled,
            description_override=description_override,
            priority=priority,
        )
        self.db.add(profile_tool)

        # Log to history
        history = ConfigHistory(
            profile_id=profile_id,
            domain="tools",
            action="add",
            changed_by=user or "system",
            changes={
                "tool_id": {"old": None, "new": tool_id},
                "tool_name": {"old": None, "new": tool.name},
                "tool_type": {"old": None, "new": tool.tool_type},
            },
        )
        self.db.add(history)

        self.db.commit()
        self.db.refresh(profile_tool)
        return profile_tool

    def update_profile_tool(
        self,
        profile_id: int,
        tool_id: int,
        is_enabled: bool = None,
        description_override: str = None,
        priority: int = None,
        user: str = None,
    ) -> ProfileTool:
        """
        Update a profile-tool assignment.

        Args:
            profile_id: Profile ID
            tool_id: Tool ID
            is_enabled: New enabled state (optional)
            description_override: New description override (optional)
            priority: New priority (optional)
            user: User making the change

        Returns:
            Updated ProfileTool object

        Raises:
            ValueError: If assignment not found
        """
        profile_tool = self.get_profile_tool(profile_id, tool_id)
        if not profile_tool:
            raise ValueError(f"Tool {tool_id} not assigned to profile {profile_id}")

        changes = {}

        if is_enabled is not None and is_enabled != profile_tool.is_enabled:
            changes["is_enabled"] = {"old": profile_tool.is_enabled, "new": is_enabled}
            profile_tool.is_enabled = is_enabled

        if description_override is not None:
            if description_override != profile_tool.description_override:
                changes["description_override"] = {
                    "old": profile_tool.description_override,
                    "new": description_override,
                }
                profile_tool.description_override = description_override

        if priority is not None and priority != profile_tool.priority:
            changes["priority"] = {"old": profile_tool.priority, "new": priority}
            profile_tool.priority = priority

        if changes:
            history = ConfigHistory(
                profile_id=profile_id,
                domain="tools",
                action="update",
                changed_by=user or "system",
                changes=changes,
            )
            self.db.add(history)

        self.db.commit()
        self.db.refresh(profile_tool)
        return profile_tool

    def remove_tool_from_profile(self, profile_id: int, tool_id: int, user: str = None) -> None:
        """
        Remove a tool assignment from a profile.

        Args:
            profile_id: Profile ID
            tool_id: Tool ID
            user: User making the change

        Raises:
            ValueError: If assignment not found
        """
        profile_tool = self.get_profile_tool(profile_id, tool_id)
        if not profile_tool:
            raise ValueError(f"Tool {tool_id} not assigned to profile {profile_id}")

        tool = profile_tool.tool

        # Log to history
        history = ConfigHistory(
            profile_id=profile_id,
            domain="tools",
            action="remove",
            changed_by=user or "system",
            changes={
                "tool_id": {"old": tool_id, "new": None},
                "tool_name": {"old": tool.name if tool else None, "new": None},
            },
        )
        self.db.add(history)
        self.db.flush()

        self.db.delete(profile_tool)
        self.db.commit()

    def reorder_profile_tools(
        self, profile_id: int, tool_ids: list[int], user: str = None
    ) -> list[ProfileTool]:
        """
        Reorder tools for a profile.

        Args:
            profile_id: Profile ID
            tool_ids: List of tool IDs in desired order
            user: User making the change

        Returns:
            Updated list of ProfileTool objects
        """
        for priority, tool_id in enumerate(tool_ids):
            profile_tool = self.get_profile_tool(profile_id, tool_id)
            if profile_tool:
                profile_tool.priority = priority

        self.db.commit()
        return self.get_profile_tools(profile_id)
