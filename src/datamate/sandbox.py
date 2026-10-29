import ast
import math
import re
import unicodedata
from typing import Any

import numpy as np
import pandas as pd

from .models import ExecutionResult

BLOCKED_FUNCTION_NAMES = {
    "__import__",
    "breakpoint",
    "compile",
    "eval",
    "exec",
    "globals",
    "input",
    "locals",
    "open",
    "vars",
}

BLOCKED_ATTRIBUTES = {
    "ExcelWriter",
    "HDFStore",
    "to_clipboard",
    "to_csv",
    "to_excel",
    "to_feather",
    "to_gbq",
    "to_hdf",
    "to_html",
    "to_json",
    "to_latex",
    "to_markdown",
    "to_orc",
    "to_parquet",
    "to_pickle",
    "to_sql",
    "to_stata",
    "to_xml",
}

SAFE_BUILTINS = {
    "abs": abs,
    "all": all,
    "any": any,
    "bool": bool,
    "dict": dict,
    "enumerate": enumerate,
    "filter": filter,
    "float": float,
    "int": int,
    "isinstance": isinstance,
    "len": len,
    "list": list,
    "map": map,
    "max": max,
    "min": min,
    "range": range,
    "reversed": reversed,
    "round": round,
    "set": set,
    "sorted": sorted,
    "str": str,
    "sum": sum,
    "tuple": tuple,
    "zip": zip,
    "True": True,
    "False": False,
    "None": None,
}


def validate_python_code(code_string: str, max_length: int = 50000) -> tuple[bool, str | None]:
    if len(code_string) > max_length:
        return False, "Code length exceeds maximum allowed characters"
    try:
        syntax_tree = ast.parse(code_string)
    except SyntaxError as syntax_error:
        return False, f"SyntaxError: {syntax_error.msg} at line {syntax_error.lineno}"

    for node in ast.walk(syntax_tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            return False, "Import statements are not allowed in sandbox code"
        if isinstance(node, (ast.While, ast.AsyncFor, ast.AsyncWith, ast.Await)):
            return False, f"Construct {type(node).__name__} is not allowed"
        if isinstance(node, ast.Name):
            if node.id in BLOCKED_FUNCTION_NAMES or node.id.startswith("__"):
                return False, f"Forbidden name: {node.id}"
        if isinstance(node, ast.Attribute):
            if node.attr.startswith("__") or node.attr in BLOCKED_ATTRIBUTES:
                return False, f"Forbidden attribute: {node.attr}"
    return True, None


def execute_sandboxed_pandas(
    code_string: str,
    data_context: dict[str, Any],
    timeout_seconds: float = 10.0,
) -> ExecutionResult:
    is_valid, validation_error = validate_python_code(code_string)
    if not is_valid:
        return ExecutionResult(
            is_success=False,
            error_message=f"SafetyError: {validation_error}",
            executed_code=code_string,
        )

    dfs = data_context.get("dfs")
    if dfs is None:
        raw_tables = data_context.get("tables", {})
        dfs = {
            table_name: pd.DataFrame(table_data) if isinstance(table_data, list) else table_data
            for table_name, table_data in raw_tables.items()
        }

    as_of_date = data_context.get("as_of_date", "")
    calendar_df = data_context.get("calendar_df")
    if calendar_df is None:
        raw_calendar = data_context.get("calendar", [])
        calendar_df = pd.DataFrame(raw_calendar) if isinstance(raw_calendar, list) else raw_calendar

    exec_scope: dict[str, Any] = {
        "__builtins__": SAFE_BUILTINS,
        "dfs": dfs,
        "pd": pd,
        "np": np,
        "math": math,
        "re": re,
        "unicodedata": unicodedata,
        "as_of_date": as_of_date,
        "calendar_df": calendar_df,
        "result": None,
    }

    try:
        compiled_code = compile(code_string, "<sandbox>", "exec")
        exec(compiled_code, exec_scope)
        computed_result = exec_scope.get("result")

        if isinstance(computed_result, (np.integer, np.int64, np.int32)):
            computed_result = int(computed_result)
        elif isinstance(computed_result, (np.floating, np.float64, np.float32)):
            computed_result = float(computed_result)
        elif isinstance(computed_result, np.bool_):
            computed_result = bool(computed_result)
        elif isinstance(computed_result, pd.Series):
            computed_result = computed_result.tolist()
        elif isinstance(computed_result, pd.DataFrame):
            computed_result = {
                "columns": list(computed_result.columns),
                "rows": computed_result.values.tolist(),
            }

        return ExecutionResult(
            is_success=True,
            output_value=computed_result,
            executed_code=code_string,
        )

    except Exception as runtime_error:
        return ExecutionResult(
            is_success=False,
            error_message=f"RuntimeError: {type(runtime_error).__name__}: {str(runtime_error)}",
            executed_code=code_string,
        )
