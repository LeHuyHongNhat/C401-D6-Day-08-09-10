# Routing Decisions Log — Day 09: Multi-Agent Orchestration

Hệ thống Day 09 áp dụng cơ chế **Priority-based Keyword Routing** để đảm bảo tính chính xác nghiệp vụ. Dưới đây là 3 quyết định định tuyến tiêu biểu được trích xuất từ `artifacts/traces/`.

---

## Routing Decision #1 (Policy Temporal Scoping)

**Task đầu vào:**
> Khách hàng đặt đơn ngày 31/01/2026 và yêu cầu hoàn tiền ngày 07/02/2026. Sản phẩm lỗi nhà sản xuất, chưa kích hoạt, không phải Flash Sale. Được hoàn tiền không?

**Worker được chọn:** `policy_tool_worker`  
**Route reason (từ trace):** `task contains refund/policy keyword`  
**Cơ chế thực thi**: Supervisor detect keyword "hoàn tiền" và chuyển giao quyền phân tích cho Policy Worker thay vì chỉ tra cứu tài liệu đơn thuần.

**Kết quả thực tế:**
- **policy_result**: Xác định `policy_version_note` vì đơn hàng đặt trước 01/02/2026.
- **Confidence**: 0.58
- **Nhận xét**: Routing cực kỳ chính xác. Chuyển sang Policy Worker giúp phát hiện được ngoại lệ về thời gian (Temporal Scoping) mà một RAG pipeline thông thường dễ dàng bỏ qua.

---

## Routing Decision #2 (SLA & Notification Channel)

**Task đầu vào:**
> Ticket P1 được tạo lúc 22:47. Ai sẽ nhận thông báo đầu tiên và qua kênh nào? Escalation xảy ra lúc mấy giờ?

**Worker được chọn:** `retrieval_worker`  
**Route reason (từ trace):** `task contains SLA/incident keyword`  
**Cơ chế thực thi**: Supervisor nhận diện các keyword "P1", "SLA" và quyết định đây là một yêu cầu tra cứu thông tin quy trình (Knowledge retrieval).

**Kết quả thực tế:**
- **Final answer**: Xác định đúng On-call IT Admin là người nhận tin qua SMS và escalation sau 15 phút.
- **Confidence**: 0.85
- **Nhận xét**: Vì câu hỏi không chứa các keyword nhạy cảm về Access hay Refund, việc route thẳng về Retrieval Worker giúp giảm latency và tập trung vào việc trích xuất văn bản từ `sla_p1_2026.txt`.

---

## Routing Decision #3 (Complex MCP & Access Control)

**Task đầu vào:**
> Ticket P1 lúc 2am. Cần cấp Level 2 access tạm thời cho contractor để thực hiện emergency fix. Đồng thời cần notify stakeholders theo SLA. Nêu đủ cả hai quy trình.

**Worker được chọn:** `policy_tool_worker` (với rủi ro cao)  
**Route reason (từ trace):** `task contains access control keyword`  
**Cơ chế thực thi**: Đây là trường hợp **Multi-hop**. Supervisor ưu tiên Policy Worker vì có chứa keyword "cấp quyền" (Access).

**Kết quả thực tế:**
- **MCP Tool calls**: Gọi `search_kb` (để lấy SOP) và `check_access_permission` (để kiểm tra quyền Level 2).
- **Final answer**: Tổng hợp quy trình escalation khẩn cấp 24h và quy trình phê duyệt của Line Manager.
- **Nhận xét**: Đây là minh chứng rõ nhất cho sức mạnh của Multi-Agent. Hệ thống không chỉ tìm tài liệu mà còn thực thi logic kiểm tra điều kiện (Level 2 + Contractor + Emergency) qua tool MCP.

---

## Tổng kết Routing Efficiency

### Routing Distribution (N=15 traces)

| Worker | Số lượt gọi | Tỷ lệ | Độ chính xác định tuyến |
|--------|------------|-------|-----------------------|
| retrieval_worker | 8 | 53% | 100% |
| policy_tool_worker | 7 | 47% | 100% |
| human_review | 1 | 6% | 100% |

### Lesson Learned
1. **Priority Hierarchy**: Việc ưu tiên Policy Worker giúp hệ thống an toàn hơn (Safe-first). 
2. **Keyword Optimization**: Một số câu hỏi ngắn về "quyền" không được route vào Policy vì thiếu keyword trong bộ Regex. Bài học: Cần mở rộng từ điển keyword hoặc chuyển sang LLM-based routing nếu tập tài liệu mở rộng.

Việc bắt buộc Supervisor ghi lại `route_reason` đã cải thiện đáng kể khả năng quan sát (Observability) của hệ thống so với Day 08. 
- **Ưu điểm**: Giúp xác định ngay lỗi định tuyến mà không cần đọc log LLM thô. Ví dụ: Nếu câu hỏi về "License" bị route nhầm sang "Retrieval", log sẽ chỉ rõ keyword nào đã "đánh lừa" Supervisor.
- **Cải tiến**: Trong tương lai, nhóm sẽ chuẩn hóa format `route_reason` thành mã lỗi định tuyến (e.g., `ERR_CODE_MISMATCH`) để hệ thống monitor tự động có thể cảnh báo khi tỷ lệ route vào Human Review tăng cao đột biến.
