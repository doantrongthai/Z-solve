import math
import unicodedata
from typing import Any


class AnswerFormatter:
    @staticmethod
    def normalize_string(raw_text: str) -> str:
        normalized = unicodedata.normalize("NFC", str(raw_text))
        return " ".join(normalized.strip().split())

    @staticmethod
    def format_number(value: Any, is_currency: bool = False) -> int | float:
        if isinstance(value, str):
            cleaned = value.replace(",", "").replace(" ", "").replace("đ", "").replace("VND", "").strip()
            numeric_val = float(cleaned)
        elif isinstance(value, (int, float)):
            numeric_val = float(value)
        else:
            numeric_val = float(value)

        if math.isnan(numeric_val) or math.isinf(numeric_val):
            raise ValueError("Numeric value cannot be NaN or Inf")

        if is_currency or numeric_val.is_integer():
            return int(round(numeric_val))
        return round(numeric_val, 2)

    @staticmethod
    def format_percent(value: Any) -> float:
        if isinstance(value, str):
            cleaned = value.replace("%", "").replace(",", ".").replace(" ", "").strip()
            numeric_val = float(cleaned)
        elif isinstance(value, (int, float)):
            numeric_val = float(value)
        else:
            numeric_val = float(value)

        if math.isnan(numeric_val) or math.isinf(numeric_val):
            raise ValueError("Percent value cannot be NaN or Inf")

        return round(numeric_val, 2)

    @staticmethod
    def format_date(value: Any) -> str:
        text = str(value).strip()
        if len(text) >= 10 and text[4] == "-" and text[7] == "-":
            return text[:10]
        if len(text) >= 7 and text[4] == "-":
            return text[:7]
        return text

    @staticmethod
    def format_boolean(value: Any) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            lowered = value.strip().lower()
            if lowered in ("true", "1", "có", "dung", "đúng", "yes"):
                return True
            if lowered in ("false", "0", "không", "khong", "sai", "no"):
                return False
        if isinstance(value, (int, float)):
            return bool(value)
        raise ValueError(f"Cannot parse boolean from {value}")

    @staticmethod
    def format_list(value: Any) -> list[Any]:
        if isinstance(value, list):
            items = value
        elif isinstance(value, (tuple, set)):
            items = list(value)
        elif isinstance(value, (int, float, str)):
            items = [value]
        else:
            items = list(value)

        formatted_items = []
        for item in items:
            if isinstance(item, (int, float)):
                if isinstance(item, float) and item.is_integer():
                    formatted_items.append(int(item))
                elif isinstance(item, float):
                    formatted_items.append(round(item, 2))
                else:
                    formatted_items.append(item)
            elif isinstance(item, str):
                formatted_items.append(AnswerFormatter.normalize_string(item))
            else:
                formatted_items.append(item)
        return formatted_items

    @staticmethod
    def format_table(value: Any) -> dict[str, Any]:
        if not isinstance(value, dict) or "columns" not in value or "rows" not in value:
            raise ValueError("Table must contain columns and rows keys")
        columns = [AnswerFormatter.normalize_string(c) for c in value["columns"]]
        rows = []
        for row in value["rows"]:
            formatted_row = []
            for cell in row:
                if isinstance(cell, (int, float)):
                    if isinstance(cell, float) and cell.is_integer():
                        formatted_row.append(int(cell))
                    elif isinstance(cell, float):
                        formatted_row.append(round(cell, 2))
                    else:
                        formatted_row.append(cell)
                elif isinstance(cell, str):
                    formatted_row.append(AnswerFormatter.normalize_string(cell))
                else:
                    formatted_row.append(cell)
            rows.append(formatted_row)
        return {"columns": columns, "rows": rows}

    @classmethod
    def format_answer(cls, answer_type: str, raw_value: Any) -> Any:
        if answer_type == "abstain":
            return None
        if answer_type == "unanswerable":
            return None
        if raw_value is None:
            return None

        if answer_type == "number":
            return cls.format_number(raw_value)
        if answer_type == "percent":
            return cls.format_percent(raw_value)
        if answer_type == "string":
            return cls.normalize_string(str(raw_value))
        if answer_type == "date":
            return cls.format_date(raw_value)
        if answer_type == "boolean":
            return cls.format_boolean(raw_value)
        if answer_type == "list":
            return cls.format_list(raw_value)
        if answer_type == "table":
            return cls.format_table(raw_value)

        raise ValueError(f"Unsupported answer type: {answer_type}")

