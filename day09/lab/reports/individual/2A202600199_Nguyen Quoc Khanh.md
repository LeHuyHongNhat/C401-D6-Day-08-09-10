# Báo Cáo Cá Nhân — Lab Day 09: Multi-Agent Orchestration

**Họ và tên:** Nguyễn Quốc Khánh - 2A202600199
**Vai trò trong nhóm:** Worker Owner (Retrieval) & Integration Tech Lead  
**Ngày nộp:** 14/04/2026  

---

## 1. Trách nhiệm và Vai trò trong dự án

Trong dự án Multi-Agent Orchestration thuộc Lab Day 09, tôi đảm nhận hai vai trò chính:
1.  **Thiết kế Retrieval Worker**: Xây dựng pipeline RAG hoàn chỉnh trong `workers/retrieval.py` sử dụng ChromaDB.
2.  **Tối ưu hóa tích hợp**: Đảm bảo sự ổn định của luồng dữ liệu (State Management) giữa Supervisor và các Worker. Tôi đã trực tiếp xử lý các lỗi xung đột hệ thống và chuẩn hóa Traceability cho toàn bộ pipeline trong giai đoạn tích hợp cuối cùng.

---

## 2. Quyết định kỹ thuật: Regex-based Semantic Splitting

Một đóng góp kỹ thuật then chốt của tôi là áp dụng **Semantic Splitting dựa trên Regex** thay vì các phương pháp chunking ký tự thông thường.

**Lý do:** Các tài liệu chính sách nội bộ (SLA, SOP) có cấu trúc phân cấp chặt chẽ. Việc chia nhỏ văn bản theo độ dài cố định thường làm xé lẻ các điều khoản, gây mất ngữ cảnh cho LLM. Tôi đã triển khai logic nhận diện các Header định dạng `=== ... ===` để phân tách tài liệu thành những khối thông tin có ý nghĩa trọn vẹn. 

Bằng chứng từ kết quả Trace cho thấy, các chunks trả về từ Worker của tôi luôn giữ được các ràng buộc logic của quy định, giúp Synthesis Worker tổng hợp câu trả lời chính xác và grounded hoàn toàn vào tài liệu nguồn.

---

## 3. Khắc phục lỗi MCP Regression & Traceability

Thách thức lớn nhất tôi đối mặt là việc xử lý các lỗi phát sinh ngay trước giờ nộp bài chính thức (17:00). Sau khi thực hiện `git pull` bản cập nhật từ nhóm, hệ thống đã gặp lỗi nghiêm trọng do sự thay đổi giao diện MCP từ phía các thành viên khác.

**Vấn đề & Giải pháp:**
- **MCP Interface mismatch**: `mcp_server.py` thay đổi sang kiến trúc Class khiến `policy_tool_worker` bị crash. Tôi đã nhanh chóng refactor module này để tương thích với Class-based interface.
- **Thiếu hụt Traceability**: Tôi đã chuẩn hóa lại `AgentState` trong `graph.py` và cập nhật logic trích xuất nguồn trong `eval_trace.py`. Việc này đảm bảo các trường dữ liệu quan trọng như `workers_called` và `sources` được hiển thị đầy đủ trong file log cuối cùng, đáp ứng 100% tiêu chuẩn chấm điểm Trace & Observability.

---

## 4. Phân tích trọng tâm từ Trace (Official Grading Run)

Dựa trên kết quả từ file `grading_run.jsonl`, tôi xin phân tích hai ví dụ điển hình:

**Câu gq01 (Multi-detail extraction):**
- **Trace Analysis**: Supervisor route chính xác vào `retrieval_worker`. Hệ thống đã tìm thấy chính xác section "Phần 2: SLA" trong file `sla_p1_2026.txt`.
- **Kết quả**: Nhờ Semantic Chunking, Synthesis Worker đã nhận được đầy đủ các mốc thời gian (15 phút phản hồi, 4 giờ xử lý và 10 phút escalation) trong cùng một ngữ cảnh, giúp trả lời chính xác cả 3 ý mà không bị lẫn lộn thông tin.

**Câu gq09 (Multi-hop Reasoning):**
- **Trace Analysis**: `workers_called: ["policy_tool_worker", "synthesis_worker"]`.
- **Kết quả**: Đây là câu hỏi phức tạp yêu cầu thông tin từ cả SLA và Access Control. Policy Worker đã thực hiện gọi MCP `search_kb` để lấy dữ liệu chéo từ cả hai tài liệu. Hệ thống đã giải quyết thành công yêu cầu "Emergency bypass" cho Level 2 — một minh chứng cho thấy sự ưu việt của kiến trúc Multi-Agent so với kiến trúc Single-Agent ở Day 08.

---

## 5. So sánh kiến trúc và Tự đánh giá

**So sánh Day 08 và Day 09:**
Kiến trúc Multi-Agent (Day 09) cung cấp khả năng **phân tách trách nhiệm (Separation of Concerns)** rõ rệt. Thay vì LLM phải xử lý cả việc tìm kiếm và phân tích quy định, Retrieval Worker của tôi chỉ tập trung cung cấp bằng chứng, còn Policy Worker tập trung vào logic logic kiểm tra. Điều này giảm thiểu tối đa hiện tượng "hallucination" và giúp hệ thống dễ dàng debug hơn thông qua Trace log.

**Tự đánh giá:**
Tôi đánh giá cao khả năng thích nghi và xử lý lỗi của mình trong giai đoạn tích hợp. Tuy nhiên, tôi nhận thấy Latency của hệ thống vẫn còn khá cao (~5s) do việc gọi các công cụ MCP chưa được song song hóa. Nếu có thêm thời gian, tôi sẽ triển khai Parallel Tool Calling để tối ưu hiệu năng.

---

## 6. Kết luận

Dự án này không chỉ giúp tôi làm chủ kỹ thuật Vector DB và Agent Orchestration (LangGraph) mà còn rèn luyện tư duy thiết kế hệ thống có tính quan sát cao (Observability). Việc đảm bảo bộ kết quả Grading Run hoàn hảo vào phút chót là thành tích tự hào nhất của tôi trong dự án này.
