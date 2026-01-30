"""
Unity Catalog function tool implementation.

Creates LangChain tools for executing Unity Catalog SQL functions
using the Databricks UCFunctionToolkit for native integration.
"""

import logging
from typing import Any

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field, create_model

from src.core.databricks_client import get_user_client
from src.database.models import ToolLibrary

logger = logging.getLogger(__name__)


class UCFunctionError(Exception):
    """Raised when UC function execution fails."""

    pass


class UCFunctionInput(BaseModel):
    """Default input schema for UC function tool."""

    arguments: dict = Field(
        default_factory=dict,
        description="Arguments to pass to the function as key-value pairs",
    )


def execute_uc_function(
    full_name: str,
    arguments: dict[str, Any] = None,
) -> dict[str, Any]:
    """
    Execute a Unity Catalog SQL function using UCFunctionToolkit.

    Args:
        full_name: Full function name (catalog.schema.function_name)
        arguments: Function arguments

    Returns:
        Dict with 'result' containing function output

    Raises:
        UCFunctionError: If function execution fails
    """
    logger.info(
        "Executing UC function",
        extra={"function": full_name, "arguments": arguments},
    )

    try:
        from unitycatalog.ai.core.databricks import DatabricksFunctionClient
    except ImportError:
        raise UCFunctionError(
            "unitycatalog-ai package not installed. "
            "Install with: pip install unitycatalog-ai"
        )

    try:
        # Get user client for on-behalf-of execution
        client = get_user_client()

        # Create UC function client with user credentials
        uc_client = DatabricksFunctionClient(client=client)

        # Execute the function
        args = arguments or {}
        logger.info(f"Executing UC function {full_name} with args: {args}")

        result = uc_client.execute_function(full_name, args)

        # Check for errors
        if hasattr(result, "error") and result.error:
            logger.error(
                f"UC function execution error",
                extra={"function": full_name, "error": result.error},
            )
            raise UCFunctionError(f"Function execution failed: {result.error}")

        # Extract result value
        result_value = result.value if hasattr(result, "value") else result

        logger.info(
            "UC function executed successfully",
            extra={"function": full_name, "has_result": result_value is not None},
        )

        return {"result": result_value, "function": full_name}

    except UCFunctionError:
        raise
    except Exception as e:
        logger.error(f"UC function execution failed: {e}", exc_info=True)
        raise UCFunctionError(f"Failed to execute UC function {full_name}: {e}") from e


def create_uc_function_tool(tool_def: ToolLibrary, description: str) -> StructuredTool:
    """
    Create a LangChain StructuredTool for a UC function.

    Uses the Databricks UCFunctionToolkit for native integration with
    Unity Catalog functions, executing with the user's permissions.

    Args:
        tool_def: ToolLibrary object with uc_function config
        description: Tool description for LLM

    Returns:
        LangChain StructuredTool instance
    """
    config = tool_def.config
    catalog = config.get("catalog")
    schema = config.get("schema")
    function_name = config.get("function_name")
    parameters = config.get("parameters", {})  # Optional parameter definitions

    if not all([catalog, schema, function_name]):
        raise ValueError(
            f"UC function tool {tool_def.name} missing catalog, schema, or function_name"
        )

    full_name = f"{catalog}.{schema}.{function_name}"

    # Try to get function metadata from UCFunctionToolkit for better schema
    try:
        from databricks_openai import UCFunctionToolkit

        client = get_user_client()
        toolkit = UCFunctionToolkit(function_names=[full_name], client=client)

        if toolkit.tools:
            tool_spec = toolkit.tools[0]
            # Extract parameters from tool spec if available
            if "function" in tool_spec and "parameters" in tool_spec["function"]:
                func_params = tool_spec["function"]["parameters"]
                properties = func_params.get("properties", {})
                required = func_params.get("required", [])

                # Build Pydantic fields from spec
                fields = {}
                for param_name, param_spec in properties.items():
                    param_type = param_spec.get("type", "string")
                    param_desc = param_spec.get("description", f"{param_name} parameter")

                    type_map = {
                        "string": str,
                        "integer": int,
                        "number": float,
                        "boolean": bool,
                        "object": dict,
                        "array": list,
                    }
                    py_type = type_map.get(param_type, str)

                    if param_name in required:
                        fields[param_name] = (py_type, Field(description=param_desc))
                    else:
                        fields[param_name] = (
                            py_type,
                            Field(default=None, description=param_desc),
                        )

                if fields:
                    InputSchema = create_model(f"{function_name}Input", **fields)

                    def _wrapper(**kwargs) -> dict[str, Any]:
                        return execute_uc_function(
                            full_name=full_name,
                            arguments=kwargs,
                        )

                    tool_name = f"call_{tool_def.name.lower().replace(' ', '_').replace('-', '_')}"
                    full_description = description or f"Execute the {full_name} function"
                    full_description += f"\n\nThis calls the Unity Catalog function: {full_name}"

                    return StructuredTool.from_function(
                        func=_wrapper,
                        name=tool_name,
                        description=full_description,
                        args_schema=InputSchema,
                    )

    except ImportError:
        logger.warning("databricks-openai not available, using manual parameter config")
    except Exception as e:
        logger.warning(f"Could not get function metadata from toolkit: {e}")

    # Fallback: Create input schema based on manual parameter definitions
    if parameters:
        fields = {}
        for param_name, param_info in parameters.items():
            param_type = param_info.get("type", "str")
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
            }

            py_type = type_map.get(param_type.lower(), str)

            if param_required:
                fields[param_name] = (py_type, Field(description=param_desc))
            else:
                fields[param_name] = (
                    py_type,
                    Field(default=None, description=param_desc),
                )

        InputSchema = create_model(f"{function_name}Input", **fields)

        def _wrapper(**kwargs) -> dict[str, Any]:
            return execute_uc_function(
                full_name=full_name,
                arguments=kwargs,
            )

    else:
        # Use default schema with arguments dict
        InputSchema = UCFunctionInput

        def _wrapper(arguments: dict = None) -> dict[str, Any]:
            return execute_uc_function(
                full_name=full_name,
                arguments=arguments or {},
            )

    # Generate unique tool name
    tool_name = f"call_{tool_def.name.lower().replace(' ', '_').replace('-', '_')}"

    # Build description
    full_description = description or f"Execute the {full_name} function"
    full_description += f"\n\nThis calls the Unity Catalog function: {full_name}"

    return StructuredTool.from_function(
        func=_wrapper,
        name=tool_name,
        description=full_description,
        args_schema=InputSchema,
    )
