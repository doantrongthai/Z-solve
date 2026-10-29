import json
import tempfile
from pathlib import Path

from datamate.ingest import DataIngestor


def test_load_questions() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        q_file = tmp_path / "questions.jsonl"
        items = [
            {
                "id": "q_001",
                "business_id": "biz_101",
                "question": "Hôm nay doanh thu bao nhiêu",
                "as_of_date": "2026-03-01",
            },
            {
                "id": "q_002",
                "business_id": "biz_102",
                "question": "Sản phẩm nào hot nhất",
                "as_of_date": "2026-03-02",
            },
        ]
        with open(q_file, "w", encoding="utf-8") as f:
            for item in items:
                f.write(json.dumps(item) + "\n")

        ingestor = DataIngestor()
        records = ingestor.load_questions(q_file)
        assert len(records) == 2
        assert records[0].id == "q_001"
        assert records[0].business_id == "biz_101"
        assert records[1].id == "q_002"


def test_load_answers() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        ans_file = tmp_path / "answers.jsonl"
        items = [
            {"id": "q_001", "type": "number", "answer": 500000, "alias": []},
            {"id": "q_002", "type": "string", "answer": "Bia Tiger", "alias": ["tiger"]},
        ]
        with open(ans_file, "w", encoding="utf-8") as f:
            for item in items:
                f.write(json.dumps(item) + "\n")

        ingestor = DataIngestor()
        answers_map = ingestor.load_answers(ans_file)
        assert len(answers_map) == 2
        assert answers_map["q_001"].type == "number"
        assert answers_map["q_001"].answer == 500000
        assert answers_map["q_002"].alias == ["tiger"]
