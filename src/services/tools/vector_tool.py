"""
Vector search tool implementation.

Creates LangChain tools for querying Databricks Vector Search indexes
using the Databricks VectorSearchRetrieverTool for native integration.
"""

import logging
from typing import Any

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from src.core.databricks_client import get_user_client
from src.database.models import ToolLibrary

logger = logging.getLogger(__name__)


class VectorSearchError(Exception):
    """Raised when vector search fails."""

    pass


class VectorSearchInput(BaseModel):
    """Input schema for vector search tool."""

    query: str = Field(description="Search query text to find similar documents")
    num_results: int = Field(
        default=5,
        description="Number of results to return (default: 5)",
        ge=1,
        le=20,
    )


def search_vector_index(
    index_name: str,
    query: str,
    num_results: int = 5,
    columns: list[str] = None,
) -> dict[str, Any]:
    """
    Search a Databricks Vector Search index using VectorSearchRetrieverTool.

    Args:
        index_name: Full index name (catalog.schema.index)
        query: Search query text
        num_results: Number of results to return
        columns: Optional list of columns to return

    Returns:
        Dict with 'results' list and 'count'

    Raises:
        VectorSearchError: If search fails
    """
    logger.info(
        "Searching vector index",
        extra={
            "index": index_name,
            "query": query[:100],
            "num_results": num_results,
        },
    )

    try:
        from databricks_openai import VectorSearchRetrieverTool
    except ImportError:
        raise VectorSearchError(
            "databricks-openai package not installed. "
            "Install with: pip install databricks-openai"
        )

    try:
        # Get user client for on-behalf-of execution
        client = get_user_client()

        # Create VectorSearchRetrieverTool with user credentials
        vs_tool = VectorSearchRetrieverTool(
            index_name=index_name,
            num_results=num_results,
            columns=columns,
            client=client,
        )

        # Execute the search
        results = vs_tool.execute(query)

        # Format results - VectorSearchRetrieverTool returns documents
        formatted_results = []
        if results:
            if isinstance(results, list):
                for item in results:
                    if isinstance(item, dict):
                        formatted_results.append(item)
                    elif hasattr(item, "page_content"):
                        # LangChain Document format
                        result_dict = {"content": item.page_content}
                        if hasattr(item, "metadata"):
                            result_dict.update(item.metadata)
                        formatted_results.append(result_dict)
                    else:
                        formatted_results.append({"content": str(item)})
            else:
                formatted_results.append({"content": str(results)})

        logger.info(
            "Vector search completed",
            extra={"result_count": len(formatted_results)},
        )

        return {
            "results": formatted_results,
            "count": len(formatted_results),
        }

    except VectorSearchError:
        raise
    except Exception as e:
        logger.error(f"Vector search failed: {e}", exc_info=True)
        raise VectorSearchError(f"Vector search failed: {e}") from e


def create_vector_tool(tool_def: ToolLibrary, description: str) -> StructuredTool:
    """
    Create a LangChain StructuredTool for vector search.

    Uses the Databricks VectorSearchRetrieverTool for native integration
    with Vector Search, executing with the user's permissions.

    Args:
        tool_def: ToolLibrary object with vector_index config
        description: Tool description for LLM

    Returns:
        LangChain StructuredTool instance
    """
    config = tool_def.config
    index_name = config.get("index_name")
    default_num_results = config.get("num_results", 5)
    columns = config.get("columns")  # Optional: specific columns to return

    # Note: endpoint_name is not required by VectorSearchRetrieverTool
    # It automatically resolves the endpoint from the index name

    if not index_name:
        raise ValueError(
            f"Vector tool {tool_def.name} missing index_name in config"
        )

    def _search_wrapper(query: str, num_results: int = None) -> dict[str, Any]:
        return search_vector_index(
            index_name=index_name,
            query=query,
            num_results=num_results or default_num_results,
            columns=columns,
        )

    # Generate unique tool name
    tool_name = f"search_{tool_def.name.lower().replace(' ', '_').replace('-', '_')}"

    # Build description
    full_description = description or f"Search the {tool_def.name} knowledge base"
    full_description += (
        "\n\nUse this tool to find relevant documents or information. "
        "Returns a list of matching results with relevance scores."
    )

    return StructuredTool.from_function(
        func=_search_wrapper,
        name=tool_name,
        description=full_description,
        args_schema=VectorSearchInput,
    )
