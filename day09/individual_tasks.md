# Danh sách công việc cá nhân — Nguyễn Quốc Khánh
## Vai trò: Worker Owner — Retrieval
## File chính: `workers/retrieval.py`

---

### 1. Sprint 1: Setup & Skeleton (Giờ đầu tiên)
*   **Công việc cụ thể:**
    - [x] Tạo file `workers/retrieval.py`.
    - [x] Định nghĩa hàm `run(state: dict) -> dict` đúng theo contract trong `worker_contracts.yaml`.
    - [x] Implement phần log I/O (`worker_io_log`) để phục vụ tracing (BẮT BUỘC).
    - [x] Viết các function stubs (`search_chromadb`, `_build_index`) để team có thể tích hợp sớm.
*   **Phối hợp với:**
    - **Lê Huy Hồng Nhật (Tech Lead):** Chờ Nhật hoàn thiện `AgentState` và `worker_contracts.yaml` (khoảng 20 phút đầu) để khớp cấu trúc dữ liệu.
    - **Lê Công Thành (Trace & Eval):** Cung cấp skeleton code sớm để Thành setup pipeline test.

### 2. Sprint 2: Full Implementation (Giờ thứ 2)
*   **Công việc cụ thể:**
    - [x] Hoàn thiện hàm `search_chromadb()` kết nối với ChromaDB thật.
    - [x] Xử lý logic tự động build index từ tài liệu nếu collection rỗng.
    - [x] Test độc lập worker (không cần chạy qua graph) để đảm bảo trả về đúng `retrieved_chunks` (text, source, section, score).
*   **Phối hợp với:**
    - **Lê Công Thành (Trace & Eval):** Phản hồi và sửa lỗi ngay khi Thành chạy smoke test phát hiện crash hoặc sai format.
    - **Nguyễn Tuấn Khải (Policy & Synthesis):** Đảm bảo format của `retrieved_chunks` đúng yêu cầu đầu vào của Synthesis Worker.

### 3. Sprint 3: Tuning & Debugging (Giờ thứ 3)
*   **Công việc cụ thể:**
    - [x] Fix các lỗi phát sinh khi chạy full graph end-to-end. (Kết nối Retrieval vào Graph).
    - [x] Phân tích kết quả retrieval cho các câu hỏi test, đặc biệt là các câu multi-hop (cần chunks từ nhiều file).
    - [x] Chuẩn bị số liệu/nội dung cho báo cáo cá nhân.
*   **Phối hợp với:**
    - **Lê Huy Hồng Nhật:** Review code và tối ưu hóa logic nếu supervisor route sai do thiếu thông tin retrieval.
    - **Lê Công Thành:** Lấy dữ liệu trace từ `artifacts/traces/` để làm minh chứng cho báo cáo.

### 4. Sprint 4: Finalize & Reporting (Giờ thứ 4)
*   **Công việc cụ thể:**
    - [x] Viết báo cáo cá nhân (`reports/individual/khanh.md`): 500-800 từ.
    - [x] **Trọng tâm phân tích:** Các câu hỏi `gq01` và `gq05` (liên quan đến SLA P1).
    - [x] Phân tích ảnh hưởng của chunking và search strategy đến chất lượng câu trả lời.
*   **Phối hợp với:**
    - **Nguyễn Quế Sơn (Documentation):** Cung cấp thông tin chi tiết về phần Retrieval để Sơn hoàn thiện `group_report.md` và các bản doc hệ thống.
    - **Nhật & Thành:** Kiểm tra checklist cuối cùng trước khi chạy Grading (17:00).

---

### Checklist hoàn thành (Master Checklist cho Khánh)
- [x] `workers/retrieval.py` chạy độc lập không lỗi.
- [x] Output đúng contract (có `retrieved_chunks` và `worker_io_log`).
- [ ] Commit message có prefix `[Khanh][SX]`.
- [ ] Báo cáo cá nhân phân tích sâu câu `gq01`/`gq05`.
