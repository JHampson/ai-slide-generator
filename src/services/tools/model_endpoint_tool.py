"""
Model Serving Endpoint tool implementation.

Creates LangChain tools for querying Databricks Model Serving endpoints
using the user's OAuth token (OBO authentication).
"""

import json
import logging
from typing import Any

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field, create_model

from src.core.databricks_client import get_user_client
from src.database.models import ToolLibrary

logger = logging.getLogger(__name__)


class ModelEndpointError(Exception):
    """Raised when model endpoint query fails."""

    pass


class ModelEndpointInput(BaseModel):
    """Default input schema for model endpoint tool."""

    input_data: dict = Field(
        default_factory=dict,
        description="Input data to pass to the model as key-value pairs",
    )


def query_model_endpoint(
    endpoint_name: str,
    input_data: dict[str, Any],
) -> str:
    """
    Query a Databricks Model Serving endpoint.

    Uses the user's OAuth token for on-behalf-of authentication,
    ensuring the query runs with the user's permissions.

    Args:
        endpoint_name: Name of the serving endpoint
        input_data: Input data to send to the model

    Returns:
        JSON string with model response

    Raises:
        ModelEndpointError: If query fails
    """
    logger.info(
        "Querying model endpoint",
        extra={"endpoint": endpoint_name, "input_keys": list(input_data.keys())},
    )

    try:
        # Get user client for on-behalf-of execution
        client = get_user_client()

        # Query the endpoint using dataframe_records format
        # This is the most flexible format for custom models
        response = client.serving_endpoints.query(
            name=endpoint_name,
            dataframe_records=[input_data],
        )

        # Convert response to dict
        result = response.as_dict() if hasattr(response, "as_dict") else {"predictions": str(response)}

        logger.info(
            "Model endpoint query successful",
            extra={"endpoint": endpoint_name, "has_predictions": "predictions" in result},
        )

        # Return as JSON string for LangChain/DB compatibility
        return json.dumps(result)

    except Exception as e:
        logger.error(f"Model endpoint query failed: {e}", exc_info=True)
        raise ModelEndpointError(f"Failed to query model endpoint {endpoint_name}: {e}") from e


def create_model_endpoint_tool(tool_def: ToolLibrary, description: str) -> StructuredTool:
    """
    Create a LangChain StructuredTool for a Model Serving endpoint.

    Uses the Databricks SDK serving_endpoints.query() method with
    the user's OAuth token for on-behalf-of authentication.

    Args:
        tool_def: ToolLibrary object with model_endpoint config
        description: Tool description for LLM

    Returns:
        LangChain StructuredTool instance
    """
    config = tool_def.config
    endpoint_name = config.get("endpoint_name")
    input_schema = config.get("input_schema", {})  # Optional parameter definitions

    if not endpoint_name:
        raise ValueError(
            f"Model endpoint tool {tool_def.name} missing endpoint_name in config"
        )

    # Build Pydantic input schema based on configuration
    if input_schema:
        fields = {}
        for param_name, param_info in input_schema.items():
            param_type = param_info.get("type", "string")
            param_desc = param_info.get("description", f"{param_name} parameter")
            param_required = param_info.get("required", False)

            type_map = {
                "str": str,
                "string": str,
                "int": int,
                "integer": int,
                "float": float,
                "number": float,
                "bool": bool,
                "boolean": bool,
                "object": dict,
                "array": list,
            }

            py_type = type_map.get(param_type.lower(), str)

            if param_required:
                fields[param_name] = (py_type, Field(description=param_desc))
            else:
                fields[param_name] = (
                    py_type,
                    Field(default=None, description=param_desc),
                )

        InputSchema = create_model(f"{endpoint_name.replace('-', '_')}Input", **fields)

        def _wrapper(**kwargs) -> str:
            # Remove None values
            input_data = {k: v for k, v in kwargs.items() if v is not None}
            return query_model_endpoint(
                endpoint_name=endpoint_name,
                input_data=input_data,
            )

    else:
        # Use default schema with generic input_data dict
        InputSchema = ModelEndpointInput

        def _wrapper(input_data: dict = None) -> str:
            return query_model_endpoint(
                endpoint_name=endpoint_name,
                input_data=input_data or {},
            )

    # Generate unique tool name
    tool_name = f"query_{tool_def.name.lower().replace(' ', '_').replace('-', '_')}"

    # Build description
    full_description = description or f"Query the {endpoint_name} model serving endpoint"
    full_description += f"\n\nThis queries the Databricks Model Serving endpoint: {endpoint_name}"

    return StructuredTool.from_function(
        func=_wrapper,
        name=tool_name,
        description=full_description,
        args_schema=InputSchema,
    )
