"""
Tool factory for creating LangChain tools from profile configurations.

This module provides functions to create LangChain StructuredTool instances
from ToolLibrary configurations. Each tool type has a dedicated creator function.
"""

import logging

from langchain_core.tools import StructuredTool

from src.database.models import ProfileTool, ToolType
from src.services.tools.genie_tool import (
    GenieToolError,
    create_genie_tool,
    initialize_genie_conversation,
    query_genie_space,
)
from src.services.tools.mcp_tool import create_mcp_tools
from src.services.tools.model_endpoint_tool import ModelEndpointError, create_model_endpoint_tool
from src.services.tools.uc_function_tool import UCFunctionError, create_uc_function_tool
from src.services.tools.vector_tool import VectorSearchError, create_vector_tool

logger = logging.getLogger(__name__)

__all__ = [
    # Factory functions
    "create_tools_for_profile",
    "initialize_genie_conversations",
    # Genie
    "GenieToolError",
    "create_genie_tool",
    "initialize_genie_conversation",
    "query_genie_space",
    # Vector
    "VectorSearchError",
    "create_vector_tool",
    # MCP
    "create_mcp_tools",
    # UC Function
    "UCFunctionError",
    "create_uc_function_tool",
    # Model Endpoint
    "ModelEndpointError",
    "create_model_endpoint_tool",
]


def create_tools_for_profile(
    profile_tools: list[ProfileTool],
    session_id: str,
    genie_conversations: dict[int, str] = None,
) -> list[StructuredTool]:
    """
    Create LangChain tools from a profile's assigned tools.

    Args:
        profile_tools: List of ProfileTool objects from the database
        session_id: Current session ID for session-scoped state
        genie_conversations: Dict mapping tool_id to existing conversation_id
                            (for multi-turn Genie conversations)

    Returns:
        List of LangChain StructuredTool instances ready for agent use
    """
    tools = []
    genie_conversations = genie_conversations or {}

    # Sort by priority (lower = first)
    sorted_tools = sorted(profile_tools, key=lambda x: x.priority)

    for pt in sorted_tools:
        # Skip disabled tools or inactive library entries
        if not pt.is_enabled:
            logger.debug(f"Skipping disabled tool: {pt.tool.name}")
            continue
        if not pt.tool.is_active:
            logger.debug(f"Skipping inactive library tool: {pt.tool.name}")
            continue

        tool_def = pt.tool
        description = pt.description_override or tool_def.description
        tool_type = tool_def.tool_type

        try:
            if tool_type == ToolType.GENIE_SPACE.value:
                # Get existing conversation ID if available
                conv_id = genie_conversations.get(tool_def.id)
                tool = create_genie_tool(tool_def, description, session_id, conversation_id=conv_id)
                tools.append(tool)

            elif tool_type == ToolType.VECTOR_INDEX.value:
                tool = create_vector_tool(tool_def, description)
                tools.append(tool)

            elif tool_type == ToolType.MCP_SERVER.value:
                # MCP may expose multiple tools
                mcp_tools = create_mcp_tools(tool_def, description)
                tools.extend(mcp_tools)

            elif tool_type == ToolType.UC_FUNCTION.value:
                tool = create_uc_function_tool(tool_def, description)
                tools.append(tool)

            elif tool_type == ToolType.MODEL_ENDPOINT.value:
                tool = create_model_endpoint_tool(tool_def, description)
                tools.append(tool)

            else:
                logger.warning(f"Unknown tool type: {tool_type}")

        except Exception as e:
            logger.error(f"Failed to create tool {tool_def.name}: {e}")
            # Continue with other tools rather than failing completely

    logger.info(f"Created {len(tools)} tools for profile")
    return tools


def initialize_genie_conversations(
    profile_tools: list[ProfileTool],
) -> dict[int, str]:
    """
    Initialize Genie conversations for all Genie tools in a profile.

    This should be called at session start to pre-initialize conversations
    with the system message.

    Args:
        profile_tools: List of ProfileTool objects

    Returns:
        Dict mapping tool_id to conversation_id
    """
    conversations = {}

    for pt in profile_tools:
        if not pt.is_enabled or not pt.tool.is_active:
            continue

        if pt.tool.tool_type == ToolType.GENIE_SPACE.value:
            try:
                space_id = pt.tool.config.get("space_id")
                if space_id:
                    conv_id = initialize_genie_conversation(space_id)
                    conversations[pt.tool.id] = conv_id
                    logger.info(
                        f"Initialized Genie conversation for tool {pt.tool.name}",
                        extra={"conversation_id": conv_id},
                    )
            except Exception as e:
                logger.error(f"Failed to initialize Genie conversation for {pt.tool.name}: {e}")

    return conversations
