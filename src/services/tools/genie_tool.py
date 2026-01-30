"""
Genie space tool implementation.

Creates LangChain tools for querying Databricks Genie spaces.
"""

import logging
import time
from typing import Any, Optional

import pandas as pd
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from src.core.databricks_client import get_user_client
from src.database.models import ToolLibrary

logger = logging.getLogger(__name__)


class GenieToolError(Exception):
    """Raised when Genie tool execution fails."""

    pass


class GenieQueryInput(BaseModel):
    """Input schema for Genie query tool."""

    query: str = Field(description="Natural language question to ask the Genie space")


def initialize_genie_conversation(space_id: str) -> str:
    """
    Initialize a Genie conversation with a system message.

    Args:
        space_id: Databricks Genie space ID

    Returns:
        Genie conversation ID string

    Raises:
        GenieToolError: If conversation initialization fails
    """
    logger.info(f"Initializing Genie conversation for space {space_id}")
    client = get_user_client()

    conversation_start_message = (
        "You are a data analyst agent for an AI slide generation system. "
        "Unless explicitly instructed otherwise, convert datetimes to dates "
        "and always round numeric columns to the nearest whole number. "
        "Provide an informative explanation of your query results."
    )

    try:
        response = client.genie.start_conversation_and_wait(
            space_id=space_id, content=conversation_start_message
        )
        conversation_id = response.conversation_id

        logger.info(
            "Initialized Genie conversation",
            extra={
                "conversation_id": conversation_id,
                "space_id": space_id,
            },
        )

        return conversation_id

    except Exception as e:
        raise GenieToolError(f"Failed to initialize Genie conversation: {e}") from e


def query_genie_space(
    space_id: str,
    query: str,
    conversation_id: Optional[str] = None,
    max_retries: int = 2,
) -> dict[str, Any]:
    """
    Query a Databricks Genie space.

    Args:
        space_id: Genie space ID
        query: Natural language question
        conversation_id: Optional existing conversation ID for multi-turn
        max_retries: Maximum retries on failure

    Returns:
        Dict with 'message', 'data', and 'conversation_id'

    Raises:
        GenieToolError: If query fails after all retries
    """
    logger.info(
        "Querying Genie space",
        extra={"space_id": space_id, "query": query[:100]},
    )

    client = get_user_client()
    attempt = 0
    last_error = None

    while attempt <= max_retries:
        try:
            if conversation_id is None:
                response = client.genie.start_conversation_and_wait(
                    space_id=space_id, content=query
                )
                conversation_id = response.conversation_id
            else:
                response = client.genie.create_message_and_wait(
                    space_id=space_id, conversation_id=conversation_id, content=query
                )

            message_id = response.message_id

            # Extract attachments (data results)
            attachments = response.attachments
            data = ""
            message_content = ""

            for attachment in attachments:
                if attachment.query:
                    attachment_response = client.genie.get_message_attachment_query_result(
                        space_id=space_id,
                        conversation_id=conversation_id,
                        message_id=message_id,
                        attachment_id=attachment.attachment_id,
                    )
                    response_dict = attachment_response.as_dict()["statement_response"]
                    columns = [_["name"] for _ in response_dict["manifest"]["schema"]["columns"]]
                    data_array = response_dict["result"]["data_array"]
                    df = pd.DataFrame(data_array, columns=columns)
                    data = df.to_csv(index=False)

                if attachment.text:
                    message_content = attachment.text

            if attempt > 0:
                logger.info(
                    "Genie query succeeded after retries",
                    extra={"attempt": attempt + 1, "conversation_id": conversation_id},
                )

            logger.info(
                "Genie query completed",
                extra={
                    "has_message": bool(message_content),
                    "has_data": bool(data),
                    "conversation_id": conversation_id,
                },
            )

            return {
                "message": message_content,
                "data": data,
                "conversation_id": conversation_id,
            }

        except Exception as e:
            last_error = e
            attempt += 1
            if attempt <= max_retries:
                logger.warning(
                    f"Genie query failed, retrying: {e}",
                    extra={"attempt": attempt, "max_retries": max_retries},
                )
                time.sleep(1)
            else:
                raise GenieToolError(
                    f"Failed to query Genie space after {max_retries + 1} attempts: {e}"
                ) from last_error


def create_genie_tool(
    tool_def: ToolLibrary,
    description: str,
    session_id: str,
    conversation_id: str = None,
) -> StructuredTool:
    """
    Create a LangChain StructuredTool for a Genie space.

    Args:
        tool_def: ToolLibrary object with genie_space config
        description: Tool description for LLM
        session_id: Current session ID
        conversation_id: Optional pre-initialized conversation ID

    Returns:
        LangChain StructuredTool instance
    """
    config = tool_def.config
    space_id = config.get("space_id")
    space_name = config.get("space_name", tool_def.name)

    if not space_id:
        raise ValueError(f"Genie tool {tool_def.name} missing space_id in config")

    # Use closure to capture session state
    _conversation_id = conversation_id

    def _query_wrapper(query: str) -> dict[str, Any]:
        nonlocal _conversation_id

        result = query_genie_space(
            space_id=space_id,
            query=query,
            conversation_id=_conversation_id,
        )

        # Update conversation ID for next call
        _conversation_id = result.get("conversation_id")

        return result

    # Generate unique tool name (sanitize for LangChain)
    tool_name = f"query_{tool_def.name.lower().replace(' ', '_').replace('-', '_')}"

    # Build description
    full_description = description or f"Query the {space_name} Genie space for data"
    full_description += (
        "\n\nUse this tool to ask natural language questions about data. "
        "Returns a message explaining the results and CSV-formatted data."
    )

    return StructuredTool.from_function(
        func=_query_wrapper,
        name=tool_name,
        description=full_description,
        args_schema=GenieQueryInput,
    )
