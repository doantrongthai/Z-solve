from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class PipelineConfig:
    random_seed: int = 42
    executor_timeout_seconds: float = 10.0
    max_repair_attempts: int = 2
    max_code_characters: int = 50000
    allow_code_execution: bool = True
    default_split: str = "public_test"
    base_data_directory: Path = Path("datamate")
    results_directory: Path = Path("results")
    submission_filename: str = "submission.jsonl"
    prompts_directory: Path = Path("prompts")
    prompt_version: str = "system_prompt_v1.txt"
    model_name: str = "Qwen/Qwen2.5-Coder-7B-Instruct"
    enable_llm: bool = False
    load_in_4bit: bool = False
    load_in_8bit: bool = False
    confidence_threshold: float = 0.5
    supported_types: tuple[str, ...] = field(
        default_factory=lambda: (
            "number",
            "percent",
            "string",
            "date",
            "boolean",
            "list",
            "table",
            "unanswerable",
            "abstain",
        )
    )

    def get_split_directory(self, split: str) -> Path:
        return self.base_data_directory / split / split

    def get_questions_path(self, split: str) -> Path:
        return self.get_split_directory(split) / "questions.jsonl"

    def get_answers_path(self, split: str) -> Path:
        return self.get_split_directory(split) / "answers.jsonl"

    def get_calendar_path(self, split: str) -> Path:
        return self.get_split_directory(split) / "calendar.csv"

    def get_rulebook_path(self, split: str) -> Path:
        return self.get_split_directory(split) / "rulebook.md"

    def get_business_data_directory(self, split: str, business_id: str) -> Path:
        return self.get_split_directory(split) / "data" / business_id

    def get_submission_path(self, output_path: Path | None = None) -> Path:
        if output_path is not None:
            return output_path
        return self.results_directory / self.submission_filename

