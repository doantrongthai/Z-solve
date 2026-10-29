from typing import Any

import pandas as pd

from .models import ExecutionResult
from .sandbox import execute_sandboxed_pandas


class CodeExecutor:
    def __init__(self, timeout_seconds: float = 10.0, max_repair_attempts: int = 2) -> None:
        self.timeout_seconds = timeout_seconds
        self.max_repair_attempts = max_repair_attempts

    def prepare_data_context(
        self,
        tables: dict[str, pd.DataFrame],
        as_of_date: str,
        calendar_df: pd.DataFrame,
    ) -> dict[str, Any]:
        return {
            "dfs": tables,
            "as_of_date": as_of_date,
            "calendar_df": calendar_df,
        }

    def execute(
        self,
        code_string: str,
        data_context: dict[str, Any],
    ) -> ExecutionResult:
        try:
            return execute_sandboxed_pandas(
                code_string=code_string,
                data_context=data_context,
                timeout_seconds=self.timeout_seconds,
            )
        except Exception as general_error:
            return ExecutionResult(
                is_success=False,
                error_message=f"ExecutorCrash: {type(general_error).__name__}: {str(general_error)}",
                executed_code=code_string,
            )
