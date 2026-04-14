# Báo Cáo Cá Nhân — Lab Day 09: Multi-Agent Orchestration

**Họ và tên:** Nguyễn Quốc Khánh  
**Vai trò trong nhóm:** Worker Owner — Retrieval  
**Ngày nộp:** 14/04/2026  
**Độ dài yêu cầu:** 500–800 từ  

---

## 1. Tôi phụ trách phần nào?

Trong dự án này, tôi chịu trách nhiệm chính về module **Retrieval Worker**, cụ thể là file `workers/retrieval.py`. Công việc của tôi bao gồm việc xây dựng pipeline RAG từ khâu xử lý tài liệu (indexing) đến khâu tìm kiếm ngữ nghĩa (semantic search) bằng ChromaDB.

Tôi đã thiết lập I/O contract chặt chẽ cho worker của mình để đảm bảo kết nối mượt mà với Supervisor (anh Lê Huy Hồng Nhật) và Synthesis Worker (anh Nguyễn Tuấn Khải). Cụ thể, hàm `run(state)` của tôi nhận vào một task và trả về danh sách `retrieved_chunks` chuẩn hóa với đầy đủ metadata (source, section, score). Ngoài ra, tôi cũng phụ trách phần **Tracing I/O** bằng cách ghi lại chi tiết input/output vào bảng `worker_io_log` của state, giúp nhóm Trace & Docs (anh Lê Công Thành) dễ dàng phân tích lỗi sau này.

---

## 2. Tôi đã ra một quyết định kỹ thuật gì?

Một quyết định kỹ thuật quan trọng mà tôi đã thực hiện trong Sprint 2 và tối ưu hóa trong Sprint 3 là áp dụng **Semantic Splitting (theo Section Headers)** thay vì dùng các thư viện Recursive Character Splitting phổ biến.

**Lý do chọn cách này:**
Các tài liệu quy định nội bộ (`SLA`, `Access Control`, `Policy`) thường có cấu trúc rất rõ ràng theo từng mục như `Phần 1`, `Điều 2`, `Section 3`. Nếu dùng bộ tách văn bản thông thường, một quy định có thể bị cắt làm đôi ở các chunk khác nhau, làm mất đi tính toàn vẹn của thông tin. Tôi đã viết hàm `split_into_chunks` sử dụng Regex để nhận diện các header `=== ... ===`. Điều này đảm bảo mỗi chunk là một điều khoản hoặc một bước quy trình hoàn chỉnh.

**Bằng chứng từ trace:**
Trong câu hỏi `q15` về quy trình xử lý sự cố P1 lúc 2 giờ sáng, nhờ semantic splitting, worker của tôi đã trả về trọn vẹn chunk "Phần 3: Quy trình xử lý sự cố P1" bao gồm đủ 5 bước mà không bị lẫn lộn thông tin từ các phần khác. Điều này giúp Synthesis Worker tổng hợp câu trả lời cực kỳ chính xác.

```python
# Đoạn code thực hiện semantic splitting của tôi:
def split_into_chunks(content: str, base_meta: dict) -> List[Dict[str, Any]]:
    section_parts = re.split(r"(===\s*.+?\s*===)", cleaned_content)
    # ... logic để nhóm header và nội dung thành chunk hoàn chỉnh ...
```

---

## 3. Tôi đã sửa một lỗi gì?

Trong quá trình chạy Full Graph End-to-End ở Sprint 3, tôi phát hiện một lỗi nghiêm trọng khiến hệ thống bị crash với thông báo `'NoneType' object has no attribute 'get'`.

**Symptom:** 
Khi Supervisor route vào `retrieval_worker`, sau đó chuyển sang `synthesis_worker`, toàn bộ pipeline bị dừng lại và không trả về câu trả lời, dù retrieval đã lấy được thông tin.

**Root cause:** 
Lỗi nằm ở sự thiếu đồng nhất về state khởi tạo. Synthesis Worker dự đoán rằng `policy_result` luôn tồn tại dưới dạng dictionary để gọi `.get("exceptions_found")`. Tuy nhiên, ở nhánh route chỉ đi qua Retrieval, `policy_result` vẫn mang giá trị khởi tạo là `None`. 

**Cách sửa:** 
Tôi đã chủ động phối hợp với Supervisor Owner để sửa file `graph.py`, khởi tạo `policy_result` là một dictionary trống `{}` thay vì `None`. Đồng thời, tôi cũng tư vấn cho bạn viết module Synthesis thêm kiểm tra điều kiện an toàn.

**Bằng chứng trước/sau:**
- **Trước**: Trace hiện `synthesizer: ERROR: 'NoneType' object has no attribute 'get'`, `confidence=0.0`.
- **Sau**: Trace `trace_20260414_164023.json` cho thấy `final_answer` được tạo ra thành công và `confidence` đạt 0.62.

---

## 4. Tôi tự đánh giá đóng góp của mình

**Tôi làm tốt nhất ở điểm nào?**
Tôi đã hoàn thiện module Retrieval rất sớm và ổn định, giúp cả nhóm có bằng chứng thực tế để test routing ngay từ Sprint 2. Ngoài ra, việc tôi chủ động debug lỗi state chung thay vì chỉ quan tâm đến worker của riêng mình đã giúp pipeline end-to-end hoạt động trơn tru.

**Tôi làm chưa tốt hoặc còn yếu ở điểm nào?**
Ban đầu tôi đặt `top_k=3` cho retrieval, điều này dẫn đến việc thiếu thông tin cho các câu hỏi multi-hop phức tạp (cần context từ cả SLA và Access Control). Tôi phải đợi đến Sprint 3 mới nhận ra và tăng lên `top_k=5`.

**Nhóm phụ thuộc vào tôi ở đâu?**
Retrieval là "cửa ngõ" dữ liệu. Nếu retrieval trả về sai nguồn hoặc chunk rác, tất cả logic kiểm tra policy sau đó và câu trả lời cuối cùng đều vô nghĩa. Toàn bộ hệ thống Multi-hop reasoning phụ thuộc vào chất lượng context tôi cung cấp.

---

## 5. Nếu có thêm 2 giờ, tôi sẽ làm gì?

Tôi sẽ thử nghiệm kỹ thuật **Hybrid Search (kết hợp Semantic Search và BM25)**. Qua phân tích trace của câu `gq05`, tôi nhận thấy nếu người dùng gõ sai thuật ngữ chuyên môn, chỉ dùng vector search đôi khi không tìm được chính xác section header. Kết hợp BM25 sẽ giúp tăng độ phủ cho các từ khóa chính xác (keywords).
