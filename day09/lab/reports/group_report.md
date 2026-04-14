# Báo Cáo Nhóm — Lab Day 09: Multi-Agent Orchestration

**Tên nhóm:** C401 - D6
**Ngày nộp:** 14/04/2026
**Thành viên:**
| Tên | Vai trò | Email |
|-----|---------|-------|
| Lê Huy Hồng Nhật | Tech Lead / Supervisor Owner | nhat050403@gmail.com |
| Nguyễn Quốc Khánh | Worker Owner (Retrieval) | khanhnq352005@gmail.com |
| Nguyễn Tuấn Khải | Worker Owner (Policy + Synthesis) | tuankhaidx2003@gmail.com |
| Phan Văn Tấn | MCP Owner | tana2k53nvt@gmail.com |
| Lê Công Thành | Eval / Trace Owner | lcthanh.htvn@gmail.com |
| Nguyễn Quế Sơn | Documentation Owner | sonnguyenque5@gmail.com |

---

## 1. Kiến trúc hệ thống (150–200 từ)

Hệ thống Day 09 được xây dựng trên nền tảng **Supervisor-Worker Orchestration** sử dụng **LangGraph**. Thay vì một khối duy nhất thực hiện mọi tác vụ như Day 08, nhóm đã chia nhỏ chức năng thành các chuyên gia (Workers) được điều phối bởi một Supervisor trung tâm.

- **Supervisor**: Đóng vai trò là "Dispatcher", sử dụng bộ từ khóa và mức độ rủi ro để định tuyến câu hỏi. Supervisor ghi lại `route_reason` để đảm bảo tính minh bạch hoàn toàn trong quá trình thực thi.
- **Workers Layer**: Bao gồm `retrieval_worker` (tra cứu tri thức), `policy_tool_worker` (xử lý ngoại lệ và nghiệp vụ), và `human_review` (chốt chặn an toàn cho các tác vụ nguy hiểm).
- **MCP Integration**: Hệ thống kết nối với một MCP Server tập trung, cung cấp 4 công cụ (`search_kb`, `get_ticket_info`, `check_access_permission`, `create_ticket`) giúp Agent thoát khỏi giới hạn của dữ liệu tĩnh và tương tác được với hệ thống bên thứ 3.

---

## 2. Quyết định kỹ thuật quan trọng nhất (200–250 từ)

**Quyết định:** Triển khai **Cơ chế Phân loại Rủi ro kết hợp Human-in-the-Loop (HITL)** thay vì để Agent tự quyết định cấp quyền.

**Bối cảnh vấn đề:**
Trong quá trình thử nghiệm, nhóm nhận thấy các yêu cầu như "cấp quyền Level 3" hay "truy cập khẩn cấp lúc 2am" là những kịch bản mang tính rủi ro bảo mật cực cao. Day 08 (Single Agent) thường dễ dàng bị bẻ lái (prompt injection) để cấp quyền sai.

**Các phương án đã cân nhắc:**

| Phương án | Ưu điểm | Nhược điểm |
|-----------|---------|-----------|
| **Pure LLM Decision** | Nhanh, mượt mà. | Dễ bị ảo giác hoặc bị "lừa" cấp quyền sai luật. |
| **Strict Rule-based** | Tuyệt đối an toàn. | Khó xử lý các tình huống nhạy cảm chưa có trong tập luật. |
| **Risk-based HITL (Chọn)** | Kết hợp sự linh hoạt của AI và sự an toàn của con người. | Có độ trễ khi chờ người duyệt. |

**Phương án đã chọn và lý do:**
Nhóm chọn **Risk-based HITL**. Supervisor sẽ đánh dấu `risk_high=True` khi gặp các keyword nhạy cảm. Điều này kích hoạt một node `human_review` chuyên biệt để tạm dừng pipeline. Đây là quyết định chiến lược để đảm bảo hệ thống AI có thể triển khai thực tế trong môi trường doanh nghiệp khắt khe.

**Bằng chứng thực tế:**
Trong trace `run_20260414_175011_570705.json`, câu hỏi về quyền Level 3 đã kích hoạt flag rủi ro, đẩy logic sang Policy Worker để gọi tool `check_access_permission`, thay vì chỉ trả lời bằng văn bản thông thường.

---

## 3. Kết quả chấm điểm Grading (150–200 từ)

**Tổng điểm ước tính:** 88 / 96

- **Câu thành công nhất (ID: `gq01`)**: Xử lý hoàn hảo việc phân vùng thời gian (Temporal Scoping). Agent nhận diện đúng đơn hàng ngày 31/01 cần áp dụng chính sách v3 cũ dù dữ liệu v4 đang là mặc định.
- **Câu cần cải thiện (ID: `gq07`)**: Hệ thống đôi khi vẫn đưa ra lời khuyên chung chung khi không tìm thấy thông tin cụ thể trong context (Abstain chưa đủ "cứng").
- **Điểm sáng kỹ thuật**: Việc xử lý câu hỏi **Multi-hop** (vừa hỏi SLA vừa hỏi quyền truy cập) diễn ra mượt mà nhờ Supervisor định tuyến tuần tự và tổng hợp dữ liệu từ nhiều Worker log.

---

## 4. So sánh Day 08 vs Day 09 — Architectural Shift

Mục tiêu chính của Day 09 không phải là tăng điểm số mà là tăng **tính minh bạch và khả năng mở rộng**.

| Metric | Day 08 | Day 09 | Nhận xét |
|--------|--------|--------|----------|
| **Completeness** | 0.64 | **0.75** | Tính đầy đủ tăng nhờ bóc tách logic xử lý ngoại lệ. |
| **Latency** | **~3s** | ~3.8s | Tăng nhẹ do modular overhead nhưng vẫn trong ngưỡng chấp nhận. |
| **Debug Time** | ~20p | **~2p** | Biết ngay lỗi ở node nào nhờ trace chi tiết. |

**Điều nhóm tự hào nhất:** Việc xây dựng thành công bộ Contract cho Worker giúp nhóm có thể thay đổi toàn bộ logic của Retrieval Worker mà không làm hỏng logic của Synthesis Worker.

---

## 5. Phân công và Đóng góp Nhóm

| Thành viên | Trách nhiệm chính | Đóng góp |
|------------|-------------------|----------|
| Lê Huy Hồng Nhật | Xây dựng Graph, Logic Supervisor, Tích hợp LangGraph | 17% |
| Nguyễn Quốc Khánh | Phát triển Retrieval Worker và Semantic Splitting | 17% |
| Nguyễn Tuấn Khải | Phát triển Policy Worker + Synthesis Worker | 17% |
| Phan Văn Tấn | Triển khai MCP Server Mock và Dispatcher tool | 17% |
| Lê Công Thành | Phát triển eval_trace.py và so sánh Single vs Multi | 16% |
| Nguyễn Quế Sơn | Documentation Owner, Trace Analyst, System Arch Graph | 16% |

**Đánh giá trung thực về quá trình làm việc nhóm:**
Nhóm phối hợp tốt thông qua việc thống nhất Contract trước khi code (Sprint 1). Việc duy trì `worker_contracts.yaml` giúp các thành viên code độc lập mà không cần chờ nhau, đảm bảo tiến độ tích hợp diễn ra mượt mà.

---

## 6. Nếu có thêm 1 ngày, nhóm sẽ làm gì?

Nhóm sẽ nâng cấp Supervisor lên **LLM-based Intent Classifier**. Hiện tại, nếu câu hỏi không chứa chính xác từ khóa, Supervisor dễ bị đẩy về route mặc định. Một bộ phân loại thông minh hơn sẽ giúp tăng độ phủ và độ chính xác của routing lên mức tối đa. Ngoài ra, việc song song hóa (Parallelism) các worker không phụ thuộc nhau sẽ giúp giảm đáng kể mức latency 16s hiện tại.

---

*File này lưu tại: `reports/group_report.md`*  
*Ngày hoàn thành: 14/04/2026*
