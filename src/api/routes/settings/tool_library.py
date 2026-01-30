"""
Tool library API endpoints.

Manages the app-level tool library where tools are defined once
and can be assigned to multiple profiles.
"""

import logging
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.api.schemas.settings.tools import (
    ToolLibraryCreate,
    ToolLibraryResponse,
    ToolLibraryUpdate,
    ToolValidateRequest,
    ToolValidateResponse,
)
from src.core.database import get_db
from src.core.databricks_client import get_user_client
from src.database.models import ToolType
from src.services.tool_service import ToolService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tool-library", tags=["tool-library"])


def get_tool_service(db: Session = Depends(get_db)) -> ToolService:
    """Dependency to get ToolService."""
    return ToolService(db)


@router.get("", response_model=List[ToolLibraryResponse])
def list_tools(
    include_inactive: bool = False,
    tool_type: str = None,
    service: ToolService = Depends(get_tool_service),
):
    """
    List all tools in the library.

    Args:
        include_inactive: Include soft-deleted tools
        tool_type: Filter by tool type (optional)
    """
    try:
        if tool_type:
            tools = service.list_tools_by_type(tool_type, include_inactive)
        else:
            tools = service.list_tools(include_inactive)
        return tools
    except Exception as e:
        logger.error(f"Error listing tools: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list tools: {str(e)}",
        )


@router.get("/{tool_id}", response_model=ToolLibraryResponse)
def get_tool(
    tool_id: int,
    service: ToolService = Depends(get_tool_service),
):
    """Get a specific tool by ID."""
    tool = service.get_tool(tool_id)
    if not tool:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tool {tool_id} not found",
        )
    return tool


@router.post("", response_model=ToolLibraryResponse, status_code=status.HTTP_201_CREATED)
def create_tool(
    data: ToolLibraryCreate,
    service: ToolService = Depends(get_tool_service),
):
    """
    Create a new tool in the library.

    Tool types and their config schemas:
    - genie_space: {"space_id": "...", "space_name": "..."}
    - vector_index: {"endpoint_name": "...", "index_name": "...", "num_results": 5}
    - mcp_server: {"connection_name": "..."} (Unity Catalog connection name)
    - uc_function: {"catalog": "...", "schema": "...", "function_name": "...", "parameters": {...}}
    """
    try:
        # Validate tool type
        valid_types = [t.value for t in ToolType]
        if data.tool_type not in valid_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid tool_type. Must be one of: {valid_types}",
            )

        tool = service.create_tool(
            tool_type=data.tool_type,
            name=data.name,
            config=data.config,
            description=data.description,
        )
        return tool

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating tool: {e}", exc_info=True)
        if "unique constraint" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Tool with name '{data.name}' already exists",
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create tool: {str(e)}",
        )


@router.put("/{tool_id}", response_model=ToolLibraryResponse)
def update_tool(
    tool_id: int,
    data: ToolLibraryUpdate,
    service: ToolService = Depends(get_tool_service),
):
    """Update an existing tool."""
    try:
        tool = service.update_tool(
            tool_id=tool_id,
            name=data.name,
            description=data.description,
            config=data.config,
        )
        return tool
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error updating tool: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update tool: {str(e)}",
        )


@router.delete("/{tool_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_tool(
    tool_id: int,
    hard: bool = False,
    service: ToolService = Depends(get_tool_service),
):
    """
    Delete a tool from the library.

    Args:
        tool_id: Tool ID
        hard: If True, permanently delete. If False, soft-delete (default).
    """
    try:
        if hard:
            service.hard_delete_tool(tool_id)
        else:
            service.delete_tool(tool_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error deleting tool: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete tool: {str(e)}",
        )


# ============================================================================
# Discovery endpoints
# ============================================================================


@router.get("/discover/genie", response_model=Dict[str, Any])
def discover_genie_spaces():
    """
    List available Genie spaces from Databricks.

    Returns spaces that can be added to the tool library.
    """
    try:
        client = get_user_client()
        spaces_data = {}

        response = client.genie.list_spaces(page_size=100)

        if response.spaces:
            for space in response.spaces:
                spaces_data[space.space_id] = {
                    "title": space.title,
                    "description": space.description or "",
                }

        while response.next_page_token:
            response = client.genie.list_spaces(page_token=response.next_page_token, page_size=100)
            if response.spaces:
                for space in response.spaces:
                    spaces_data[space.space_id] = {
                        "title": space.title,
                        "description": space.description or "",
                    }

        sorted_titles = sorted([d["title"] for d in spaces_data.values()])

        return {"spaces": spaces_data, "sorted_titles": sorted_titles}

    except Exception as e:
        logger.error(f"Error discovering Genie spaces: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to discover Genie spaces: {str(e)}",
        )


@router.get("/discover/vector", response_model=Dict[str, Any])
def discover_vector_indexes():
    """
    List available vector search indexes from Databricks.

    Returns indexes that can be added to the tool library.
    """
    try:
        # Try to import vector search client
        try:
            from databricks.vector_search.client import VectorSearchClient

            # Get the workspace client to use its authentication
            ws_client = get_user_client()

            # Initialize VectorSearchClient with workspace client for proper auth
            vsc = VectorSearchClient(
                workspace_url=ws_client.config.host,
                personal_access_token=ws_client.config.token,
                disable_notice=True,
            )
            endpoints = vsc.list_endpoints()

            indexes_data = {}
            for endpoint in endpoints.get("endpoints", []):
                endpoint_name = endpoint.get("name")
                endpoint_status = endpoint.get("endpoint_status", {}).get("state")

                # List indexes for each endpoint
                try:
                    indexes = vsc.list_indexes(endpoint_name)
                    for idx in indexes.get("vector_indexes", []):
                        idx_name = idx.get("name")
                        indexes_data[f"{endpoint_name}/{idx_name}"] = {
                            "endpoint_name": endpoint_name,
                            "index_name": idx_name,
                            "endpoint_status": endpoint_status,
                            "index_type": idx.get("index_type"),
                        }
                except Exception as e:
                    logger.warning(f"Could not list indexes for {endpoint_name}: {e}")

            return {"indexes": indexes_data}

        except ImportError:
            return {
                "indexes": {},
                "message": "databricks-vectorsearch package not installed",
            }

    except Exception as e:
        logger.error(f"Error discovering vector indexes: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to discover vector indexes: {str(e)}",
        )


@router.post("/validate", response_model=ToolValidateResponse)
def validate_tool_config(data: ToolValidateRequest):
    """
    Validate tool configuration before creating.

    Performs type-specific validation to catch configuration errors early.
    """
    errors = []
    warnings = []

    try:
        if data.tool_type == ToolType.GENIE_SPACE.value:
            if not data.config.get("space_id"):
                errors.append("space_id is required for Genie space tools")
            if not data.config.get("space_name"):
                warnings.append("space_name is recommended for display purposes")

        elif data.tool_type == ToolType.VECTOR_INDEX.value:
            if not data.config.get("endpoint_name"):
                errors.append("endpoint_name is required for vector index tools")
            if not data.config.get("index_name"):
                errors.append("index_name is required for vector index tools")

        elif data.tool_type == ToolType.MCP_SERVER.value:
            if not data.config.get("connection_name"):
                errors.append("connection_name is required for MCP server tools")

        elif data.tool_type == ToolType.UC_FUNCTION.value:
            if not data.config.get("catalog"):
                errors.append("catalog is required for UC function tools")
            if not data.config.get("schema"):
                errors.append("schema is required for UC function tools")
            if not data.config.get("function_name"):
                errors.append("function_name is required for UC function tools")

        else:
            valid_types = [t.value for t in ToolType]
            errors.append(f"Unknown tool_type. Must be one of: {valid_types}")

        return ToolValidateResponse(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )

    except Exception as e:
        logger.error(f"Error validating tool config: {e}", exc_info=True)
        return ToolValidateResponse(
            valid=False,
            errors=[f"Validation error: {str(e)}"],
            warnings=[],
        )
