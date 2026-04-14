# Báo cáo Test Độc lập Retrieval Worker (Sprint 2)

## 1. Thông tin chung
- **Worker:** `retrieval_worker`
- **File:** `day09/lab/workers/retrieval.py`
- **Thời gian chạy:** 14/04/2026
- **Môi trường:** Python 3.9 + ChromaDB + OpenAI Embeddings (text-embedding-3-small)

## 2. Kết quả Indexing
Quá trình build index tự động đã hoàn thành với các tài liệu sau:
- `it_helpdesk_faq.txt`: 6 chunks
- `sla_p1_2026.txt`: 5 chunks
- `hr_leave_policy.txt`: 5 chunks
- `access_control_sop.txt`: 7 chunks
- `policy_refund_v4.txt`: 6 chunks
**Tổng cộng:** 29 chunks đã được index vào ChromaDB.

## 3. Kết quả Test Retrieval

### ▶ Query 1: "SLA ticket P1 là bao lâu?"
- **Số lượng retrieved:** 3 chunks
- **Kết quả tiêu biểu:**
    - **[1] (Score: 0.5889)** `sla_p1_2026.txt` > `Phần 2: SLA theo mức độ ưu tiên: Ticket P1:`
      *"Phản hồi ban đầu (first response): 15 phút kể từ khi ticket được tạo. Xử lý và khắc phục: 4 giờ..."*
    - **[2] (Score: 0.4859)** `sla_p1_2026.txt` > `Phần 3: Quy trình xử lý sự cố P1:`
      *"Bước 1: Tiếp nhận - On-call engineer nhận alert hoặc ticket, xác nhận severity trong 5 phút..."*

### ▶ Query 2: "Khi nào thì một ticket P1 được coi là quá hạn?"
- **Số lượng retrieved:** 3 chunks
- **Kết quả tiêu biểu:**
    - **[1] (Score: 0.5298)** `sla_p1_2026.txt` > `Phần 2: SLA theo mức độ ưu tiên: Ticket P1:`
      *"Phản hồi ban đầu (first response): 15 phút kể từ khi ticket được tạo. Xử lý và khắc phục..."*

### ▶ Query 3: "Tần suất cập nhật trạng thái của ticket P1?"
- **Số lượng retrieved:** 3 chunks
- **Kết quả tiêu biểu:**
    - **[1] (Score: 0.4930)** `sla_p1_2026.txt` > `Phần 2: SLA theo mức độ ưu tiên: Ticket P1:`
      *"Phản hồi ban đầu (first response): 15 phút kể từ khi ticket được tạo..."*

## 4. Kiểm tra Contract Compliance
- ✅ Trả về danh sách `retrieved_chunks`.
- ✅ Mỗi chunk bao gồm đầy đủ: `text`, `source`, `section`, `score`.
- ✅ Metadata được parse chính xác từ file gốc.

## 5. Kết luận
Sprint 2 đã hoàn thành xuất sắc. Worker hoạt động ổn định, chính xác và tuân thủ đúng contract đã đề ra. Sẵn sàng cho việc tích hợp sâu vào Graph (Sprint 3).
