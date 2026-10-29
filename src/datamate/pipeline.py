import json
import logging
from pathlib import Path
from typing import Any

from .abstain import AbstainPolicy
from .config import PipelineConfig
from .executor import CodeExecutor
from .formatter import AnswerFormatter
from .ingest import DataIngestor
from .models import GroundTruthRecord, QuestionRecord, SubmissionRecord
from .planner import QuestionPlanner


class DataMatePipeline:
    def __init__(self, config: PipelineConfig | None = None) -> None:
        self.config = config or PipelineConfig()
        self.logger = logging.getLogger("DataMatePipeline")
        self.ingestor = DataIngestor(self.config.base_data_directory)
        llm_client = None
        if self.config.enable_llm:
            from .llm import LLMConfig, LocalLLMClient

            llm_config = LLMConfig(
                model_name=self.config.model_name,
                load_in_4bit=self.config.load_in_4bit,
                load_in_8bit=self.config.load_in_8bit,
            )
            llm_client = LocalLLMClient(llm_config)

        self.planner = QuestionPlanner(
            self.config.prompts_directory / self.config.prompt_version,
            llm_client=llm_client,
        )
        self.executor = CodeExecutor(
            timeout_seconds=self.config.executor_timeout_seconds,
            max_repair_attempts=self.config.max_repair_attempts,
        )
        self.formatter = AnswerFormatter()
        self.abstain_policy = AbstainPolicy(
            confidence_threshold=self.config.confidence_threshold
        )

    def solve_single_question(
        self,
        question_record: QuestionRecord,
        business_catalog: dict[str, Any],
        calendar_df: Any,
    ) -> SubmissionRecord:
        try:
            generated_code, detected_type = self.planner.generate_code(
                question=question_record.question,
                as_of_date=question_record.as_of_date,
                schema_summary=business_catalog["schema_summary"],
            )

            if not generated_code:
                return SubmissionRecord(
                    id=question_record.id,
                    type="abstain",
                    answer=None,
                )

            target_tables = self.planner.select_relevant_tables(
                question_record.question,
                business_catalog["schema_summary"],
                question_record.as_of_date,
            )
            filtered_dfs = {
                t_name: self.ingestor.get_table_dataframe(business_catalog, t_name)
                for t_name in target_tables
            }

            data_context = self.executor.prepare_data_context(
                tables=filtered_dfs,
                as_of_date=question_record.as_of_date,
                calendar_df=calendar_df,
            )

            execution_res = self.executor.execute(generated_code, data_context)

            if self.abstain_policy.should_abstain(execution_res, detected_type):
                return SubmissionRecord(
                    id=question_record.id,
                    type="abstain",
                    answer=None,
                )

            formatted_answer = self.formatter.format_answer(
                detected_type, execution_res.output_value
            )

            return SubmissionRecord(
                id=question_record.id,
                type=detected_type,
                answer=formatted_answer,
            )

        except Exception as error:
            self.logger.warning(
                "Error processing question %s: %s", question_record.id, str(error)
            )
            return SubmissionRecord(
                id=question_record.id,
                type="abstain",
                answer=None,
            )

    def run_split(
        self,
        split: str,
        output_file_path: Path | None = None,
        max_samples: int | None = None,
    ) -> tuple[list[SubmissionRecord], dict[str, Any]]:
        questions_file = self.config.get_questions_path(split)
        calendar_file = self.config.get_calendar_path(split)
        answers_file = self.config.get_answers_path(split)

        questions = self.ingestor.load_questions(questions_file)
        if max_samples:
            questions = questions[:max_samples]

        calendar_df = self.ingestor.load_calendar(calendar_file)
        ground_truth_map = self.ingestor.load_answers(answers_file)

        business_cache: dict[str, dict[str, Any]] = {}
        submissions: list[SubmissionRecord] = []

        for question in questions:
            biz_id = question.business_id
            if biz_id not in business_cache:
                biz_dir = self.config.get_business_data_directory(split, biz_id)
                business_cache[biz_id] = self.ingestor.load_business_catalog(biz_dir)

            record = self.solve_single_question(
                question_record=question,
                business_catalog=business_cache[biz_id],
                calendar_df=calendar_df,
            )
            submissions.append(record)

        destination_path = self.config.get_submission_path(output_file_path)
        destination_path.parent.mkdir(parents=True, exist_ok=True)

        with open(destination_path, "w", encoding="utf-8") as out_file:
            for sub in submissions:
                out_file.write(json.dumps(sub.to_dict(), ensure_ascii=False) + "\n")

        evaluation_metrics: dict[str, Any] = {
            "total_questions": len(questions),
            "generated_records": len(submissions),
            "destination_path": str(destination_path),
        }

        if ground_truth_map:
            score, details = self.evaluate_penalized_accuracy(submissions, ground_truth_map)
            evaluation_metrics["penalized_accuracy"] = score
            evaluation_metrics["evaluation_breakdown"] = details

        return submissions, evaluation_metrics

    def evaluate_penalized_accuracy(
        self,
        submissions: list[SubmissionRecord],
        ground_truth: dict[str, GroundTruthRecord],
    ) -> tuple[float, dict[str, int]]:
        correct_count = 0
        wrong_count = 0
        abstain_count = 0

        for sub in submissions:
            if sub.id not in ground_truth:
                continue
            gt = ground_truth[sub.id]

            if sub.type == "abstain":
                abstain_count += 1
                continue

            if sub.type != gt.type:
                wrong_count += 1
                continue

            is_match = False
            if sub.type == "unanswerable":
                is_match = (gt.type == "unanswerable")
            elif sub.type in ("number", "percent"):
                try:
                    is_match = abs(float(sub.answer) - float(gt.answer)) < 1e-4
                except (TypeError, ValueError):
                    is_match = False
            elif sub.type == "string":
                is_match = (
                    AnswerFormatter.normalize_string(str(sub.answer)).lower()
                    == AnswerFormatter.normalize_string(str(gt.answer)).lower()
                )
            elif sub.type == "boolean":
                is_match = bool(sub.answer) == bool(gt.answer)
            elif sub.type in ("date", "list", "table"):
                is_match = sub.answer == gt.answer

            if is_match:
                correct_count += 1
            else:
                wrong_count += 1

        total = len(submissions)
        if total == 0:
            score = 0.0
        else:
            score = (correct_count * 1.0 + abstain_count * 0.0 - wrong_count * 1.0) / total

        breakdown = {
            "correct": correct_count,
            "wrong": wrong_count,
            "abstain": abstain_count,
            "total": total,
        }
        return score, breakdown
