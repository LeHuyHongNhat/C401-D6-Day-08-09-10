# Báo Cáo Cá Nhân — Lab Day 09: Multi-Agent Orchestration

**Họ và tên:** Nguyễn Quốc Khánh  
**Vai trò trong nhóm:** Worker Owner (Retrieval) & Integration Tech Lead  
**Ngày nộp:** 14/04/2026  

---

## 1. Trách nhiệm và Vai trò trong dự án

Trong dự án Multi-Agent Orchestration thuộc Lab Day 09, tôi đảm nhận trách nhiệm chính là **thiết kế Retrieval Worker** và **tối ưu hóa luồng dữ liệu** của toàn bộ Graph (LangGraph). Công việc của tôi không chỉ dừng lại ở việc truy xuất văn bản mà còn là đảm bảo dữ liệu đầu vào cho các Worker khác luôn đạt độ chính xác và tính toàn vẹn cao nhất thông qua các kỹ thuật xử lý văn bản chuyên sâu.

---

## 2. Quyết định kỹ thuật: Regex-based Semantic Splitting

Một trong những đóng góp kỹ thuật quan trọng nhất tôi đã thực hiện là chuyển đổi từ phương pháp cắt văn bản theo độ dài ký tự (Character Splitting) sang **Semantic Splitting dựa trên Regex**.

**Lý do:** Các tài liệu quy chuẩn nội bộ (SLA, SOP) thường được trình bày theo cấu trúc phân cấp chặt chẽ (Phần 1, Điều 2...). Nếu sử dụng các bộ tách văn bản thông thường, một quy định quan trọng có thể bị cắt làm đôi ở hai chunks khác nhau. Điều này buộc LLM phải suy luận từ các mảnh thông tin rời rạc, dẫn đến nguy cơ "hallucination" cao. Tôi đã viết logic nhận diện Header `=== ... ===` để đảm bảo mỗi chunk là một khối quy tắc hoàn chỉnh.

---

## 3. Khắc phục lỗi MCP Integration & Traceability

Trong giai đoạn tích hợp cuối cùng, tôi đã trực tiếp xử lý các lỗi xung đột hệ thống phát sinh sau khi merge code từ nhóm. Cụ thể, tôi đã refactor lại module `policy_tool.py` để tương thích với kiến trúc Class-based MCP của nhóm, đồng thời chuẩn hóa lại toàn bộ `AgentState` trong `graph.py`. Việc này đảm bảo các báo cáo Trace luôn hiển thị đầy đủ `workers_called` và `sources`, đáp ứng 100% tiêu chí quan sát (Observability) của dự án.

---

## 4. Phân tích trọng tâm từ Trace: gq01 & gq05 (SLA P1)

Đây là hai câu hỏi quan trọng minh chứng cho hiệu quả của hệ thống Retrieval và kỹ thuật Chunking mà tôi đã áp dụng:

**Câu gq01: "Ticket P1 được tạo lúc 22:47. Ai nhận thông báo đầu tiên và deadline escalation là mấy giờ?"**
- **Trace Analysis:** Supervisor route chính xác vào `retrieval_worker`. Hệ thống truy xuất file `sla_p1_2026.txt`.
- **Ảnh hưởng của Chunking:** Câu hỏi này yêu cầu 3 lớp thông tin: Đối tượng nhận (On-call engineer), Kênh (Slack/Email) và Deadline (22:57). Nhờ Semantic Splitting, toàn bộ "Quy trình xử lý sự cố P1" được giữ trong cùng một đoạn văn bản. Nếu dùng phương pháp cũ, thông báo (Section 1) và quy tắc escalation (Section 2) có thể bị tách rời, khiến Agent gặp khó khăn khi tính toán deadline 10 phút. Kết quả cho thấy `confidence` đạt **0.59**, minh chứng cho độ chính xác của ngữ cảnh.

**Câu gq05: "Ticket P1 không phản hồi sau 10 phút, hệ thống làm gì tiếp theo?"**
- **Trace Analysis:** Tiếp tục là một query thành công của Retrieval Worker với `confidence` đạt **0.65**.
- **Ảnh hưởng của Chunking:** Kỹ thuật tách theo Section giúp chunk trả về chứa trọn vẹn quy tắc: "Nếu không phản hồi trong 10 phút -> Escalate lên Senior Engineer". Việc cung cấp một "khối quy tắc" thay vì "dòng văn bản rời rạc" giúp LLM không chỉ trả lời đúng hành động mà còn hiểu được bối cảnh đảm bảo tính kịp thời của SLA.

---

## 5. So sánh kiến trúc và Tự đánh giá

**So sánh Day 08 và Day 09:**
Kiến trúc Multi-Agent (Day 09) cho phép Retrieval Worker hoạt động như một "chuyên gia dữ liệu" độc lập. Sự phân tách này giúp tôi tập trung tối ưu hóa chất lượng văn bản trả về (Retrieval Quality) mà không làm ảnh hưởng đến logic phân tích của các Worker khác. Đây là điểm tiến bộ vượt bậc so với kiến trúc Single-Agent ở Day 08, nơi LLM thường bị quá tải với Token Context quá lớn.

**Tự đánh giá:**
Tôi đã hoàn thành xuất sắc việc xây dựng cửa ngõ dữ liệu cho toàn hệ thống. Tuy nhiên, tôi nhận thấy Latency của hệ thống vẫn còn dư địa để tối ưu thêm khoảng 20-30% nếu triển khai Parallel Tool Calling trong các Worker.

---

## 6. Kết luận

Dự án Day 09 đã giúp tôi khẳng định giá trị của việc xử lý dữ liệu tầng thấp (preprocessing) đối với hiệu năng của toàn bộ hệ thống AI. Việc đảm bảo Trace "sạch" và trích xuất nguồn chính xác cho các câu hỏi SLA là thành công lớn nhất của tôi trong dự án này.
