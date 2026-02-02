"""
Vector search tool implementation.

Creates LangChain tools for querying Databricks Vector Search indexes
using the native VectorSearchClient for direct integration.
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
    Search a Databricks Vector Search index using VectorSearchClient directly.

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
        from databricks.vector_search.client import VectorSearchClient
    except ImportError:
        raise VectorSearchError(
            "databricks-vectorsearch package not installed. "
            "Install with: pip install databricks-vectorsearch"
        )

    try:
        # Get user client for on-behalf-of execution
        client = get_user_client()
        
        # Extract credentials from the user client
        workspace_url = client.config.host
        token = client.config.token
        
        if not workspace_url:
            raise VectorSearchError("Workspace URL not available from client config")
        if not token:
            raise VectorSearchError("Token not available from client config")

        # Create VectorSearchClient with explicit credentials
        vs_client = VectorSearchClient(
            workspace_url=workspace_url,
            personal_access_token=token,
            disable_notice=True,
        )

        # Get the index
        index = vs_client.get_index(index_name=index_name)
        
        # Require columns to be specified
        if not columns:
            raise VectorSearchError(
                "No columns specified for vector search. "
                "Configure the columns to return in the tool settings."
            )
        
        # Execute similarity search
        results = index.similarity_search(
            query_text=query,
            columns=columns,
            num_results=num_results,
        )

        # Format results from the response
        formatted_results = []
        if results and "result" in results:
            data_array = results["result"].get("data_array", [])
            column_names = results.get("manifest", {}).get("columns", [])
            col_names = [col.get("name") for col in column_names]
            
            for row in data_array:
                result_dict = {}
                for i, value in enumerate(row):
                    if i < len(col_names):
                        result_dict[col_names[i]] = value
                    else:
                        result_dict[f"col_{i}"] = value
                formatted_results.append(result_dict)

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

    Uses the Databricks VectorSearchClient for native integration
    with Vector Search, executing with the user's permissions.

    Args:
        tool_def: ToolLibrary object with vector_index config
        description: Tool description for LLM

    Returns:
        LangChain StructuredTool instance
    
    Raises:
        ValueError: If index_name or columns are missing from config
    """
    config = tool_def.config
    index_name = config.get("index_name")
    default_num_results = config.get("num_results", 5)
    
    # Parse columns - can be a comma-separated string or a list
    columns = config.get("columns")
    if isinstance(columns, str):
        columns = [c.strip() for c in columns.split(",") if c.strip()]
    elif columns is None:
        columns = []

    if not index_name:
        raise ValueError(
            f"Vector tool {tool_def.name} missing index_name in config"
        )
    
    if not columns:
        raise ValueError(
            f"Vector tool {tool_def.name} missing columns in config. "
            "Specify which columns to return from search results."
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
