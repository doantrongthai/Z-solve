from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class QuestionRecord:
    id: str
    business_id: str
    question: str
    as_of_date: str


@dataclass(frozen=True)
class GroundTruthRecord:
    id: str
    type: str
    answer: Any
    alias: list[Any] = field(default_factory=list)


@dataclass(frozen=True)
class SubmissionRecord:
    id: str
    type: str
    answer: Any = None

    def to_dict(self) -> dict[str, Any]:
        if self.type == "abstain":
            return {"id": self.id, "type": "abstain"}
        return {"id": self.id, "type": self.type, "answer": self.answer}


@dataclass(frozen=True)
class ExecutionResult:
    is_success: bool
    output_value: Any = None
    error_message: str | None = None
    executed_code: str = ""
