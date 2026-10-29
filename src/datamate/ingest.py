import json
import sqlite3
from pathlib import Path
from typing import Any

import pandas as pd

from .models import GroundTruthRecord, QuestionRecord


class DataIngestor:
    def __init__(self, base_directory: Path | None = None) -> None:
        self.base_directory = base_directory or Path("datamate")

    def load_questions(self, file_path: Path) -> list[QuestionRecord]:
        records: list[QuestionRecord] = []
        with open(file_path, "r", encoding="utf-8") as file_handle:
            for line in file_handle:
                line_str = line.strip()
                if not line_str:
                    continue
                parsed = json.loads(line_str)
                records.append(
                    QuestionRecord(
                        id=parsed["id"],
                        business_id=parsed["business_id"],
                        question=parsed["question"],
                        as_of_date=parsed["as_of_date"],
                    )
                )
        return records

    def load_answers(self, file_path: Path) -> dict[str, GroundTruthRecord]:
        answers_map: dict[str, GroundTruthRecord] = {}
        if not file_path.exists():
            return answers_map
        with open(file_path, "r", encoding="utf-8") as file_handle:
            for line in file_handle:
                line_str = line.strip()
                if not line_str:
                    continue
                parsed = json.loads(line_str)
                answers_map[parsed["id"]] = GroundTruthRecord(
                    id=parsed["id"],
                    type=parsed["type"],
                    answer=parsed.get("answer"),
                    alias=parsed.get("alias", []),
                )
        return answers_map

    def load_calendar(self, file_path: Path) -> pd.DataFrame:
        if not file_path.exists():
            return pd.DataFrame()
        return pd.read_csv(file_path)

    def load_rulebook(self, file_path: Path) -> str:
        if not file_path.exists():
            return ""
        with open(file_path, "r", encoding="utf-8") as file_handle:
            return file_handle.read()

    def load_business_catalog(self, business_directory: Path) -> dict[str, Any]:
        catalog: dict[str, Any] = {
            "business_id": business_directory.name,
            "readme": "",
            "table_sources": {},
            "schema_summary": {},
            "loaded_tables": {},
        }
        if not business_directory.exists():
            return catalog

        readme_file = business_directory / "README.md"
        if readme_file.exists():
            with open(readme_file, "r", encoding="utf-8", errors="ignore") as file_handle:
                catalog["readme"] = file_handle.read()

        for file_path in sorted(business_directory.iterdir()):
            if file_path.is_file():
                suffix = file_path.suffix.lower()
                stem = file_path.stem
                if suffix == ".xlsx":
                    try:
                        excel_file = pd.ExcelFile(file_path, engine="calamine")
                        for sheet_name in excel_file.sheet_names:
                            table_key = f"{stem}__{sheet_name}" if len(excel_file.sheet_names) > 1 else stem
                            sample_df = pd.read_excel(
                                file_path, sheet_name=sheet_name, nrows=5, header=None, engine="calamine"
                            )
                            header_idx = int(sample_df.notna().sum(axis=1).idxmax()) if not sample_df.empty else 0
                            preview_df = pd.read_excel(
                                file_path, sheet_name=sheet_name, header=header_idx, nrows=2, engine="calamine"
                            )
                            preview_df.columns = [str(c).strip() for c in preview_df.columns]
                            catalog["table_sources"][table_key] = {
                                "type": "xlsx",
                                "path": file_path,
                                "sheet_name": sheet_name,
                                "header_idx": header_idx,
                            }
                            catalog["schema_summary"][table_key] = {
                                "columns": list(preview_df.columns),
                            }
                    except Exception:
                        continue
                elif suffix == ".csv":
                    try:
                        preview_df = pd.read_csv(file_path, nrows=2)
                        preview_df.columns = [str(c).strip() for c in preview_df.columns]
                        catalog["table_sources"][stem] = {
                            "type": "csv",
                            "path": file_path,
                        }
                        catalog["schema_summary"][stem] = {
                            "columns": list(preview_df.columns),
                        }
                    except Exception:
                        continue
                elif suffix == ".sqlite":
                    try:
                        connection = sqlite3.connect(file_path)
                        cursor = connection.cursor()
                        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                        table_names = [row[0] for row in cursor.fetchall()]
                        for t_name in table_names:
                            table_key = f"{stem}__{t_name}"
                            preview_df = pd.read_sql_query(f"SELECT * FROM `{t_name}` LIMIT 2", connection)
                            preview_df.columns = [str(c).strip() for c in preview_df.columns]
                            catalog["table_sources"][table_key] = {
                                "type": "sqlite",
                                "path": file_path,
                                "table_name": t_name,
                            }
                            catalog["schema_summary"][table_key] = {
                                "columns": list(preview_df.columns),
                            }
                        connection.close()
                    except Exception:
                        continue
        return catalog

    def get_table_dataframe(self, catalog: dict[str, Any], table_name: str) -> pd.DataFrame:
        if table_name in catalog["loaded_tables"]:
            return catalog["loaded_tables"][table_name]

        if table_name not in catalog["table_sources"]:
            return pd.DataFrame()

        source_info = catalog["table_sources"][table_name]
        src_type = source_info["type"]
        file_path = source_info["path"]

        try:
            if src_type == "xlsx":
                df = pd.read_excel(
                    file_path,
                    sheet_name=source_info["sheet_name"],
                    header=source_info.get("header_idx", 0),
                    engine="calamine",
                )
            elif src_type == "csv":
                df = pd.read_csv(file_path)
            elif src_type == "sqlite":
                connection = sqlite3.connect(file_path)
                df = pd.read_sql_query(f"SELECT * FROM `{source_info['table_name']}`", connection)
                connection.close()
            else:
                df = pd.DataFrame()

            df.columns = [str(c).strip() for c in df.columns]

        except Exception:
            df = pd.DataFrame()

        catalog["loaded_tables"][table_name] = df
        return df
