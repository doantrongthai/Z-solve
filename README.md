# Zalo AI Challenge 2026 — Track 2: DataMate Agent (`Z-solve`)

Hệ thống Agent hỏi đáp dữ liệu doanh nghiệp tự động cho cuộc thi Zalo AI Challenge 2026 (Bảng DataMate). Hệ thống đọc dữ liệu đa định dạng (CSV, XLSX, SQLite), tiếp nhận câu hỏi tự nhiên bằng tiếng Việt kèm mốc thời gian `as_of_date`, sinh mã Python/Pandas thực thi trong sandbox cách ly, chuẩn hóa đáp án và áp dụng chính sách Abstain để tối đa hóa chỉ số Penalized Accuracy.

---

## 1. Cấu trúc thư mục

```text
Z-solve/
├── colab_inference.ipynb          # Notebook Google Colab sẵn sàng chạy GPU T4
├── notebooks/
│   └── datamate_colab_inference.ipynb
├── src/
│   └── datamate/
│       ├── __init__.py
│       ├── abstain.py             # Chính sách từ chối trả lời (Abstain)
│       ├── config.py              # Cấu hình pipeline, model, timeout
│       ├── executor.py            # Thực thi code trong sandbox có timeout
│       ├── formatter.py           # Chuẩn hóa đáp án (number, percent, date, list...)
│       ├── ingest.py              # Đọc CSV, XLSX, SQLite của các doanh nghiệp
│       ├── llm.py                 # LLM Client hỗ trợ 4-bit/8-bit trên GPU T4 (Qwen2.5-Coder)
│       ├── models.py              # Data structures (Question, Submission, GT)
│       ├── pipeline.py            # Quản lý luồng thực thi toàn bộ câu hỏi
│       ├── planner.py             # Lập kế hoạch, sinh prompt và sinh mã tính toán
│       └── sandbox.py             # AST validation và môi trường chạy an toàn
├── scripts/
│   ├── run_inference.py           # Script chạy inference chính
│   ├── run_pipeline.py            # Pipeline runner có CLI linh hoạt
│   └── validate_submission.py     # Validator kiểm tra định dạng nộp bài theo luật BTC
├── prompts/
│   └── system_prompt_v1.txt       # Prompt hệ thống tuân thủ rulebook.md
├── docs/
│   └── schema.md                  # Tài liệu đặc tả schema và định dạng
├── tests/                         # Bộ kiểm thử pytest
├── Dockerfile                     # Dockerfile đóng gói nộp bài chung kết
├── requirements.txt               # Danh sách thư viện phụ thuộc
└── pyproject.toml                 # Cấu hình dự án & ruff linter
```

---

## 2. Hướng dẫn chạy trên Google Colab (GPU T4)

### Trình tự 1-Click trên Google Colab:

1. **Kiểm tra GPU:**
   ```bash
   !nvidia-smi
   ```

2. **Clone repository và cài đặt thư viện:**
   ```bash
   !git clone https://github.com/doantrongthai/Z-solve.git
   %cd Z-solve
   !pip install -r requirements.txt -q
   ```

3. **Tải dữ liệu tự động từ Hugging Face:**
   ```bash
   !wget -q --show-progress https://huggingface.co/datasets/doantrongthai/ZAIC/resolve/main/datamate.zip
   !mkdir -p datamate
   !unzip -q -o datamate.zip -d datamate
   ```

4. **Chạy Inference với LLM (chế độ 4-bit tối ưu cho GPU T4):**
   ```bash
   !python scripts/run_inference.py \
       --split public_test \
       --model Qwen/Qwen2.5-Coder-7B-Instruct \
       --load-in-4bit \
       --enable-llm \
       --output results/submission.jsonl
   ```

5. **Kiểm tra tính hợp lệ của file kết quả:**
   ```bash
   !python scripts/validate_submission.py \
       --submission results/submission.jsonl \
       --questions datamate/public_test/public_test/questions.jsonl
   ```

6. **Tải file kết quả về máy để nộp:**
   ```python
   from google.colab import files
   files.download('results/submission.jsonl')
   ```

---

## 3. Chạy kiểm thử cục bộ (Local)

1. **Cài đặt môi trường:**
   ```bash
   pip install -e .
   ```

2. **Kiểm tra code style và unit tests:**
   ```bash
   ruff check src scripts tests
   pytest tests
   ```

---

## 4. Luật chấm điểm Penalized Accuracy

$$\text{PA} = \frac{\text{Correct} - \text{Wrong}}{\text{Total}}$$

- **Đúng (+1):** Giá trị và định dạng khớp tuyệt đối với ground truth.
- **Abstain (0):** Không trả lời hoặc nộp `{"type": "abstain"}` khi dữ liệu không đủ căn cứ.
- **Sai (-1):** Sai giá trị hoặc sai định dạng.
