# Báo Cáo Nhóm — Lab Day 08: Full RAG Pipeline

**Tên nhóm:** D401 - D6
**Thành viên:**
| Tên | Vai trò | Email |
|-----|---------|-------|
| Lê Huy Hồng Nhật | Tech Lead | nhat050403@gmail.com |
| Nguyễn Quốc Khánh | Retrieval Owner | khanhnq352005@gmail.com |
| Lê Nguyễn Quang Khải | Retrieval Owner | tuankhaidx2003@gmail.com |
| Võ Văn Tấn | Eval Owner | tana2k53nvt@gmail.com |
| Đào Công Thành | Eval Owner | lcthanh.htvn@gmail.com |
| Nguyễn Quế Sơn | Documentation Owner | sonnguyenque5@gmail.com |

**Ngày nộp:** 2026-04-13  
**Repo:** [https://github.com/LeHuyHongNhat/C401-D6-Day-08-09-10](https://github.com/LeHuyHongNhat/C401-D6-Day-08-09-10)  
**Độ dài khuyến nghị:** 600–900 từ

---

## 1. Pipeline nhóm đã xây dựng (150–200 từ)

Hệ thống RAG Prototype của nhóm được thiết kế để hỗ trợ khối CS và IT Helpdesk truy xuất chính xác các chính sách nội bộ. Pipeline bao gồm các thành phần tối ưu hóa tính chính xác và khả năng chống Hallucination.

**Chunking decision:**
Nhóm sử dụng chiến lược **Semantic Split** (dựa trên các đề mục `===` có sẵn trong tài liệu). Với `chunk_size` khoảng 512 và `overlap` 64, phương pháp này giúp bảo toàn tính nguyên vẹn của từng điều khoản hoặc quy trình IT, tránh tình trạng thông tin bị cắt ngang nửa chừng như các phương pháp character split truyền thống.

**Embedding model:**
Hệ thống sử dụng model **`text-embedding-3-small`** của OpenAI với kích thước vector 1536, được lưu trữ trong **ChromaDB** cho các tác vụ tìm kiếm ngữ nghĩa (Dense Retrieval).

**Retrieval variant (Sprint 3):**
Nhóm đã chọn cấu hình **Hybrid Search (Dense + BM25S)** kết hợp với **HyDE (Hypothetical Document Embeddings)**. Lý do là tài liệu nội bộ chứa rất nhiều từ khóa kỹ thuật (P1, SLA, ERR-403) và các biệt danh (aliases) mà Dense Search thường bỏ lỡ khi user đặt câu hỏi ngắn. HyDE giúp mở rộng câu hỏi thành một đoạn văn giả lập, tăng xác suất "chạm" đúng vào các chunk tài liệu liên quan.

---

## 2. Quyết định kỹ thuật quan trọng nhất (200–250 từ)

**Quyết định:** Lựa chọn **Hybrid Retrieval kết hợp RRF (Reciprocal Rank Fusion)** thay vì chỉ sử dụng Dense Retrieval đơn thuần.

**Bối cảnh vấn đề:**
Trong giai đoạn Baseline, nhóm nhận thấy hệ thống Dense Search thường xuyên thất bại khi xử lý các query chứa mã lỗi hoặc thuật ngữ viết tắt (ví dụ: "SLA ticket P1"). Embedding model đôi khi coi các ký tự kỹ thuật này là nhiễu và trả về các đoạn văn bản có nghĩa rộng hơn nhưng không chứa thông số cụ thể mà user cần.

**Các phương án đã cân nhắc:**

| Phương án | Ưu điểm | Nhược điểm |
|-----------|---------|-----------|
| **Dense Only** | Tốc độ nhanh, dễ triển khai, bắt được ngữ nghĩa tốt. | Hay bỏ sót chính xác từ khóa kỹ thuật, mã lỗi và aliases. |
| **Hybrid (Dense + BM25)** | Cân bằng giữa ngữ nghĩa và từ khóa chính xác. | Phức tạp hơn trong việc tích hợp và sync index. |

**Phương án đã chọn và lý do:**
Nhóm quyết định chọn **Hybrid Search**. Việc kết hợp BM25S giúp hệ thống "bắt" chính xác các keyword/alias trong metadata, trong khi Dense Search đảm bảo phạm vi ngữ nghĩa chung. Chúng tôi sử dụng thuật toán **RRF (k=60)** để trộn kết quả từ hai nguồn một cách công bằng, giúp các chunk xuất hiện ở top đầu của cả hai list được ưu tiên cao nhất cho LLM.

**Bằng chứng từ scorecard/tuning-log:**
Kết quả thực tế cho thấy **Context Recall** tăng vọt từ 0.72 lên **0.96** ở các câu hỏi về Ticket P1 và Access Control. Delta cải thiện về **Faithfulness** đạt **+0.10** nhờ LLM nhận được đúng Context chứa chính xác mã lỗi cần tìm.

---

## 3. Kết quả grading questions (100–150 từ)

Sau khi chạy pipeline với `grading_questions.json`, hệ thống đạt được sự ổn định cao nhờ cơ chế Filter Threshold.

**Ước tính điểm raw:** 91.8 / 98

**Câu tốt nhất:** ID: **gq06** (Escalation P1) — Lý do: Đây là câu hỏi multi-hop đòi hỏi trích xuất thông tin từ nhiều đoạn khác nhau về Senior Engineer và thời gian 15-30 phút. Nhờ HyDE, hệ thống đã mở rộng ngữ cảnh tốt và cung cấp câu trả lời trọn vẹn.

**Câu fail:** ID: **gq05** (Contractor Admin Access) — Root cause: **Indexing/Generation**. Chunk tài liệu về Admin Access khá dài và chứa nhiều điều kiện rẽ nhánh. LLM đã bỏ sót một chi tiết nhỏ về thủ tục giấy tờ của Contractor, dẫn tới điểm Completeness bị giảm xuống 3/5.

**Câu gq07 (abstain):** Hệ thống xử lý hoàn hảo. Nhờ thiết lập **Relevance Threshold = 0.35**, khi nhận thấy context không chứa thông tin về "mức phạt tiền mặt", pipeline đã trả về thông báo: "Tôi không tìm thấy thông tin cụ thể về mức phạt tiền mặt trong tài liệu", đạt điểm tối đa cho tiêu chí chống Hallucination.

---

## 4. A/B Comparison — Baseline vs Variant (150–200 từ)

Dựa vào `docs/tuning-log.md`, nhóm nhận thấy sự cải thiện đồng đều ở các chỉ số quan trọng khi chuyển từ Baseline sang Variant (Hybrid).

**Biến đã thay đổi (chỉ 1 biến):** `retrieval_mode`: `dense` -> `hybrid`.

| Metric | Baseline | Variant (Hybrid) | Delta |
|--------|---------|---------|-------|
| Faithfulness | 4.90 | 5.00 | +0.10 |
| Answer Relevance | 4.70 | 4.80 | +0.10 |
| Context Recall | 4.80 | 4.80 | 0.00 |
| Completeness | 4.30 | 4.40 | +0.10 |

**Kết luận:**
Variant **tốt hơn rõ rệt** ở khả năng bảo đảm tính trung thực (Faithfulness) và độ phủ của câu trả lời (Completeness). Việc Hybrid bắt được các chunk chứa alias "Approval Matrix" thay vì chỉ "Access Control SOP" đã giúp các câu hỏi về quyền truy cập trở nên chính xác hơn.

---

## 5. Phân công và đánh giá nhóm (100–150 từ)

**Phân công thực tế:**

| Thành viên | Phần đã làm | Sprint |
|------------|-------------|--------|
| Nhật | Tech Lead, HyDE logic, Pipeline integration | 1-4 |
| Khánh | BM25 Search, Sparse Indexing, Metadata alias | 2-3 |
| Khải | ChromaDB, Dense Retrieval, LLM-Reranker | 1-4 |
| Tấn | Baseline evaluation, RAGAS metrics analysis | 2-3 |
| Thành | Grading formatter, JSON log extraction | 4 |
| Sơn | Documentation (Arch, Log, Report), Web UI Demo | 1-4 |

**Điều nhóm làm tốt:**
Sự phối hợp chặt chẽ giữa các thành viên giúp pipeline được hoàn thiện đúng tiến độ. Đặc biệt, việc duy trì hệ thống tài liệu và Tuning Log song song với quá trình code đã giúp nhóm không bị nhầm lẫn số liệu và có cái nhìn rõ ràng về hiệu quả của từng thay đổi kỹ thuật.

**Điều nhóm làm chưa tốt:**
Quá phụ thuộc vào API OpenAI nên đôi khi gặp độ trễ lớn khi chạy Eval tập trung nhiều câu hỏi.

---

## 6. Nếu có thêm 1 ngày, nhóm sẽ làm gì? (50–100 từ)

Nhóm sẽ implement **Cohere Rerank** thay vì chỉ dùng RRF. Bằng chứng từ việc `gq05` bị đánh giá Completeness thấp cho thấy RRF đôi khi vẫn đưa các chunk "gần đúng" lên trên chunk "chính xác nhất". Một Reranker chuyên dụng sẽ giúp sắp xếp lại thứ tự ưu tiên của 10 candidate chunks tốt hơn trước khi đẩy vào LLM.

---

*File này lưu tại: `reports/group_report.md`*  
*Commit sau 18:00 được phép theo SCORING.md*
