# Báo Cáo Cá Nhân — Lab Day 08: RAG Pipeline

**Họ và tên:** Lê Công Thành  
**Vai trò trong nhóm:** Eval Owner (pair) — Sprint 2, 3, 4  
**Ngày nộp:** 2026-04-13  

---

## 1. Tôi đã làm gì trong lab này?

Trong lab này tôi phụ trách phần **evaluation pipeline** với vai trò Eval Owner (pair cùng Phan Văn Tấn). Cụ thể:

**Sprint 2:** Implement hai hàm trong `eval.py` — `compute_ragas_scores()` tích hợp RAGAS framework để tính 4 metrics tự động (Faithfulness, Answer Relevancy, Context Precision, Context Recall qua `Dataset.from_dict()`), và `compute_abstain_accuracy()` để đo tỷ lệ pipeline abstain đúng trên các câu hỏi không có dữ liệu trong docs (expected_sources rỗng). Commit: `[Thanh][S2] RAGAS integration + abstain_accuracy metric`.

**Sprint 3:** Implement `save_grading_log()` — hàm export kết quả ra `logs/grading_run.json` đúng format bắt buộc theo SCORING.md (JSON array, mỗi entry có đủ `id`, `question`, `answer`, `sources`, `chunks_retrieved`, `retrieval_mode`, `timestamp`). Thêm `run_grading_eval()` để orchestrate toàn bộ grading run lúc 17:00 bằng một lệnh `python eval.py --grading`. Viết `results/scorecard_variant.md` với so sánh Dense vs Hybrid. Commit: `[Thanh][S3] scorecard_variant.md + grading_run formatter`.

Công việc của tôi kết nối trực tiếp với Tấn (Baseline runner) ở đầu vào (`run_scorecard()`) và với Nhật (Tech Lead) ở đầu ra — `grading_run.json` là file Nhật dùng để push lúc 17:00.

---

## 2. Điều tôi hiểu rõ hơn sau lab này

**Faithfulness vs Answer Relevancy là hai metric đo hai thứ hoàn toàn khác nhau** — và quan hệ giữa chúng không phải lúc nào cũng thuận chiều.

Trước lab tôi nghĩ nếu pipeline trả lời đúng câu hỏi (Relevancy cao) thì chắc chắn faithful. Thực tế ngược lại: **q09 và q10 là abstain cases** — pipeline trả lời "Tôi không tìm thấy thông tin này trong tài liệu." Câu này Faithfulness = 5/5 (hoàn toàn grounded — không bịa gì) nhưng Answer Relevancy = 1/5 (không trực tiếp trả lời câu hỏi). LLM-as-Judge đánh giá thấp relevancy vì câu hỏi chưa được giải đáp.

Điều này dạy tôi rằng **abstain là trade-off có chủ ý**: hy sinh relevancy để đổi lấy faithfulness và tránh hallucination. Đây là quyết định đúng với RAG pipeline trong domain chính sách nội bộ — sai một chữ số về SLA hay policy có thể gây hậu quả thực tế.

**RAGAS không phải magic** — nó cần đúng wrapper API mới hoạt động. Chỉ thay đúng `deepcopy(metric)` → `Faithfulness()` (instantiate class mới) mới hết lỗi `cannot pickle module object`.

---

## 3. Điều tôi ngạc nhiên hoặc gặp khó khăn

Khó khăn lớn nhất là **Hybrid mode abstain toàn bộ** dù pipeline đã retrieve đúng chunks. Nguyên nhân tôi không ngờ tới: RRF score (`dense_weight / (60 + rank)`) tối đa chỉ ~**0.017** — luôn thấp hơn threshold 0.20 — nên toàn bộ bị filter trước khi đến generate. Giả thuyết ban đầu của tôi là lỗi BM25 path, nhưng sau khi fix path thì vẫn abstain. Phải trace từng bước mới phát hiện threshold không scale-invariant: nó chỉ có nghĩa với L2-derived similarity score của Dense, không dùng được cho RRF score.

Fix: phân nhánh threshold theo `retrieval_mode` — Dense mới lọc bằng threshold, Hybrid/Sparse trust ranking và lấy toàn bộ top-k.

Một vấn đề khác: Dense dùng `1.0 - distance` để tính score, nhưng Chroma trả L2 distance (nằm trong ~[0, 2]), nên score ra âm → cũng bị abstain hết. Fix: `1.0 / (1.0 + distance)` — giữ nguyên thứ tự, luôn dương, nằm trong (0, 1].

---

## 4. Phân tích một câu hỏi trong scorecard

**Câu hỏi được chọn:** `q01` — "SLA xử lý ticket P1 là bao lâu?" *(câu multi-detail, phản ánh khả năng tổng hợp)*

**Phân tích:**

Câu này yêu cầu 4 thông tin từ cùng một tài liệu (`support/sla-p1-2026.pdf`): phản hồi ban đầu (15 phút), resolution (4 giờ), escalation (10 phút), và update stakeholder (30 phút). Đây là **multi-detail retrieval** trong một document, không phải multi-document.

*Baseline Dense:* retrieves đúng source nhưng đôi khi thiếu section escalation (Completeness = 4/5). Nguyên nhân: chunking theo section `===` cắt "Escalation Policy" thành chunk riêng — Dense embedding của câu hỏi ngắn "SLA P1 là bao lâu?" không đủ semantic để kéo chunk escalation về trong top-3.

*Variant Hybrid:* Completeness = 5/5 trên q01. BM25 bắt được keyword "escalation" và "P1" trong hai chunks khác nhau, RRF merge đưa cả hai vào top-3 → LLM có đủ context để trả lời đầy đủ. Đây là **bằng chứng rõ nhất cho lợi thế của Hybrid** trên multi-detail queries: keyword "escalation" không xuất hiện trong câu hỏi gốc nhưng BM25 match được qua corpus.

Grading log thực tế (q01 trong `grading_run_test_questions.json`): answer đầy đủ 4 điểm, retrieval_mode = hybrid, chunks_retrieved = 3. Source có lẫn `policy/refund-v4.pdf` — đây là contamination cần cải thiện.

---

## 5. Nếu có thêm thời gian, tôi sẽ làm gì?

**Cải tiến 1 — Source deduplication sau generate:** Hiện tại `sources` field trong grading log lấy toàn bộ chunk sources bao gồm cả chunks không được cite trong answer. Scorecard cho thấy q01, q05, q06 đều có sources nhiễu (ví dụ `policy/refund-v4.pdf` trong q01). Tôi sẽ parse citation markers `[1]`, `[2]` trong answer text để chỉ giữ sources thực sự được dùng — giảm noise, tăng điểm grading.

**Cải tiến 2 — Abstain nên trả sources rỗng:** q09 (ERR-403-AUTH) abstain đúng nhưng `sources` vẫn chứa 3 files không liên quan. Theo SCORING.md, grader sẽ check sources field. Fix: khi `has_context=False`, force `sources=[]` trong output thay vì giữ lại retrieved sources.

---
