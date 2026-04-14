# Phân tích Retrieval Worker (Sprint 3) — Nguyễn Quốc Khánh

## 1. Mục tiêu phân tích
- Đánh giá khả năng tìm kiếm (retrieval) khi chạy trong hệ thống Multi-Agent (Graph).
- Kiểm tra hiệu quả của việc tăng `top_k` đối với các câu hỏi phức tạp (multi-hop).
- Xác minh tính ổn định của worker khi được gọi gián tiếp qua MCP trong `policy_tool_worker`.

## 2. Kết quả Tuning & Debugging

### Lỗi đã fix:
- **Crashes in Synthesis**: Phát hiện lỗi `NoneType` khi `policy_result` không được khởi tạo ở nhánh `retrieval_worker`. 
  - *Giải pháp:* Khởi tạo mặc định `policy_result: {}` trong `graph.py`.
- **JSON Decode Error**: Script `eval_trace.py` bị crash khi gặp file trace trống.
  - *Giải pháp:* Thêm cơ chế skip file trống và handle exception trong `analyze_traces`.

### Tối ưu hóa (Tuning):
- **Tăng `top_k` từ 3 lên 5**: Phân tích ban đầu cho thấy `top_k=3` không đủ để bao phủ cả hai tài liệu `access_control_sop.txt` và `sla_p1_2026.txt` cho các câu hỏi multi-hop. Kết quả sau khi tăng lên 5 đã cải thiện rõ rệt độ phủ (recall).

## 3. Phân tích các Case Study tiêu biểu

### Case 1: Câu hỏi SLA P1 (q01)
- **Câu hỏi**: "SLA xử lý ticket P1 là bao lâu?"
- **Kết quả**: Route đúng vào `retrieval_worker`.
- **Phân tích**: Lấy được 3 chunks từ `sla_p1_2026.txt`. Confidence đạt 0.50 sau khi fix bug crash. Câu trả lời chính xác, cite đúng nguồn.

### Case 2: Multi-hop Access & SLA (q15)
- **Câu hỏi**: "Ticket P1 lúc 2am. Cần cấp Level 2 access tạm thời... Nêu đủ cả hai quy trình."
- **Kết quả**: Route vào `policy_tool_worker` → gọi MCP `search_kb`.
- **Phân tích**: Nhờ `top_k=5`, hệ thống đã lấy được:
    - 03 chunks từ `access_control_sop.txt` (quy trình cấp quyền khẩn cấp).
    - 02 chunks từ `sla_p1_2026.txt` (quy trình thông báo SLA).
- **Kết luận**: Retrieval hoạt động xuất sắc trong mô hình Multi-Agent, cung cấp đủ bằng chứng từ 2 file khác nhau để Synthesis tổng hợp.

## 4. Số liệu tổng kết (chuẩn bị cho Sprint 4)
- **Độ phủ nguồn tin (Source Coverage)**:
    - `sla_p1_2026.txt`: Xuất hiện trong 45% các câu hỏi.
    - `access_control_sop.txt`: Xuất hiện trong 30% các câu hỏi.
- **Latency trung bình**: ~2500ms (tăng nhẹ do logic LLM Synthesis nhưng trong ngưỡng chấp nhận được).
- **Độ tin cậy (Confidence)**: Trung bình đạt 0.55 - 0.65 cho các câu thành công.

## 5. Kết luận Sprint 3
Worker Retrieval đã được tích hợp hoàn toàn và hoạt động ổn định trong Graph. Các lỗi tích hợp đã được xử lý triệt để. Hệ thống đủ điều kiện để bước sang Sprint 4 (Grading & Final Reporting).
