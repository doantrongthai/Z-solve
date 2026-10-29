import argparse
import json
import math
import re
import sys
from pathlib import Path
from typing import Any

from datamate.config import PipelineConfig

DATE_PATTERN = re.compile(r"^\d{4}-(0[1-9]|1[0-2])(-(0[1-9]|[12]\d|3[01]))?$")


class SubmissionValidator:
    def __init__(self, config: PipelineConfig | None = None) -> None:
        self.config = config or PipelineConfig()
        self.allowed_types = set(self.config.supported_types)

    def validate_file(
        self, submission_path: Path, questions_path: Path
    ) -> tuple[bool, list[str]]:
        errors: list[str] = []

        if not submission_path.exists():
            return False, [f"Submission file does not exist: {submission_path}"]

        if not questions_path.exists():
            return False, [f"Questions file does not exist: {questions_path}"]

        try:
            with open(submission_path, "r", encoding="utf-8") as file_handle:
                file_handle.read()
        except UnicodeDecodeError as decode_error:
            return False, [f"File is not valid UTF-8: {str(decode_error)}"]

        expected_ids: list[str] = []
        with open(questions_path, "r", encoding="utf-8") as file_handle:
            for line in file_handle:
                line_str = line.strip()
                if line_str:
                    expected_ids.append(json.loads(line_str)["id"])

        expected_ids_set = set(expected_ids)
        seen_ids: list[str] = []
        seen_ids_set: set[str] = set()

        line_number = 0
        with open(submission_path, "r", encoding="utf-8") as file_handle:
            for line in file_handle:
                line_number += 1
                line_str = line.strip()
                if not line_str:
                    errors.append(f"Line {line_number}: Empty line encountered")
                    continue

                try:
                    record = json.loads(line_str)
                except json.JSONDecodeError as json_error:
                    errors.append(f"Line {line_number}: Invalid JSON: {json_error.msg}")
                    continue

                if not isinstance(record, dict):
                    errors.append(f"Line {line_number}: Record is not a JSON object")
                    continue

                record_id = record.get("id")
                if not record_id or not isinstance(record_id, str):
                    errors.append(f"Line {line_number}: Missing or non-string 'id'")
                    continue

                if record_id in seen_ids_set:
                    errors.append(f"Line {line_number} [ID {record_id}]: Duplicate ID")
                else:
                    seen_ids.append(record_id)
                    seen_ids_set.add(record_id)

                if record_id not in expected_ids_set:
                    errors.append(f"Line {line_number} [ID {record_id}]: Unknown ID not present in questions")

                rec_type = record.get("type")
                if not rec_type or rec_type not in self.allowed_types:
                    errors.append(f"Line {line_number} [ID {record_id}]: Invalid type '{rec_type}'")
                    continue

                answer = record.get("answer")
                type_error = self.validate_answer_format(record_id, rec_type, answer)
                if type_error:
                    errors.append(f"Line {line_number} [ID {record_id}]: {type_error}")

        missing_ids = expected_ids_set - seen_ids_set
        if missing_ids:
            errors.append(f"Missing {len(missing_ids)} expected IDs: {sorted(list(missing_ids))[:10]}...")

        is_valid = len(errors) == 0
        return is_valid, errors

    def validate_answer_format(
        self, record_id: str, rec_type: str, answer: Any
    ) -> str | None:
        if rec_type in ("abstain", "unanswerable"):
            if answer is not None:
                return f"Type '{rec_type}' must have answer as null, found: {answer}"
            return None

        if answer is None:
            return f"Type '{rec_type}' cannot have null answer"

        if rec_type == "number":
            if isinstance(answer, bool):
                return "Boolean is not a valid number"
            if not isinstance(answer, (int, float)):
                return f"Expected number (int/float), got {type(answer).__name__}"
            if math.isnan(answer) or math.isinf(answer):
                return "Number cannot be NaN or Infinite"

        elif rec_type == "percent":
            if isinstance(answer, bool):
                return "Boolean is not a valid percent"
            if not isinstance(answer, (int, float)):
                return f"Expected percent (float/int), got {type(answer).__name__}"
            if math.isnan(answer) or math.isinf(answer):
                return "Percent cannot be NaN or Infinite"

        elif rec_type == "string":
            if not isinstance(answer, str) or not answer.strip():
                return f"Expected non-empty string, got {type(answer).__name__}"

        elif rec_type == "date":
            if not isinstance(answer, str) or not DATE_PATTERN.match(answer.strip()):
                return f"Expected date in YYYY-MM-DD or YYYY-MM, got '{answer}'"

        elif rec_type == "boolean":
            if not isinstance(answer, bool):
                return f"Expected boolean True/False, got {type(answer).__name__}"

        elif rec_type == "list":
            if not isinstance(answer, list):
                return f"Expected list array, got {type(answer).__name__}"

        elif rec_type == "table":
            if not isinstance(answer, dict):
                return f"Expected table dict, got {type(answer).__name__}"
            if "columns" not in answer or "rows" not in answer:
                return "Table missing 'columns' or 'rows'"
            if not isinstance(answer["columns"], list) or not isinstance(answer["rows"], list):
                return "Table columns and rows must be lists"

        return None


def main() -> None:
    parser = argparse.ArgumentParser(description="DataMate Submission Validator")
    parser.add_argument("--submission", type=Path, required=True)
    parser.add_argument("--questions", type=Path, required=True)
    args = parser.parse_args()

    validator = SubmissionValidator()
    is_valid, error_list = validator.validate_file(args.submission, args.questions)

    if is_valid:
        print(f"VALIDATION PASSED: {args.submission} is compliant with DataMate schema.")
        sys.exit(0)
    else:
        print(f"VALIDATION FAILED with {len(error_list)} errors:")
        for err in error_list[:20]:
            print(f"  - {err}")
        if len(error_list) > 20:
            print(f"  ... and {len(error_list) - 20} more errors.")
        sys.exit(1)


if __name__ == "__main__":
    main()

