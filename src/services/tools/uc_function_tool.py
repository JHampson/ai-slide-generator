"""
Unity Catalog function tool implementation.

Creates LangChain tools for executing Unity Catalog SQL functions
using SQL Statement Execution API for broad compatibility.
"""

import json
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


def format_sql_arg(value: Any) -> str:
    """
    Format a Python value as a SQL literal for use in function calls.
    
    Args:
        value: Python value to format
        
    Returns:
        SQL literal string
    """
    if value is None:
        return "NULL"
    elif isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    elif isinstance(value, (int, float)):
        return str(value)
    elif isinstance(value, str):
        # Escape single quotes by doubling them
        escaped = value.replace("'", "''")
        return f"'{escaped}'"
    elif isinstance(value, dict):
        # JSON objects as string literals
        return f"'{json.dumps(value)}'"
    elif isinstance(value, list):
        # Arrays as string literals
        return f"'{json.dumps(value)}'"
    else:
        # Fallback: convert to string
        return f"'{str(value)}'"


class UCFunctionInput(BaseModel):
    """Default input schema for UC function tool."""

    arguments: dict = Field(
        default_factory=dict,
        description="Arguments to pass to the function as key-value pairs",
    )


def execute_uc_function(
    full_name: str,
    arguments: dict[str, Any] = None,
    warehouse_id: str = None,
) -> dict[str, Any]:
    """
    Execute a Unity Catalog SQL function via SQL Statement Execution API.

    This method uses the SQL API instead of gRPC Function Serving, which
    provides broader compatibility with OAuth scopes.

    Args:
        full_name: Full function name (catalog.schema.function_name)
        arguments: Function arguments as key-value pairs
        warehouse_id: Optional SQL warehouse ID (uses serverless if not provided)

    Returns:
        Dict with 'result' containing function output

    Raises:
        UCFunctionError: If function execution fails
    """
    from databricks.sdk.service.sql import StatementState

    logger.info(
        "Executing UC function via SQL",
        extra={"function": full_name, "arguments": arguments},
    )

    try:
        # Get user client for on-behalf-of execution
        client = get_user_client()
        args = arguments or {}

        # Build SQL to call the function
        if args:
            # Format each argument as a SQL literal
            arg_values = ", ".join(format_sql_arg(v) for v in args.values())
            sql = f"SELECT {full_name}({arg_values})"
        else:
            sql = f"SELECT {full_name}()"

        logger.info(f"Executing SQL: {sql}")

        # Execute via Statement Execution API
        # If no warehouse_id provided, Databricks will use serverless compute
        response = client.statement_execution.execute_statement(
            warehouse_id=warehouse_id,
            statement=sql,
            wait_timeout="30s",
        )

        # Check execution status
        if response.status.state == StatementState.SUCCEEDED:
            # Extract result from first row, first column
            result_value = None
            if response.result and response.result.data_array:
                result_value = response.result.data_array[0][0]

            logger.info(
                "UC function executed successfully",
                extra={"function": full_name, "has_result": result_value is not None},
            )

            # Return as string for LangChain compatibility
            # If result is already a string (e.g. JSON), return as-is
            if isinstance(result_value, str):
                return result_value
            else:
                return json.dumps({"result": result_value, "function": full_name})

        elif response.status.state == StatementState.FAILED:
            error_msg = response.status.error.message if response.status.error else "Unknown error"
            logger.error(
                "UC function execution failed",
                extra={"function": full_name, "error": error_msg},
            )
            raise UCFunctionError(f"Function execution failed: {error_msg}")

        else:
            # Handle other states (PENDING, RUNNING, CANCELED, CLOSED)
            raise UCFunctionError(
                f"Unexpected execution state: {response.status.state}. "
                "Function may have timed out or been canceled."
            )

    except UCFunctionError:
        raise
    except Exception as e:
        logger.error(f"UC function execution failed: {e}", exc_info=True)
        raise UCFunctionError(f"Failed to execute UC function {full_name}: {e}") from e


def create_uc_function_tool(tool_def: ToolLibrary, description: str) -> StructuredTool:
    """
    Create a LangChain StructuredTool for a UC function.

    Uses SQL Statement Execution API for executing Unity Catalog functions
    with the user's permissions via OAuth on-behalf-of flow.

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
    warehouse_id = config.get("warehouse_id")  # Optional: uses serverless if not set

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
                            warehouse_id=warehouse_id,
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
                warehouse_id=warehouse_id,
            )

    else:
        # Use default schema with arguments dict
        InputSchema = UCFunctionInput

        def _wrapper(arguments: dict = None) -> dict[str, Any]:
            return execute_uc_function(
                full_name=full_name,
                arguments=arguments or {},
                warehouse_id=warehouse_id,
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
