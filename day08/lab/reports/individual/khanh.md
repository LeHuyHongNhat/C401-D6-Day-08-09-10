# Báo Cáo Cá Nhân — Lab Day 08: RAG Pipeline

**Họ và tên:** Nguyễn Quốc Khánh  
**Vai trò trong nhóm:** Retrieval Owner  
**Ngày nộp:** 13/04/2026  
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi đã làm gì trong lab này? (100-150 từ)

> Mô tả cụ thể phần bạn đóng góp vào pipeline:
- Trong lab này, tôi đảm nhiệm vai trò Retrieval Owner, tập trung chủ yếu vào Sprint 1 và Sprint 3.
- **Sprint 1**: Tôi đã implement cơ chế chunking thông minh (`split_into_chunks` trong `index.py`), cắt file văn bản dựa trên Semantic Splitting (theo các thẻ `=== Title ===`). Đồng thời, tôi xử lý việc gán Alias đặc biệt cho metadatas (như gán "approval matrix" cho file SOP truy cập) để giúp hệ thống nhận diện tốt hơn từ vựng của người dùng.
- **Sprint 3**: Nhận thấy phương pháp Dense retrieval không bắt tốt các mã lỗi (VD: `ERR-403-AUTH`), tôi đã triển khai phương pháp Hybrid Search bằng cách code hàm `retrieve_hybrid` với thuật toán Reciprocal Rank Fusion (RRF). Nhờ đó, hệ thống được tăng cường vừa bắt được ý nghĩa câu hỏi vừa bắt chính xác các keyword kĩ thuật.
- **Phối hợp**: Tôi làm việc chặt chẽ cùng anh Khải cùng chia sẻ task Retrieval để đưa dữ liệu qua BM25 và kết nối với Tech Lead (Nhật) để cấu trúc output metadata.

---

## 2. Điều tôi hiểu rõ hơn sau lab này (100-150 từ)

> Chọn 1-2 concept từ bài học mà bạn thực sự hiểu rõ hơn sau khi làm lab.
Sau khi kết thúc bài lab, tôi đã hiểu sâu rễ hơn về nguyên lý đánh trọng số và kết hợp trong **Hybrid Search (Dense + Sparse)**:
1.  **Sự chênh lệch bản chất Score**: Tôi nhận thấy điểm trả về của Dense Search (Euclidean, Cosine) và BM25 (TF-IDF base) hoàn toàn không cùng dải giá trị. Việc cộng trực tiếp hai loại điểm này sẽ gây sai lệch nghiêm trọng.
2.  **Giá trị của RRF (Reciprocal Rank Fusion)**: Việc áp dụng công thức Score dựa theo k + Rank thực sự là phương thức cứu cánh khi muốn dung hoà điểm từ nhiều retriever. Phương pháp này chỉ quan tâm thứ tự xếp hạng (Rank) thay vì raw score, giúp đảm bảo tài liệu tốt trên cả hai góc độ (Dense/Sparse) luôn được đẩy lên top kết quả một cách mượt mà nhất.

---

## 3. Điều tôi ngạc nhiên hoặc gặp khó khăn (100-150 từ)

> Điều gì xảy ra không đúng kỳ vọng? Lỗi nào mất nhiều thời gian?
- **Khó khăn về Pipeline BM25s**: Một lỗi ngớ ngẩn nhưng gây mất thời gian lớn là việc đồng bộ format index giữa `index.py` và `retrieve_sparse`. Ban đầu, lệnh `load` file `pkl` metadata liên tục bị miss logic do serialize file docs và module xung đột version `lowercase` của hàm `bm25s.tokenize()`. Việc debug tận gốc các input đầu vào của thư viện giúp tôi tỉnh táo và cẩn thận hơn khi thiết kế interface giữa các module làm việc nhóm.
- **Ngạc nhiên về sức mạnh Sparse Search:** Tôi luôn đinh ninh vector embeddings thần thánh nhưng đến khi query các mã "ERR-403-AUTH", Dense search liên tiếp báo lỗi abstain do context kéo về bị trôi. Ngay khi kết hợp BM25 (TF-IDF keyword matching), lỗi này được trị dứt điểm hoàn toàn.

---

## 4. Phân tích một câu hỏi trong scorecard (150-200 từ)

> Chọn 1 câu hỏi trong test_questions.json mà nhóm bạn thấy thú vị.

**Câu hỏi:** "Làm sao để có Approval Matrix và cấp quyền hệ thống?" (Tương tự q07 hoặc query kiểm tra alias)

**Phân tích:**
- Khi chạy bằng cấu hình Baseline (chỉ Dense Search), độ chính xác Context Recall thường rớt cực thấp do vector của "Approval Matrix" rất xa so với cái tên chính thức "Access Control SOP". Do vậy, LLM ở phía generation không có đủ evidence và thường xuyên bị ảo giác (penalty error) hoặc đành trả lời là abstain (Không đủ thông tin).
- Tuy nhiên trong **Variant 1 (Hybrid Search)**, chức năng Sparse Search với BM25 của `retrieve_hybrid` đã lập tức phát huy tác dụng. Vì ở Sprint 1 tôi đã cố tình gài alias "Approval Matrix" vào chunk đầu của tài liệu quy trình, BM25 dễ dàng quét thẳng keyword này, kéo nguyên văn chunk quy chế phê duyệt lên vị trí Rank 1.
- Thuật toán RRF đã làm tốt phần việc còn lại: Đẩy score của document có keyword "Approval Matrix" lên top, giúp quá trình Generation trả lời đúng chính xác quy trình xét duyệt.

---

## 5. Nếu có thêm thời gian, tôi sẽ làm gì? (50-100 từ)

> 1-2 cải tiến cụ thể bạn muốn thử.
Nếu thời gian cho phép, tôi sẽ đẩy thêm cải tiến ở **Semantic Chunking**. Hiện tại tôi chỉ mới cắt cứng theo thẻ title. Thực tế, các tài liệu Policy còn bị phân mảnh theo các Bullets đứt quãng. Tôi sẽ thử triển khai cách gom chunk theo Sliding Window (Chunk Overlap) hoặc xử lý nâng cao với Cross-Encoder Rerank sau bước Hybrid để siết chặt top-k chunks gửi vào Prompt.
