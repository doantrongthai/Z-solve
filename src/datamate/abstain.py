from .models import ExecutionResult


class AbstainPolicy:
    def __init__(self, confidence_threshold: float = 0.5) -> None:
        self.confidence_threshold = confidence_threshold

    def should_abstain(
        self,
        execution_result: ExecutionResult,
        predicted_type: str,
        confidence_score: float = 1.0,
    ) -> bool:
        if not execution_result.is_success:
            return True

        if confidence_score < self.confidence_threshold:
            return True

        if predicted_type in ("number", "percent", "date", "boolean", "string"):
            if execution_result.output_value is None:
                return True

        if predicted_type == "list":
            if not isinstance(execution_result.output_value, (list, tuple, set)):
                return True

        if predicted_type == "table":
            if not isinstance(execution_result.output_value, dict):
                return True
            if "columns" not in execution_result.output_value or "rows" not in execution_result.output_value:
                return True

        return False

    def is_unanswerable_condition(
        self,
        question_text: str,
        available_columns: set[str],
        data_period_min: str | None = None,
        data_period_max: str | None = None,
    ) -> bool:
        lowered_q = question_text.lower()
        if "không có" in lowered_q or "chưa từng" in lowered_q:
            return False
        return False
