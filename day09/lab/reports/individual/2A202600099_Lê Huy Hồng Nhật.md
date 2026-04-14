# Báo Cáo Cá Nhân — Lab Day 09: Multi-Agent Orchestration

**Họ và tên:** Lê Huy Hồng Nhật
**Mã sinh viên:** 2A202600099
**Vai trò trong nhóm:** Tech Lead + Supervisor Owner
**Ngày nộp:** 2026-04-14
**Độ dài:** ~700 từ

---

## 1. Tôi phụ trách phần nào?

Tôi đảm nhiệm vai trò **Tech Lead** và **Supervisor Owner**, chịu trách nhiệm xây dựng phần orchestration cốt lõi để đảm bảo toàn bộ hệ thống có thể vận hành đồng bộ.

**Các module/file chính tôi phụ trách:**

* **`graph.py`** — xây dựng `AgentState`, `supervisor_node` / `route_decision`, cấu hình LangGraph (`retrieval_worker`, `policy_tool_worker`, `human_review`, `synthesis`), triển khai `run_graph`, `save_trace`. Tôi kết nối các worker thực tế (`retrieval_run`, `policy_tool_run`, `synthesis_run`) và thiết lập `run_id` có độ phân giải microsecond để tránh ghi đè trace khi chạy batch.
* **`contracts/worker_contracts.yaml`** — định nghĩa contract cho từng worker và MCP.

Ngoài ra, tôi chỉnh sửa **`eval_trace.py`**: bổ sung `_lab_path()`, xây dựng hàm **`compare_single_vs_multi()`** (so sánh kết quả Day08 từ JSON hoặc CSV A/B với Day09), thực hiện merge code từ các nhánh, đồng bộ **`nhat` → `main`**, và commit các file phục vụ grading (`grading_questions.json`, `grading_run.jsonl`, trace) theo đúng runbook.

**Kết nối trong nhóm:** Contract và state đóng vai trò như API chung; graph điều phối luồng xử lý và đảm bảo trace chứa đầy đủ các trường phục vụ SCORING.

**Bằng chứng:** `40ce0b0`, `05a4aac`, `bec8360`, `5ffa35c`, `86721dd`, `75766cc` (git log `nhat`/`main`).

---

## 2. Tôi đã ra một quyết định kỹ thuật gì?

**Quyết định:** Thiết lập **thứ tự kiểm tra routing trong `supervisor_node`: `human_review` trước**, sau đó đến policy và cuối cùng là retrieval/default.

**Lý do:** Với các câu hỏi chứa đồng thời từ khóa như “ticket/SLA” và mã lỗi dạng **ERR-…** không tồn tại trong KB, nếu ưu tiên SLA trước, hệ thống có thể route sai sang `retrieval_worker` và cố gắng trả lời bằng RAG. Theo thiết kế, các trường hợp lỗi không xác định cần được chuyển sang `human_review` trước.

**Các phương án đã cân nhắc:**

* Sử dụng LLM để phân loại route (độ chính xác cao hơn nhưng tăng latency và chi phí).
* Giữ rule keyword đơn giản với SLA trước ERR (dễ dẫn đến sai lệch như đã phân tích).

Tôi lựa chọn phương án **keyword kết hợp thứ tự ưu tiên rõ ràng**, nhằm đảm bảo trace luôn có `route_reason` minh bạch và tránh phụ thuộc thêm một lần gọi model chỉ để định tuyến.

**Trade-off:** Phương pháp này không xử lý tốt các trường hợp cần hiểu ngữ cảnh sâu; các trường hợp biên có thể cần điều chỉnh keyword dựa trên trace thực tế.

**Bằng chứng:** Trong `graph.py`, thứ tự routing được định nghĩa rõ: **human_review → policy → retrieval → default**. Trong trace batch, các câu chứa mã lỗi (ví dụ ERR-403) được chuyển sang review thay vì retrieval dù có xuất hiện từ khóa “ticket”.

---

## 3. Tôi đã sửa một lỗi gì?

**Lỗi:** Khi chạy `python eval_trace.py` từ thư mục gốc của repository thay vì `day09/lab`, hệ thống gặp lỗi `FileNotFoundError: data/test_questions.json` do sử dụng đường dẫn tương đối phụ thuộc vào CWD.

**Biểu hiện:** Pipeline không thể chạy bộ test 15 câu trong môi trường chấm hoặc khi clone repo; các file trace và artifact không được tạo đúng vị trí.

**Nguyên nhân:** `eval_trace.py` sử dụng đường dẫn tương đối mà không cố định theo thư mục lab.

**Cách khắc phục:** Thiết lập `_LAB_ROOT` kết hợp với hàm **`_lab_path()`** để toàn bộ đường dẫn (`data/`, `artifacts/`) luôn neo theo `day09/lab`; bổ sung tham số `--day08-results` với cơ chế resolve từ root repository.

**Kết quả trước/sau:**

* Trước: phát sinh `FileNotFoundError` khi chạy từ root.
* Sau: log hiển thị đầy đủ đường dẫn tuyệt đối đến `.../day09/lab/data/...`, trace được ghi vào `artifacts/traces/`.

Tham khảo commit: `05a4aac`, `5ffa35c`.

---

## 4. Tôi tự đánh giá đóng góp của mình

**Điểm làm tốt:** Tôi hoàn thiện sớm schema state và graph LangGraph, giúp các thành viên có thể phát triển song song. Tôi điều phối việc merge nhiều nhánh và đảm bảo `main`/`nhat` luôn đồng bộ với artifact phục vụ grading. Đồng thời, tôi hoàn thiện hàm `compare_single_vs_multi` để báo cáo có số liệu cụ thể thay vì để trống.

**Hạn chế / rủi ro:** Routing dựa trên keyword vẫn mang tính heuristic. Các câu như **gq09** (multi-hop) yêu cầu kết hợp nhiều nguồn (SLA và access), nên nếu chỉ sử dụng một worker hoặc một lần retrieve, hệ thống có thể chưa đạt kết quả tối ưu nếu không mở rộng orchestration.

**Phụ thuộc của nhóm vào tôi:** Các thành viên cần graph chạy end-to-end, trace JSON đầy đủ trường và pipeline grading hoạt động ổn định. Nếu graph hoặc contract sai, các module khác dù đúng vẫn khó đáp ứng yêu cầu chấm điểm.

**Phụ thuộc của tôi vào nhóm:** Chất lượng của `retrieval.py`, `policy_tool.py`, `synthesis.py`, `mcp_server.py`. Graph chỉ điều phối; nếu worker trả về dữ liệu kém hoặc MCP lỗi, chất lượng câu trả lời sẽ bị ảnh hưởng dù trace vẫn hợp lệ.

---

## 5. Nếu có thêm 2 giờ, tôi sẽ làm gì?

Nếu có thêm thời gian, tôi sẽ thiết kế lại một nhánh xử lý riêng cho các câu hỏi multi-hop (đặc biệt là gq09). Cụ thể, sau bước supervisor, nếu phát hiện câu hỏi đồng thời chứa các yếu tố như “P1/escalation” và “Level 2/access/contractor”, hệ thống sẽ thực hiện chuỗi retrieval có chủ đích hoặc cho phép policy gọi thêm tool. Mục tiêu là đảm bảo trace thể hiện rõ hai nguồn evidence (SLA và SOP) thay vì chỉ một lần truy xuất, phù hợp với yêu cầu cross-document của rubric.
