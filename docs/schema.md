# Tài liệu Đặc tả Dữ liệu và Schema — DataMate (Zalo AI Challenge 2026)

## 1. Cấu trúc file câu hỏi (`questions.jsonl`)

Tập câu hỏi được lưu dưới định dạng **UTF-8 JSON Lines (`.jsonl`)**, mỗi dòng là một đối tượng JSON hợp lệ gồm 4 trường bắt buộc:

| Tên trường | Kiểu dữ liệu | Ý nghĩa & Quy ước | Ví dụ |
| :--- | :--- | :--- | :--- |
| `id` | `string` | Mã định danh duy nhất của câu hỏi (bắt đầu bằng tiền tố `q_`). | `"q_06de33fa21cc"` |
| `business_id` | `string` | Mã định danh doanh nghiệp tương ứng (tên thư mục con trong `data/`). | `"biz_118"` (train) hoặc `"dev_002"` (test) |
| `question` | `string` | Câu hỏi tự nhiên bằng tiếng Việt đời thường (có từ viết tắt, tiếng lóng, từ địa phương). | `"sp bán dc nhiều nhất tuần rồi là gì"` |
| `as_of_date` | `string` | Ngày mốc ("hôm nay") theo chuẩn ISO `YYYY-MM-DD`. | `"2026-03-04"` |

### Trích dẫn nguyên văn từ tài liệu gốc (Bằng chứng):
> **Description (Portal & all_challenge_details.json):**
> *"Input — one line of questions.jsonl:*
> `{"id": "q_06de33fa21cc", "business_id": "biz_118", "question": "sp bán dc nhiều nhất tuần rồi là gì", "as_of_date": "2026-03-04"}`*
> *"- An as-of date : the “today” against which relative time expressions (“tháng này”, “tuần rồi”, “cùng kỳ năm ngoái”) are resolved."*
>
> **Rulebook (Mục 1 & 2):**
> *"**Hôm nay** của mỗi câu là trường `as_of_date` trong `questions.jsonl`. Mọi cách nói tương đối tính theo ngày này. File có thể có bản ghi ngày sau hôm nay: với câu hỏi theo hôm nay, những bản ghi đó coi như chưa xảy ra."*

---

## 2. Cấu trúc dữ liệu doanh nghiệp (`data/<business_id>/`)

Mỗi doanh nghiệp sở hữu một kho dữ liệu thực tế gồm các định dạng `.xlsx`, `.csv`, `.sqlite` cùng một tệp `README.md` mô tả nghiệp vụ.

### 2.1. Các đặc điểm thách thức của dữ liệu bảng tính
1. **Tên file & sheet có dấu tiếng Việt và khoảng trắng**:
   - Tên file: `Danh sách hàng hóa.xlsx`, `So_chi_tiet_ban_hang.xlsx`, `BanHang_T10_2025.xlsx`, `Báo cáo ca.xlsx`.
   - Sheet names: Thường chia theo tháng hoặc quý, ví dụ `T1_2025`, `Sheet1`, `ChiTiet`.
2. **Cột tiếng Việt & Header lệch**:
   - Tên cột tiếng Việt có dấu, viết hoa thường không nhất quán: `Mã hàng`, `Tên hàng hóa`, `ĐVT`, `Số lượng`, `Đơn giá`, `Thành tiền`, `Giảm giá`, `Trạng thái đơn`, `Ghi chú`.
   - Một số sheet có header không nằm ở dòng đầu tiên (dòng 0) mà bắt đầu từ dòng 2 hoặc 3 (phía trên là tiêu đề báo cáo công ty).
3. **Ô trống do gom nhóm (Merged Cells / Forward Fill)**:
   - Khi một đơn hàng có nhiều dòng mặt hàng, các dòng sau thường để trống mã đơn, mã khách, ngày đặt, trạng thái đơn.
   > **Trích dẫn nguyên văn Rulebook (Mục 8):**
   > *"Ô để trống ở các dòng sau của cùng một nhóm dòng: giống ô đó ở dòng đầu nhóm: khách, ghi chú, trạng thái của đơn áp cho mọi dòng của đơn. Không phải thiếu dữ liệu, không có nghĩa là khách lẻ hay đơn hoàn thành."*
4. **Trạng thái đơn hàng và Sổ không có cột trạng thái**:
   > **Trích dẫn nguyên văn Rulebook (Mục 8):**
   > *"Trạng thái đơn: mỗi đơn có đúng một trong bốn trạng thái: **hoàn thành**, **huỷ**, **trả hàng**, **đang giao**."*
   > *"Sổ không có cột trạng thái: trạng thái đơn ghi ở cột Ghi chú. Ghi chú không nhắc trạng thái là đơn hoàn thành."*
5. **Dòng trùng lặp do lỗi xuất file**:
   > **Trích dẫn nguyên văn Rulebook (Mục 8):**
   > *"Hai dòng của **cùng một đơn** giống nhau ở mọi ô: lỗi xuất file, tính một lần. Hai dòng giống nhau của hai đơn khác nhau là hai lần bán, tính cả hai."*
6. **Lịch Âm – Dương (`calendar.csv`)**:
   - Cột: `date, weekday, lunar_day, lunar_month, lunar_year, lunar_leap, holiday`.
   > **Trích dẫn nguyên văn Rulebook (Mục 2):**
   > *"Tết năm Y, dịp Tết, mùa Tết: từ ngày dương của **23 tháng Chạp** (năm âm Y − 1) đến **hết** ngày dương của **mùng 10 tháng Giêng** (năm âm Y). So với trước Tết = cùng số ngày ngay trước 23 tháng Chạp. Tra lịch âm trong `calendar.csv` cùng thư mục."*

---

## 3. Các kiểu đáp án và quy tắc định dạng (`type` & `answer`)

Mỗi dòng kết quả có cấu trúc: `{"id": "...", "type": "...", "answer": ...}`.

### 3.1. Bảng quy cách định dạng từng kiểu

| `type` | Định dạng (`format`) | Quy tắc chuẩn hóa & Làm tròn | Ví dụ hợp lệ | Ví dụ SAI (bị -1 điểm) |
| :--- | :--- | :--- | :--- | :--- |
| `number` | JSON number (integer hoặc float). | Tiền VND là số nguyên, làm tròn về đồng. Số lượng/khác làm tròn tối đa 2 chữ số thập phân. Không kèm ký hiệu đơn vị, không dấu phân cách nghìn. | `4820000`, `18.6` | `"4.820.000"`, `"4820K"`, `"4820000đ"` |
| `percent` | JSON number biểu diễn số phần trăm. | Làm tròn đúng 2 chữ số thập phân; giữ đúng dấu âm/dương. Không kèm ký hiệu `%`. | `12.4`, `-5.27` | `"12.4%"`, `0.124` |
| `string` | Chuỗi văn bản tiếng Việt Unicode NFC. | Lấy đúng tên trong dữ liệu (sản phẩm, khách hàng, chi nhánh, biển số...). Không phân biệt hoa/thường, khoảng trắng thừa. | `"Sting dâu 330ml"` | `"Sting dầu 330ml"` (sai dấu) |
| `date` | Chuỗi ngày ISO. | Ngày: `"YYYY-MM-DD"`. Nếu câu hỏi theo tháng: `"YYYY-MM"`. | `"2026-08-15"`, `"2025-09"` | `"15/08/2026"`, `"tháng 9/2025"` |
| `boolean` | Giá trị boolean JSON. | `true` hoặc `false` (chữ thường, boolean type). | `true`, `false` | `"true"`, `"có"`, `1` |
| `list` | Mảng JSON có thứ tự `[...]`. | Xếp hạng giảm dần theo tiêu chí câu hỏi; nếu hòa xếp theo mã tăng dần. Một phần tử vẫn là mảng. | `["Cà phê sữa", "Bạc xỉu"]`, `[3, 10]` | `"Cà phê sữa, Bạc xỉu"`, `3` |
| `table` | Đối tượng JSON bảng 2 chiều. | `{"columns": [...], "rows": [[...], ...]}`. Cột đầu là tên đối tượng, các cột sau là số đo. Ô số là JSON number. | `{"columns": ["khach_hang", "so_tien_no"], "rows": [["Chị Lan", 3200000]]}` | Có ô ghi chuỗi tiền `"3.200.000đ"` |
| `unanswerable` | `{"type": "unanswerable", "answer": null}` | Khi dữ liệu không đủ căn cứ để kết luận (kỳ nằm ngoài dữ liệu, file thiếu loại thông tin cần). | `{"type": "unanswerable", "answer": null}` | Trả về `0` hoặc đoán mò |
| `abstain` | `{"type": "abstain"}` | Khi hệ thống không chắc chắn hoặc gặp lỗi runtime để bảo toàn điểm (nhận 0 thay vì -1). Theo Portal Submission Guidance: `{"id": "...", "type": "abstain"}`. | `{"id": "q_01242", "type": "abstain"}` |

### Trích dẫn nguyên văn Rulebook (Mục 9 & Evaluation):
> *"Mỗi dòng submission.jsonl: `{"id": "...", "type": "...", "answer": ...}`. Đúng +1, sai −1, bỏ trống (`{"type": "abstain"}` hoặc không có dòng) 0."*
> *"Mỗi type có một format duy nhất; sai format là sai. Đáp án chỉ ghi giá trị: số không kèm chữ đơn vị hay ký hiệu %; tên lấy nguyên từ dữ liệu, không kèm tên cột hay nhãn nhóm. Câu hỏi nhiều số thì ghi list theo đúng thứ tự câu hỏi nêu."*
> *"Đúng format rồi mới so giá trị:*
> *- **Số, phần trăm**: khớp tuyệt đối. Tiền đúng từng đồng, số đếm đúng từng đơn vị, phần trăm đúng 2 chữ số thập phân. Chỉ bỏ qua sai số dấu phẩy động.*
> *- **Làm tròn**: tiền ra số lẻ làm tròn về đồng; trung bình của một khoản tiền cũng là tiền, làm tròn về đồng. Phần trăm và số trung bình khác làm tròn 2 chữ số thập phân, trừ khi một luật khác trong rulebook ghi khác.*
> *- **Chuỗi**: không phân biệt hoa thường, khoảng trắng, dấu câu. Nhận mọi cách viết tên có trong file của shop, hoặc mã.*
> *- **Danh sách**: đúng cả tập và thứ tự. Top k xếp theo tiêu chí câu hỏi, giảm dần. Cùng số đo thì theo mã tăng dần.*
> *- **Bảng**: mỗi dòng một đối tượng; cột đầu là tên đối tượng, các cột sau là số đo theo đúng thứ tự câu hỏi nêu."*

---

## 4. Định dạng file nộp bài (`submission.jsonl`)

1. **Tên file & Đường dẫn**:
   - Vòng Public Test: `submission.jsonl` (hoặc cấu hình tại `results/submission.jsonl`).
   - Môi trường Docker chấm tự động: `/result/submission.jsonl`.
   > **Trích dẫn nguyên văn Rules (Mục 2 & 7):**
   > *"For scoring, the organizers mount the test set into the container at `/data` and collect `/result/submission.jsonl`."*
2. **Encoding**:
   - Bắt buộc chuẩn **UTF-8** (không kèm BOM).
3. **Cấu trúc từng dòng**:
   - Mỗi dòng tương ứng chính xác với 1 câu hỏi trong `questions.jsonl`.
   - Khóa bắt buộc: `"id"`, `"type"`, `"answer"`.
4. **Thứ tự & Xử lý ID**:
   - Phải có đủ $100\%$ các `id` xuất hiện trong file câu hỏi.
   - Không được trùng lặp ID, không được thừa ID không tồn tại.
   - Các ID không giải được hoặc cố ý bỏ qua xuất dạng chuẩn của portal: `{"id": "...", "type": "abstain"}` (hoặc kèm `answer: null`).

