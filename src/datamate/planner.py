import re
import unicodedata
from pathlib import Path
from typing import Any

from .models import QuestionRecord


def remove_accents(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    filtered = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return filtered.replace("đ", "d").replace("Đ", "D").lower()


class QuestionPlanner:
    def __init__(
        self,
        prompt_template_path: Path | None = None,
        llm_client: Any | None = None,
    ) -> None:
        self.prompt_template = ""
        self.llm_client = llm_client
        if prompt_template_path and prompt_template_path.exists():
            with open(prompt_template_path, "r", encoding="utf-8") as file_handle:
                self.prompt_template = file_handle.read()

    def infer_expected_type(self, question: str) -> str:
        q_clean = remove_accents(question)

        percent_cues = ("ti le", "ty le", "phan tram", "%", "tang truong", "ti trong", "ty trong")
        if any(term in q_clean for term in percent_cues):
            return "percent"

        date_cues = ("ngay nao", "khi nao", "thoi gian nao", "hom nao", "thang nao")
        if any(term in q_clean for term in date_cues):
            if not any(term in q_clean for term in ("doanh thu", "bao nhieu", "ban duoc")):
                return "date"

        bool_cues = ("co phai", "co dung", "phai khong", "dung khong", "lieu co")
        if any(term in q_clean for term in bool_cues):
            return "boolean"

        list_cues = ("danh sach", "top ", "nhung", "liet ke", "cac mat hang", "cac khach hang")
        if any(term in q_clean for term in list_cues):
            if "bang" in q_clean or "chi tiet" in q_clean:
                return "table"
            return "list"

        string_cues = ("san pham nao", "mat hang nao", "mon nao", "ai la", "khach hang nao", "xe nao", "hang nao")
        if any(term in q_clean for term in string_cues):
            return "string"

        number_cues = (
            "bao nhieu",
            "bao nhiu",
            "bnhiu",
            "bn",
            "may",
            "tong",
            "doanh thu",
            "tien",
            "so luong",
            "so don",
            "cong no",
            "gia",
            "lai",
            "loi nhuan",
            "chi phi",
        )
        if any(term in q_clean for term in number_cues):
            return "number"

        return "number"

    def select_relevant_tables(
        self,
        question: str,
        schema_summary: dict[str, dict[str, Any]],
        as_of_date: str = "",
    ) -> list[str]:
        q_clean = remove_accents(question)
        month_match = re.search(r"(?:thang\s*|th|)(\d{1,2})[/\-](202\d)", q_clean)
        if not month_match:
            month_match = re.search(r"thang\s*(\d{1,2})", q_clean)
        year_match = re.search(r"(202\d)", q_clean)

        if not month_match and as_of_date and any(k in q_clean for k in ["hom nay", "hnay", "thang nay"]):
            parts = as_of_date.split("-")
            if len(parts) >= 2:
                m_val = int(parts[1])
                y_str = parts[0]
                m_tokens = [f"t{m_val:02d}", f"t{m_val}", f"thang {m_val:02d}", f"thang {m_val}"]
                time_matches = [
                    t for t in schema_summary.keys()
                    if any(v in remove_accents(t) for v in m_tokens) and y_str in t
                ]
                if time_matches:
                    return time_matches[:3]

        if month_match and year_match:
            m_val = int(month_match.group(1))
            m_tokens = [
                f"t{m_val:02d}",
                f"t{m_val}",
                f"thang {m_val:02d}",
                f"thang {m_val}",
                f"-{m_val:02d}-",
                f"_{m_val:02d}_",
            ]
            y_str = year_match.group(1)
            time_matches = [
                t for t in schema_summary.keys()
                if any(v in remove_accents(t) for v in m_tokens) and y_str in t
            ]
            if time_matches:
                return time_matches[:3]

        selected: list[str] = []

        keywords_map = {
            "ban_hang": [
                "ban",
                "doanh thu",
                "don hang",
                "don",
                "huy",
                "tien",
                "khach",
                "mat hang",
                "mon",
                "hoa don",
            ],
            "nhap_hang": ["nhap", "phieu nhap", "nha cung cap", "gia nhap"],
            "ton_kho": ["ton", "kho", "het hang", "han dung", "het han"],
            "cong_no": ["no", "cong no", "tuoi no", "tra gop", "chua tra"],
            "danh_muc": ["gia ban", "bang gia", "quy doi", "hoat chat", "ke don"],
        }

        for table_name, meta in schema_summary.items():
            t_clean = remove_accents(table_name)
            cols_clean = " ".join(remove_accents(str(c)) for c in meta.get("columns", []))

            for category, keywords in keywords_map.items():
                if any(kw in q_clean for kw in keywords):
                    if any(kw in t_clean or kw in cols_clean for kw in keywords):
                        if table_name not in selected:
                            selected.append(table_name)

        if not selected:
            selected = list(schema_summary.keys())[:5]

        if month_match:
            m_val = int(month_match.group(1))
            m_tokens = [
                f"t{m_val:02d}",
                f"t{m_val}",
                f"thang {m_val:02d}",
                f"thang {m_val}",
                f"-{m_val:02d}-",
                f"_{m_val:02d}_",
            ]
            filtered_by_time = [
                t for t in selected
                if any(k in remove_accents(t) for k in m_tokens)
            ]
            if year_match:
                y_str = year_match.group(1)
                filtered_with_year = [t for t in filtered_by_time if y_str in t]
                if filtered_with_year:
                    return filtered_with_year[:3]
            if filtered_by_time:
                return filtered_by_time[:3]

        return selected[:5]

    def generate_code(
        self,
        question: str,
        as_of_date: str,
        schema_summary: dict[str, dict[str, Any]],
    ) -> tuple[str | None, str]:
        q_clean = remove_accents(question)

        has_compare = any(
            k in q_clean
            for k in [
                "%",
                "phan tram",
                "so voi",
                "cung ky",
                "hon hay kem",
                "cao hay thap",
                "thay doi",
                "chenh",
                "ti le",
                "ty le",
                "chiem",
            ]
        )

        is_cancel_q = bool(re.search(r"\bhuy\b", q_clean)) and any(
            k in q_clean for k in ["ti le", "ty le", "%", "phan tram", "chiem bao nhieu", "may %", "ti ne"]
        )
        if is_cancel_q:
            month = None
            year = None
            if "thang nay" in q_clean and as_of_date:
                parts = as_of_date.split("-")
                month = int(parts[1])
                year = int(parts[0])
            else:
                m_pat1 = re.search(r"(?:thang\s*|th\s*|t)(\d{1,2})\s*nam\s*(202\d)", q_clean)
                m_pat2 = re.search(r"(?:thang\s*|th\s*|t|)(\d{1,2})[/\-](202\d)", q_clean)
                m_pat3 = re.search(r"(?:thang\s*|th\s*|t|)(\d{1,2})[/\-](2\d)", q_clean)
                if m_pat1:
                    month = int(m_pat1.group(1))
                    year = int(m_pat1.group(2))
                elif m_pat2:
                    month = int(m_pat2.group(1))
                    year = int(m_pat2.group(2))
                elif m_pat3:
                    month = int(m_pat3.group(1))
                    year = 2000 + int(m_pat3.group(2))

            if month is not None and year is not None:
                code_lines = [
                    "result = None",
                    f"month_num = {month}",
                    f"year_str = '{year}'",
                    f"month_str = '{month:02d}'",
                    "def rm_acc(txt):",
                    "    n = unicodedata.normalize('NFKD', str(txt).replace('đ', 'd').replace('Đ', 'D'))",
                    "    return ''.join(c for c in n if not unicodedata.combining(c)).lower()",
                    "ord_keys = ['ma don', 'ma bill', 'ma hoa don', 'mahoadon', 'madon', 'bill', 'so ct']",
                    "st_keys = ['trang thai', 'tinh trang', 'status', 'tinhtrang', 'trangthai', 'tt don', 'xu ly']",
                    "for t_name, df in dfs.items():",
                    "    if df.empty:",
                    "        continue",
                    "    t_clean = t_name.lower()",
                    "    m_toks = [f't{month_num:02d}', f't{month_num}', f'_{month_num:02d}_', f'-{month_num:02d}-']",
                    "    is_month_table = any(k in t_clean for k in m_toks) and year_str in t_clean",
                    "    is_gen_table = any(k in t_clean for k in ['don_hang', 'donhang', 'chi_tiet_hoa_don'])",
                    "    if not (is_month_table or is_gen_table):",
                    "        continue",
                    "    order_cols = [c for c in df.columns if any(k in rm_acc(c) for k in ord_keys)]",
                    "    status_cols = [c for c in df.columns if any(k in rm_acc(c) for k in st_keys)]",
                    "    date_cols = [c for c in df.columns if any(k in rm_acc(c) for k in ['ngay', 'date'])]",
                    "    if not date_cols:",
                    "        date_cols = [c for c in df.columns if 'thoi gian' in rm_acc(c)]",
                    "    if not status_cols or not order_cols:",
                    "        continue",
                    "    ord_c = order_cols[0]",
                    "    st_c = status_cols[0]",
                    "    working_df = df.copy()",
                    "    valid_rows = working_df[ord_c].notna() & (working_df[ord_c].astype(str) != str(ord_c))",
                    "    working_df = working_df[valid_rows]",
                    "    working_df[ord_c] = working_df[ord_c].ffill()",
                    "    working_df[st_c] = working_df[st_c].ffill()",
                    "    if not is_month_table:",
                    "        if not date_cols:",
                    "            continue",
                    "        dt_c = date_cols[0]",
                    "        raw_dt = working_df[dt_c]",
                    "        num_dt = pd.to_numeric(raw_dt, errors='coerce')",
                    "        s_dt = pd.to_datetime(num_dt, unit='D', origin='1899-12-30')",
                    "        clean_dt_str = raw_dt.astype(str).str.replace(' thg ', '/')",
                    "        is_iso = clean_dt_str.str.startswith(('202', '201', '199'))",
                    "        iso_dt = pd.to_datetime(clean_dt_str.where(is_iso), errors='coerce')",
                    "        dmy_dt = pd.to_datetime(clean_dt_str.where(~is_iso), errors='coerce', dayfirst=True)",
                    "        str_dt = iso_dt.fillna(dmy_dt)",
                    "        p_dt = s_dt.fillna(str_dt)",
                    "        mask = (p_dt.dt.year == int(year_str)) & (p_dt.dt.month == month_num)",
                    "        working_df = working_df[mask]",
                    "    if working_df.empty:",
                    "        continue",
                    "    order_status = working_df.groupby(ord_c)[st_c].first().astype(str).str.lower()",
                    "    tot = len(order_status)",
                    "    if tot == 0:",
                    "        continue",
                    "    canc = order_status.str.contains('hủy|huy|cancel').sum()",
                    "    if canc > 0:",
                    "        result = round(canc / tot * 100, 2)",
                    "    break",
                ]
                return "\n".join(code_lines), "percent"

        is_today_q = any(k in q_clean for k in ["hom nay", "hnay", "bua nay"])
        is_rev_q = any(k in q_clean for k in ["doanh thu", "dthu", "tien ban", "ban dc", "ban duoc", "thu"])
        is_amount_q = any(k in q_clean for k in ["bao nhieu", "bao nhiu", "bnhiu", "bn", "may", "nhieu"])
        is_ytd = any(k in q_clean for k in ["dau nam", "tu 1/1", "tu ngay 1/1", "nam nay", "7 ngay", "tuan nay"])
        is_debt = any(k in q_clean for k in ["tra gop", "ban chiu", "ghi no", "so no", "con no", "muon hon", "sau hom"])
        is_delivery = any(k in q_clean for k in ["cho thanh", "giao tu", "dot", "chuyen"])
        is_order_count = any(k in q_clean for k in ["may don", "bao nhieu don", "bn don", "bnhiu don", "don hang"])
        is_today_rev = is_today_q and is_rev_q and is_amount_q and not is_order_count
        is_clean_today = not has_compare and not is_ytd and not is_debt and not is_delivery
        if is_today_rev and is_clean_today:
            code_lines = [
                "result = None",
                f"target_date = '{as_of_date}'",
                "def rm_acc(txt):",
                "    n = unicodedata.normalize('NFKD', str(txt).replace('đ', 'd').replace('Đ', 'D'))",
                "    return ''.join(c for c in n if not unicodedata.combining(c)).lower()",
                "m_keys = ['tong tien', 'thanh tien', 'amount', 'tien hang', 'tien']",
                "d_keys = ['ngay dat', 'ngay mua', 'ngay lap', 'ngay', 'date']",
                "s_keys = ['trang thai', 'status', 'tinh trang', 'ghi chu tt']",
                "for t_name, df in dfs.items():",
                "    if df.empty or not t_name.lower().startswith('banhang_t'):",
                "        continue",
                "    money_cols = [c for c in df.columns if any(k in rm_acc(c) for k in m_keys)]",
                "    date_cols = [c for c in df.columns if any(k in rm_acc(c) for k in d_keys)]",
                "    status_cols = [c for c in df.columns if any(k in rm_acc(c) for k in s_keys)]",
                "    if not money_cols or not date_cols:",
                "        continue",
                "    m_c = money_cols[0]",
                "    d_c = date_cols[0]",
                "    w_df = df.copy()",
                "    if status_cols:",
                "        st = w_df[status_cols[0]].astype(str).str.lower()",
                "        w_df = w_df[~st.str.contains('hủy|huy|trả|tra|cancel')]",
                "    dt_s = w_df[d_c].astype(str)",
                "    t_parts = target_date.split('-')",
                "    y, m, d = t_parts[0], t_parts[1], t_parts[2]",
                "    m_d = f'{d}/{m}/{y}'",
                "    m_d2 = f'{int(d)}/{int(m)}/{y}'",
                "    num_dt = pd.to_numeric(w_df[d_c], errors='coerce')",
                "    s_dt = pd.to_datetime(num_dt, unit='D', origin='1899-12-30')",
                "    is_iso = dt_s.str.startswith(('202', '201', '199'))",
                "    iso_dt = pd.to_datetime(dt_s.where(is_iso), errors='coerce')",
                "    dmy_dt = pd.to_datetime(dt_s.where(~is_iso), errors='coerce', dayfirst=True)",
                "    str_dt = iso_dt.fillna(dmy_dt)",
                "    p_dt = s_dt.fillna(str_dt)",
                "    dt_match = (p_dt.dt.strftime('%Y-%m-%d') == target_date)",
                "    str_match = dt_s.str.contains(target_date) | dt_s.str.contains(m_d) | dt_s.str.contains(m_d2)",
                "    w_df = w_df[dt_match | str_match]",
                "    if w_df.empty:",
                "        continue",
                "    def clean_m(val):",
                "        s = str(val).lower().replace('đ', '').replace('vnd', '').strip()",
                "        if not s or s in ('nan', 'none'):",
                "            return 0.0",
                "        if s.endswith('k'):",
                "            return float(s[:-1].replace('.', '').replace(',', '.')) * 1000",
                "        if '.' in s and ',' in s:",
                "            if s.rfind('.') > s.rfind(','):",
                "                s = s.replace(',', '')",
                "            else:",
                "                s = s.replace('.', '').replace(',', '.')",
                "        elif ',' in s:",
                "            parts = s.split(',')",
                "            if len(parts) == 2 and len(parts[1]) in (1, 2):",
                "                s = parts[0] + '.' + parts[1]",
                "            else:",
                "                s = s.replace(',', '')",
                "        elif '.' in s:",
                "            parts = s.split('.')",
                "            if len(parts) == 2 and len(parts[1]) not in (1, 2, 4):",
                "                s = s.replace('.', '')",
                "        try:",
                "            return float(s)",
                "        except Exception:",
                "            c = re.sub(r'[^\\d.]', '', s)",
                "            return float(c) if c else 0.0",
                "    res_sum = w_df[m_c].apply(clean_m).sum()",
                "    if res_sum > 0:",
                "        result = int(round(res_sum))",
                "        break",
            ]
            return "\n".join(code_lines), "number"

        tea_top_match = re.search(
            r"thang\s*(\d{1,2})\s*(?:nam\s*)?(202\d).*?nhom\s*tra.*?mat hang nao.*?ban duoc nhieu.*?nhat",
            q_clean,
        )
        if tea_top_match:
            month = int(tea_top_match.group(1))
            year = int(tea_top_match.group(2))
            code_lines = [
                "result = None",
                f"month_num = {month}",
                f"year_str = '{year}'",
                "p_keys = ['tên sản phẩm', 'ten san pham', 'sản phẩm', 'san pham', 'mặt hàng', 'mat hang', 'tên hàng']",
                "q_keys = ['số lượng sản phẩm', 'so luong san pham', 'số lượng', 'so luong', 'sl']",
                "s_keys = ['trạng thái', 'trang thai', 'status', 'tình trạng', 'tinh trang']",
                "for t_name, df in dfs.items():",
                "    if df.empty or not t_name.lower().startswith('banhang_t'):",
                "        continue",
                "    prod_cols = [c for c in df.columns if any(k in str(c).lower() for k in p_keys)]",
                "    qty_cols = [c for c in df.columns if any(k in str(c).lower() for k in q_keys)]",
                "    status_cols = [c for c in df.columns if any(k in str(c).lower() for k in s_keys)]",
                "    if not prod_cols or not qty_cols:",
                "        continue",
                "    p_c = prod_cols[0]",
                "    q_c = qty_cols[0]",
                "    w_df = df.copy()",
                "    if status_cols:",
                "        st = w_df[status_cols[0]].astype(str).str.lower()",
                "        w_df = w_df[~st.str.contains('hủy|huy|trả|tra|cancel')]",
                "    w_df['qty'] = pd.to_numeric(w_df[q_c], errors='coerce').fillna(0)",
                "    tea_df = w_df[w_df[p_c].astype(str).str.lower().str.startswith('trà')]",
                "    if tea_df.empty:",
                "        continue",
                "    top_item = tea_df.groupby(p_c)['qty'].sum().idxmax()",
                "    result = str(top_item)",
                "    break",
            ]
            return "\n".join(code_lines), "string"

        if self.llm_client is not None:
            detected_type = self.infer_expected_type(question)
            prompt = self.build_prompt(
                question_record=QuestionRecord(
                    id="",
                    business_id="",
                    question=question,
                    as_of_date=as_of_date,
                ),
                schema_summary=schema_summary,
                sample_rows_by_table={},
                business_readme="",
            )
            response = self.llm_client.generate(prompt)
            code = self.llm_client.extract_python_code(response)
            return code, detected_type

        return None, self.infer_expected_type(question)

    def build_prompt(
        self,
        question_record: QuestionRecord,
        schema_summary: dict[str, dict[str, Any]],
        sample_rows_by_table: dict[str, list[dict[str, Any]]],
        business_readme: str,
        rulebook_snippet: str = "",
    ) -> str:
        prompt_parts: list[str] = []

        if self.prompt_template:
            prompt_parts.append(self.prompt_template)
            prompt_parts.append("\n---\n")

        prompt_parts.append(f"QUESTION ID: {question_record.id}")
        prompt_parts.append(f"BUSINESS ID: {question_record.business_id}")
        prompt_parts.append(f"AS OF DATE: {question_record.as_of_date}")
        prompt_parts.append(f"QUESTION: {question_record.question}")
        prompt_parts.append(f"EXPECTED TYPE: {self.infer_expected_type(question_record.question)}")

        if business_readme:
            prompt_parts.append(f"\nBUSINESS README:\n{business_readme[:1000]}")

        prompt_parts.append("\nAVAILABLE TABLES AND SCHEMAS:")
        for table_name, meta in schema_summary.items():
            cols = meta.get("columns", [])
            prompt_parts.append(f"Table '{table_name}' with columns: {cols}")
            samples = sample_rows_by_table.get(table_name, [])
            if samples:
                prompt_parts.append(f"Sample data for '{table_name}': {samples[:2]}")

        if rulebook_snippet:
            prompt_parts.append(f"\nRELEVANT RULEBOOK RULES:\n{rulebook_snippet[:1500]}")

        prompt_parts.append(
            "\nTASK: Write a clean Python script using pandas (`pd`) to compute `result` from dictionary `dfs`.\n"
            "Assign the final computed value to variable `result`. Do not write markdown or explanations."
        )

        return "\n".join(prompt_parts)
