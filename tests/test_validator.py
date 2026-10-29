import json
import tempfile
from pathlib import Path

from scripts.validate_submission import SubmissionValidator


def test_validator_success() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        q_file = tmp_path / "questions.jsonl"
        sub_file = tmp_path / "submission.jsonl"

        questions = [
            {"id": "q_1", "business_id": "biz_1", "question": "test 1", "as_of_date": "2026-01-01"},
            {"id": "q_2", "business_id": "biz_1", "question": "test 2", "as_of_date": "2026-01-01"},
            {"id": "q_3", "business_id": "biz_1", "question": "test 3", "as_of_date": "2026-01-01"},
        ]
        submissions = [
            {"id": "q_1", "type": "number", "answer": 100},
            {"id": "q_2", "type": "percent", "answer": 15.5},
            {"id": "q_3", "type": "abstain", "answer": None},
        ]

        with open(q_file, "w", encoding="utf-8") as f:
            for q in questions:
                f.write(json.dumps(q) + "\n")

        with open(sub_file, "w", encoding="utf-8") as f:
            for s in submissions:
                f.write(json.dumps(s) + "\n")

        validator = SubmissionValidator()
        is_valid, errors = validator.validate_file(sub_file, q_file)
        assert is_valid is True
        assert len(errors) == 0


def test_validator_missing_id() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        q_file = tmp_path / "questions.jsonl"
        sub_file = tmp_path / "submission.jsonl"

        questions = [
            {"id": "q_1", "business_id": "biz_1", "question": "test 1", "as_of_date": "2026-01-01"},
            {"id": "q_2", "business_id": "biz_1", "question": "test 2", "as_of_date": "2026-01-01"},
        ]
        submissions = [
            {"id": "q_1", "type": "number", "answer": 100},
        ]

        with open(q_file, "w", encoding="utf-8") as f:
            for q in questions:
                f.write(json.dumps(q) + "\n")

        with open(sub_file, "w", encoding="utf-8") as f:
            for s in submissions:
                f.write(json.dumps(s) + "\n")

        validator = SubmissionValidator()
        is_valid, errors = validator.validate_file(sub_file, q_file)
        assert is_valid is False
        assert any("Missing" in err for err in errors)


def test_validator_invalid_type_answer() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        q_file = tmp_path / "questions.jsonl"
        sub_file = tmp_path / "submission.jsonl"

        questions = [{"id": "q_1", "business_id": "biz_1", "question": "test", "as_of_date": "2026-01-01"}]
        submissions = [{"id": "q_1", "type": "number", "answer": "100 VND"}]

        with open(q_file, "w", encoding="utf-8") as f:
            for q in questions:
                f.write(json.dumps(q) + "\n")

        with open(sub_file, "w", encoding="utf-8") as f:
            for s in submissions:
                f.write(json.dumps(s) + "\n")

        validator = SubmissionValidator()
        is_valid, errors = validator.validate_file(sub_file, q_file)
        assert is_valid is False
        assert any("Expected number" in err for err in errors)

