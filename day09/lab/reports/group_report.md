# Báo Cáo Nhóm — Lab Day 09: Multi-Agent Orchestration

**Tên nhóm:** C401 - D6  
**Repo:** https://github.com/LeHuyHongNhat/C401-D6-Day-08-09-10  
**Ngày nộp:** 14/04/2026  
**Độ dài khuyến nghị:** 600–1000 từ  

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

## 1. Kiến trúc nhóm đã xây dựng

**Hệ thống tổng quan:** Nhóm triển khai **Supervisor–Worker** bằng **LangGraph** (`graph.py`): luồng `START → supervisor → (retrieval_worker | policy_tool_worker | human_review) → synthesis → END`. Trạng thái dùng `AgentState` (TypedDict) thống nhất với `contracts/worker_contracts.yaml` để mọi worker ghi `workers_called`, `route_reason`, `worker_io_log` / trace phục vụ chấm điểm.

Chi tiết pipeline và sơ đồ được mô tả trong `docs/system_architecture.md`.

**Routing logic cốt lõi:** **Keyword matching** trong `supervisor_node` (không dùng LLM classifier cho route). Thứ tự ưu tiên: kiểm tra mã lỗi / HITL (`human_review`) trước, sau đó refund/policy/access, rồi SLA/incident → `retrieval_worker`, còn lại default retrieval. Mỗi lần route ghi `route_reason` cụ thể (không để `"unknown"`) — đúng yêu cầu Sprint 1 trong SCORING.md.

**MCP tools đã tích hợp** (module `mcp_server.py`, gọi từ `policy_tool_worker`): `search_kb`, `get_ticket_info`, `check_access_permission`, `create_ticket`.

**Ví dụ trace có gọi MCP** — từ `artifacts/grading_run.jsonl`, câu **gq03** (Level 3 access):

- `supervisor_route`: `policy_tool_worker`  
- `mcp_tools_used`: gồm `search_kb` (trả về chunks từ KB) và `check_access_permission` (payload có `required_approvers`, `approver_count`).

Cùng file log, **gq09** cũng ghi `search_kb` + `check_access_permission` với `access_level` 2 và `requester_role` contractor — minh chứng MCP gắn với câu multi-hop.

---

## 2. Quyết định kỹ thuật quan trọng nhất

**Quyết định:** Dùng **supervisor keyword-based** và **ưu tiên nhánh `human_review` / HITL** cho tác vụ không chắc chắn (mã lỗi không rõ), thay vì ép toàn bộ câu có từ “ticket/SLA” vào retrieval.

**Bối cảnh:** Cần trace minh bạch (`route_reason`), latency routing thấp, và tránh route sai khi câu hỏi vừa giống SLA vừa là tình huống cần escalate người.

**Các phương án đã cân nhắc:**

| Phương án | Ưu điểm | Nhược điểm |
|-----------|---------|------------|
| LLM phân loại intent | Linh hoạt ngữ nghĩa | Thêm latency, phụ thuộc API, khó debug |
| Chỉ một RAG monolith (Day 08) | Đơn giản | Không tách bước, khó chứng minh từng bước |
| **Keyword + thứ tự ưu tiên (chọn)** | Nhanh, trace rõ, đủ cho bộ câu lab | Phụ thuộc bộ từ khóa; câu biên có thể cần mở rộng sau |

**Phương án đã chọn và lý do:** Giữ **keyword routing** và document thứ tự kiểm tra trong code để điểm Sprint 1 (graph chạy được, ≥2 loại route, `route_reason` rõ) được đáp ứng ổn định.

**Bằng chứng từ trace/code:**

```text
# grading_run.jsonl — mọi dòng đều có supervisor_route + route_reason (tránh -20% điểm câu theo SCORING.md khi thiếu field)
"gq05": "route_reason": "task contains SLA/incident keyword", "supervisor_route": "retrieval_worker"
"gq03": "route_reason": "task contains access control keyword", "supervisor_route": "policy_tool_worker"
```

---

## 3. Kết quả grading questions (theo SCORING.md)

### 3.1 Cách chấm (trích SCORING.md)

- **Tổng raw tối đa:** **96** điểm (10 câu `gq01`–`gq10`).  
- **Quy đổi sang 30 điểm nhóm (phần grading):**  
  `Điểm grading = (tổng điểm raw đạt được / 96) × 30`  
- **Mức theo từng câu:** **Full** (đủ mọi `grading_criteria`), **Partial** (≥50% criteria, không hallucinate), **Zero**, **Penalty** (bịa thông tin → **−50%** điểm câu).  
- **Bổ sung Day 09:** Thiếu `supervisor_route` hoặc `route_reason` trong trace → **−20% điểm câu đó** (dù câu trả lời đúng).  
- **Điểm chính thức** do giảng viên chấm theo rubric; nhóm **không** tự thay thế bằng một con số “chốt sổ” nếu chưa có bảng điểm từ lớp.

### 3.2 Tự đánh giá dựa trên `artifacts/grading_run.jsonl` + `data/grading_questions.json`

**Trace format:** 10 dòng JSONL đều có `supervisor_route`, `route_reason`, `workers_called`, `mcp_tools_used` — **đủ điều kiện tránh phạt −20%** vì thiếu field.

**Câu pipeline xử lý tốt (ứng viên Full / Partial cao):**

- **gq04** (store credit **110%**) — answer khớp số liệu policy, có cite.  
- **gq05** (escalate sau 10 phút) — nêu escalate lên Senior Engineer, khớp SLA.  
- **gq10** (Flash Sale + lỗi NSX) — kết luận không hoàn tiền, trích `policy_refund_v4.txt`, khớp hướng exception completeness.

**Câu cần lưu ý / dễ Partial:**

- **gq01:** Tiêu chí yêu cầu cả **PagerDuty** trong kênh thông báo; answer trong log chỉ nêu Slack + email rõ ràng → **có thể không đạt Full** theo đúng checklist.  
- **gq02** (temporal — đơ 31/01, hoàn tiền 07/02, phạm vi **v3 vs v4**): tiêu chí nhấn mạnh **abstain / không bịa nội dung v3**; answer hiện kết luận “không hoàn tiền” theo v4 — **cần GV xem có đủ tiêu chí “nhận ra đơ trước 01/02 áp dụng v3” hay không**.  
- **gq07** (mức phạt tài chính): answer **“Không đủ thông tin trong tài liệu nội bộ.”** — đúng hướng **abstain**, không bịa số (**tránh Penalty** theo bảng gq07 trong SCORING.md). Có thể Partial nếu coi là abstain hơi mỏng so với gợi ý “liên hệ bộ phận”.

**gq09 (16 điểm, multi-hop):** Trace ghi `workers_called`: `["policy_tool_worker", "synthesis_worker"]` — **đủ 2 worker** (điều kiện **trace bonus +1** trong SCORING nếu GV áp dụng). Nội dung gộp SLA + Level 2 emergency; cần đối chiếu từng bullet trong `grading_criteria` (vd. đủ **3 kênh** notification gồm PagerDuty) — **có thể Partial** nếu thiếu ý trong answer.

---

## 4. So sánh Day 08 vs Day 09 — Điều nhóm quan sát được

Nguồn số liệu tổng hợp: `artifacts/eval_report.json` (chạy sau `eval_trace.py`) và bảng trong `docs/single_vs_multi_comparison.md`.

**Lưu ý phương pháp:** Điểm **0.885** (Day 08) trong `eval_report.json` là **proxy** từ scorecard CSV (trung bình bốn metric /20), còn **0.515** (Day 09) là **confidence trung bình** từ trace — **không cùng định nghĩa một chỉ số**, không nên kết luận “Day 09 kém hơn 37% chất lượng” chỉ từ hai con số này. So sánh **latency** và **routing** thì nhất quán hơn.

| Metric | Day 08 (trong repo) | Day 09 (trong repo) | Nhận xét |
|--------|---------------------|---------------------|----------|
| Proxy chất lượng scorecard | ~0.885 (`eval_report` — từ CSV baseline) | avg **confidence** ~0.515 (`eval_report`) | Khác loại metric — cần grading rubric để so accuracy |
| Latency | Không đo trong CSV Day 08 | **~3851 ms** trung bình (`eval_report`) | Đa node + MCP, chậm hơn single-agent baseline đo được |
| Minh bạch | Không có `route_reason` per step | Có `supervisor_route` + `route_reason` + `workers_called` | Đúng mục tiêu SCORING / debug |

**Điều bất ngờ:** Cùng bộ câu, multi-agent **tăng chi phí latency** nhưng **giảm thời gian đoán lỗi** khi đọc trace (nhóm ghi nhận trong `single_vs_multi_comparison.md`).

**Khi multi-agent “không lợi”:** Câu chỉ cần một lần retrieve đơn giản vẫn phải qua supervisor + synthesis — overhead không cần thiết nếu không cần policy/MCP.

---

## 5. Phân công và đánh giá nhóm

| Thành viên | Phần đã làm (chính) | Ghi chú |
|------------|---------------------|---------|
| Lê Huy Hồng Nhật | `graph.py`, contracts, merge nhánh, `eval_trace` (path, so sánh Day08–Day09), run grading | Tech Lead |
| Nguyễn Quốc Khánh | `workers/retrieval.py`, Chroma, semantic split | Sprint 2 |
| Nguyễn Tuấn Khải | `policy_tool.py`, `synthesis.py` | Sprint 2–3 |
| Phan Văn Tấn | `mcp_server.py`, dispatcher tools | Sprint 3 |
| Lê Công Thành | `eval_trace`, trace validation, smoke test | Sprint 4 (theo commit nhóm) |
| Nguyễn Quế Sơn | `docs/system_architecture.md`, routing, single vs multi | Documentation |

**Làm tốt:** Thống nhất contract trước khi code; trace JSONL đủ field cho SCORING; có `grading_run.jsonl` trong repo.

**Chưa tốt / rủi ro:** Một số câu grading (gq01, gq02, gq09) cần **đối chiếu từng bullet** với answer — nhóm chưa tự chấm điểm raw chính thức.

**Nếu làm lại:** Ghi rõ **ownership eval_trace** (merge nhiều người) trong README để khớp evidence commit.

---

## 6. Nếu có thêm 1 ngày, nhóm sẽ làm gì?

1. **Rà từng câu `gq01`–`gq10`** theo đúng `grading_criteria` trong `grading_questions.json`, ước lượng raw **trước khi nộp**, và bổ sung **PagerDuty** / abstain **gq02** nếu trace cho thấy thiếu (bằng chứng: so khớp answer hiện tại với checklist SCORING).  
2. **Không dùng latency “16s” chung chung** — lấy **max** / **p95** từ từng dòng `latency_ms` trong `grading_run.jsonl` nếu cần báo cáo đuôi dài (trung bình ~vài giây theo `eval_report`, không phải 16s trung bình).