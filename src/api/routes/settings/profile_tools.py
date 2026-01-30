"""
Profile tools API endpoints.

Manages tool assignments to profiles from the tool library.
"""

import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.api.schemas.settings.tools import (
    ProfileToolCreate,
    ProfileToolResponse,
    ProfileToolUpdate,
    ToolReorderRequest,
)
from src.core.database import get_db
from src.database.models import ConfigProfile, ProfileTool
from src.services.tool_service import ToolService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["profile-tools"])


def get_tool_service(db: Session = Depends(get_db)) -> ToolService:
    """Dependency to get ToolService."""
    return ToolService(db)


def _to_response(pt: ProfileTool) -> ProfileToolResponse:
    """Convert ProfileTool to response schema."""
    return ProfileToolResponse(
        id=pt.id,
        profile_id=pt.profile_id,
        tool_id=pt.tool_id,
        is_enabled=pt.is_enabled,
        description_override=pt.description_override,
        priority=pt.priority,
        created_at=pt.created_at,
        tool_name=pt.tool.name,
        tool_type=pt.tool.tool_type,
        tool_description=pt.tool.description,
        tool_config=pt.tool.config,
    )


@router.get("/profiles/{profile_id}/tools", response_model=List[ProfileToolResponse])
def list_profile_tools(
    profile_id: int,
    db: Session = Depends(get_db),
    service: ToolService = Depends(get_tool_service),
):
    """
    List all tools assigned to a profile.

    Returns tools in priority order (lowest priority first).
    """
    # Verify profile exists
    profile = db.query(ConfigProfile).filter_by(id=profile_id).first()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Profile {profile_id} not found",
        )

    try:
        profile_tools = service.get_profile_tools(profile_id)
        return [_to_response(pt) for pt in profile_tools]
    except Exception as e:
        logger.error(f"Error listing profile tools: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list profile tools: {str(e)}",
        )


@router.post(
    "/profiles/{profile_id}/tools",
    response_model=ProfileToolResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_tool_to_profile(
    profile_id: int,
    data: ProfileToolCreate,
    db: Session = Depends(get_db),
    service: ToolService = Depends(get_tool_service),
):
    """
    Add a tool from the library to a profile.

    The tool must exist in the tool library.
    """
    # Verify profile exists
    profile = db.query(ConfigProfile).filter_by(id=profile_id).first()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Profile {profile_id} not found",
        )

    try:
        profile_tool = service.add_tool_to_profile(
            profile_id=profile_id,
            tool_id=data.tool_id,
            is_enabled=data.is_enabled,
            description_override=data.description_override,
            priority=data.priority,
        )
        return _to_response(profile_tool)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error adding tool to profile: {e}", exc_info=True)
        if "unique constraint" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Tool {data.tool_id} is already assigned to profile {profile_id}",
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add tool to profile: {str(e)}",
        )


@router.put(
    "/profiles/{profile_id}/tools/{tool_id}",
    response_model=ProfileToolResponse,
)
def update_profile_tool(
    profile_id: int,
    tool_id: int,
    data: ProfileToolUpdate,
    service: ToolService = Depends(get_tool_service),
):
    """
    Update a tool assignment for a profile.

    Can update enabled state, description override, or priority.
    """
    try:
        profile_tool = service.update_profile_tool(
            profile_id=profile_id,
            tool_id=tool_id,
            is_enabled=data.is_enabled,
            description_override=data.description_override,
            priority=data.priority,
        )
        return _to_response(profile_tool)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error updating profile tool: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update profile tool: {str(e)}",
        )


@router.delete(
    "/profiles/{profile_id}/tools/{tool_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def remove_tool_from_profile(
    profile_id: int,
    tool_id: int,
    service: ToolService = Depends(get_tool_service),
):
    """Remove a tool assignment from a profile."""
    try:
        service.remove_tool_from_profile(profile_id=profile_id, tool_id=tool_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error removing tool from profile: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to remove tool from profile: {str(e)}",
        )


@router.post(
    "/profiles/{profile_id}/tools/reorder",
    response_model=List[ProfileToolResponse],
)
def reorder_profile_tools(
    profile_id: int,
    data: ToolReorderRequest,
    db: Session = Depends(get_db),
    service: ToolService = Depends(get_tool_service),
):
    """
    Reorder tools for a profile.

    Pass tool IDs in the desired order. Priority will be set based on position.
    """
    # Verify profile exists
    profile = db.query(ConfigProfile).filter_by(id=profile_id).first()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Profile {profile_id} not found",
        )

    try:
        profile_tools = service.reorder_profile_tools(
            profile_id=profile_id,
            tool_ids=data.tool_ids,
        )
        return [_to_response(pt) for pt in profile_tools]
    except Exception as e:
        logger.error(f"Error reordering profile tools: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reorder profile tools: {str(e)}",
        )


@router.post(
    "/profiles/{profile_id}/tools/{tool_id}/toggle",
    response_model=ProfileToolResponse,
)
def toggle_profile_tool(
    profile_id: int,
    tool_id: int,
    service: ToolService = Depends(get_tool_service),
):
    """
    Toggle a tool's enabled state for a profile.

    Convenience endpoint that flips the is_enabled flag.
    """
    try:
        # Get current state
        profile_tool = service.get_profile_tool(profile_id, tool_id)
        if not profile_tool:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tool {tool_id} not assigned to profile {profile_id}",
            )

        # Toggle
        updated = service.update_profile_tool(
            profile_id=profile_id,
            tool_id=tool_id,
            is_enabled=not profile_tool.is_enabled,
        )
        return _to_response(updated)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error toggling profile tool: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to toggle profile tool: {str(e)}",
        )
