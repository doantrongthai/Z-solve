# Báo cáo Nghiên cứu Chuyên sâu Track 1: LifeMate (Zalo AI Challenge 2026)

---

## 1. Tổng quan bài toán LifeMate

**LifeMate – Agentic AI That Turns Your Voice Into Action** là bảng thi xây dựng **AI Agent điều khiển bằng giọng nói tiếng Việt**, có khả năng nghe các yêu cầu ngôn ngữ tự nhiên từ người dùng và tự động thực thi các hành động đa bước (multi-step action chaining) trên một môi trường ứng dụng mô phỏng (`ToolEnv`).

### Luồng dữ liệu vào & ra (I/O Specification):
* **Đầu vào (Input):**
  1. **Audio file (`.wav`):** Giọng nói tiếng Việt (3 miền Bắc - Trung - Nam, có thể lẫn từ mượn tiếng Anh).
  2. **Bối cảnh người dùng (`context`):**
     * `current_time`, `timezone`: Mốc thời gian để suy luận các từ ngữ tương đối ("mai", "tối nay", "thứ hai tuần tới").
     * `location` (`lat`, `lng`): Vị trí địa lý hiện tại.
     * `user_profile`: Tên, địa chỉ nhà (`home_address`), nơi làm việc (`work_address`).
     * `installed_apps`: Danh mục các ứng dụng đang cài và danh sách công cụ được phép gọi.
  3. **Lịch sử hội thoại (`history`):** Các lượt thoại trước đó giữa người dùng và trợ lý ảo (nếu có).
  4. **Môi trường ứng dụng (`ToolEnv`):** Trạng thái hiện tại của thiết bị, danh bạ, tài khoản, lịch, nhắc việc (`state.json`).
* **Đầu ra (Output):**
  * Danh sách chuỗi gọi công cụ có thứ tự (`tool_calls` gồm `name` và `arguments`).
  * Mã băm trạng thái cuối cùng của môi trường: `state_hash = env.get_state_hash()`.
  * Dòng ghi nộp bài trong `submission.jsonl`:
    ```json
    {"id": "public_0039", "tool_calls": [{"name": "alarm.list", "arguments": {}}, {"name": "alarm.create", "arguments": {"time": "2026-11-11T05:30:00+07:00"}}], "state_hash": "461fcd40625c9968434b56ee113c0953f332f0c1189a3d385575e1dabec263f3"}
    ```

---

## 2. Các quy định và ràng buộc kỹ thuật (Rules & Constraints)

1. **Giới hạn tham số model:** Tổng toàn bộ hệ thống (**ASR + LLM + Embedding/Reranker**) phải **$\le$ 6 tỷ tham số (6B)**. Riêng **LLM phải < 5B tham số** và context length tối đa $\le 16.384$ tokens.
2. **Chạy hoàn toàn Offline:** Không gọi API bên ngoài ở pha inference. Toàn bộ weights và code đóng gói trong Docker.
3. **Thời gian chạy:** Tối đa **30 giây / mẫu**. Chạy quá thời gian hoặc lỗi execution nhận **0 điểm**.
4. **Tính toàn vẹn của ToolEnv (Zero Cheating):**
   - Tuyệt đối không đọc trực tiếp file `state.json`.
   - Mỗi mẫu chỉ được khởi tạo **đúng một phiên `ToolEnv` duy nhất**; mọi call (kể cả call bị lỗi schema) đều được ghi nhận vào `env.get_tool_calls()`. Không được tạo lại `ToolEnv` để thử rồi chạy lại.
5. **Công thức tính điểm (Evaluation Metric):**
   - **State Match (Điều kiện tiên quyết):** `submitted_state_hash == gold_state_hash`. Nếu sai hash $\implies$ **0 điểm ngay lập tức**.
   - **Tool Calls $F_1$ Score:** Nếu state khớp, điểm được tính bằng $F_1$ giữa chuỗi tool call dự đoán và gold tool call:
     $$P = \frac{M}{|T|}, \quad R = \frac{M}{|G|}, \quad F_1 = \frac{2PR}{P + R}$$
     *(Trong đó $M$ là số call khớp cả tên và tham số, $U$ là call thừa/sai sẽ làm giảm $P$)*.

---

## 3. Khảo sát & Phân tích Bộ Dữ liệu Thực tế (`isolated_track1`)

Chúng tôi đã tiến hành phân tích toàn diện 1.545 mẫu trong tập `train.jsonl` và 634 mẫu trong `public_test.jsonl`:

### Thống kê tập `train.jsonl` (1.545 mẫu):
* **Số mẫu không gọi tool nào (Out-of-scope):** **111 mẫu (7.2%)**
  * *Hành vi:* Yêu cầu nằm ngoài khả năng của các app đã cài hoặc câu nói bông đùa. Agent phải trả về `tool_calls: []` và giữ nguyên initial `state_hash`.
* **Số mẫu gọi `sys.ask_missing_info`:** **217 mẫu (14.0%)**
  * *Hành vi:* Khi người dùng đưa ra yêu cầu thiếu tham số bắt buộc không thể tự suy diễn (ví dụ: muốn thêm nhạc vào playlist nhưng không nói playlist nào hay bài nào).
* **Số bước gọi tool trung bình:** **2.29 bước / mẫu**.
* **Số bước gọi tool tối đa:** **6 bước / mẫu**.

### Phân bố các công cụ phổ biến nhất:
| Thứ hạng | Tên Tool | Tần suất xuất hiện | Nhóm chức năng |
|:---:|---|:---:|---|
| 1 | `contacts.search` | 234 | Tra cứu danh bạ (lấy `contact_id`, số điện thoại) |
| 2 | `sys.ask_missing_info` | 217 | Yêu cầu người dùng bổ sung thông tin thiếu |
| 3 | `smart_home.light_set` | 126 | Điều khiển đèn thông minh |
| 4 | `reminders.create` | 115 | Tạo lời nhắc |
| 5 | `bill_payment.list_bills` | 112 | Liệt kê hoá đơn cần thanh toán |
| 6 | `smart_home.get_status` | 107 | Đọc trạng thái thiết bị trong nhà |
| 7 | `calendar.list_events` | 105 | Kiểm tra lịch biểu hiện có |
| 8 | `bill_payment.pay` | 104 | Thanh toán tiền điện/nước/internet |
| 9 | `chat_ott.list_chats` | 94 | Đọc danh sách chat |
| 10 | `banking.transfer` | 82 | Chuyển khoản ngân hàng |

---

## 4. Khảo sát mã nguồn cộng đồng & Hệ thống tương tự trên GitHub

1. **Về các repo Zalo AI Challenge 2026 LifeMate:**
   * Cuộc thi mới mở ngày 26/10/2026, nên chưa có giải pháp mã nguồn mở công khai trực tiếp gắn nhãn LifeMate trên GitHub (các đội đang bảo mật mã nguồn trong thời gian thi đấu).
2. **Các kiến trúc tham khảo hàng đầu cho bài toán này:**
   * **ReAct / Function Calling Agents:** Framework lặp tương tác (Thought $\to$ Action $\to$ Observation $\to$ Thought $\to$ Action).
   * **ToolBench / Gorilla OpenFunctions:** Phương pháp format schema dưới dạng OpenAI Function Calling chuẩn hóa.
   * **PhoWhisper / Whisper ASR:** Giải pháp chuyển đổi âm thanh tiếng Việt đạt WER thấp nhất hiện nay.

---

## 5. Thiết kế Kiến trúc Tối ưu cho LifeMate Agent

### Các thành phần chính của Pipeline:

1. **Bộ chuyển đổi giọng nói (ASR Engine):**
   * **Lựa chọn:** `vinai/PhoWhisper-small` (240 triệu tham số) hoặc `openai/whisper-small` (244 triệu tham số).
   * *Ưu điểm:* Xử lý tốt phương ngữ Bắc - Trung - Nam, kích thước siêu nhẹ (~500MB weights), tốc độ giải mã $< 0.3$ giây/audio.

2. **Mô hình ngôn ngữ tư duy (LLM Engine):**
   * **Lựa chọn hàng đầu:** **`Qwen/Qwen2.5-3B-Instruct`** (hoặc `Qwen2.5-Coder-3B-Instruct` - 3.09 tỷ tham số).
   * *Tại sao chọn model này?*
     * Đáp ứng hoàn hảo luật: $3.09\text{B} + 0.24\text{B} = 3.33\text{B} \le 6\text{B}$ tổng toàn hệ thống (LLM $< 5\text{B}$).
     * Hỗ trợ cấu trúc Function Calling / Tool Calling cực mạnh.
     * Hiểu ngữ cảnh tiếng Việt và suy luận logic phân nhánh (`Nếu... thì...`) xuất sắc trong phân khúc $\le 3\text{B}$.

3. **Vòng lặp ReAct tương tác với `ToolEnv`:**
   * **Bước 1 (Lọc Tool):** Chỉ đưa các tool có trong `context["installed_apps"]` vào prompt của mẫu đó.
   * **Bước 2 (Multi-step Chaining):**
     * Ví dụ với câu "Kiểm tra xem mai có mưa không, nếu mưa thì dời lịch chạy bộ":
       - Lần 1: Gọi `weather.get_forecast` $\to$ Nhận kết quả mưa.
       - Lần 2: Gọi `calendar.list_events` $\to$ Tìm thấy `evt_01` chạy bộ.
       - Lần 3: Gọi `calendar.update_event` $\to$ Cập nhật giờ chạy bộ mới.
     * Mỗi kết quả trả về từ `env.call()` được nối vào context để LLM quyết định bước tiếp theo.
   * **Bước 3 (Dừng & Trích xuất):**
     * Khi LLM hoàn tất nhiệm vụ, trích xuất `env.get_tool_calls()` và `env.get_state_hash()`.
