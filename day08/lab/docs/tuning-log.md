# Tuning Log — RAG Pipeline (Day 08 Lab)

> Template: Ghi lại mỗi thay đổi và kết quả quan sát được.
> A/B Rule: Chỉ đổi MỘT biến mỗi lần.

---

## Baseline (Sprint 2)

**Ngày:** ___________  
**Config:**
```
retrieval_mode = "dense"
chunking_strategy = "semantic split"
top_k_search = 10
top_k_select = 3
use_rerank = False
threshold = 0.35
llm_model = "gpt-4o-mini"

**System Prompt:** "Chỉ trả lời dựa trên CONTEXT được cung cấp. Nếu không tìm thấy thông tin → trả lời: 'Không tìm thấy thông tin...'. Luôn trích dẫn nguồn."
```

**Scorecard Baseline:**
| Metric | Average Score |
|--------|--------------|
| Faithfulness | 1.00 /5 |
| Answer Relevance | 3.00 /5 |
| Context Recall | 0.50 /5 |
| Completeness | 3.00 /5 |

**Câu hỏi yếu nhất (điểm thấp):**
*   Tất cả các câu hỏi (đặc biệt các câu q01, q02, q03) đều có phần Recall = 0.
*   Hiện tượng: "No retrieved chunks, answer likely not faithful", có nghĩa là hệ thống Dense baseline ở mức khởi điểm không trả về đúng/đủ chunk cho các tài liệu tương ứng, dẫn tới Faithfulness thấp chạm mốc 1.0. (Riêng q09 về Insufficient Context có recall 5 vì vốn dĩ không có expected_sources).

**Giả thuyết nguyên nhân (Error Tree):**
- [ ] Indexing: Chunking cắt giữa điều khoản
- [ ] Indexing: Metadata thiếu effective_date
- [x] Retrieval: Dense bỏ lỡ exact keyword / alias (Do tính chất của dữ liệu CS & IT)
- [x] Retrieval: Không retrieve được chunk nào (Do pipeline Dense đang chưa setup đầy đủ hoặc vector query không khớp vector metadata)
- [ ] Generation: Prompt không đủ grounding
- [ ] Generation: Context quá dài → lost in the middle

---

## Variant 1 (Sprint 3)

**Ngày:** 2026-04-13  
**Biến thay đổi:** `retrieval_mode`: `"dense"` → `"hybrid"` (Dense + BM25S + RRF k=60)  
**Lý do chọn biến này:**
> Baseline Dense bỏ lỡ các query dùng keyword chính xác và alias. Cụ thể:
> - **ext08** ("Approval Matrix for System Access") — Dense không bắt được alias của `access-control-sop.md` vì tên tài liệu đã đổi.
> - **ext01, ext11** (P1 SLA) — query ngắn, keyword "P1" không đủ ngữ nghĩa cho embedding.
> - Corpus lẫn lộn: ngôn ngữ tự nhiên (policy HR) + tên riêng/mã kỹ thuật (ticket P1, ERR-403, Level 3).
> → Hybrid giữ được cả Dense (semantic) lẫn BM25 (keyword exact), RRF tổng hợp rank từ cả hai.

**Config thay đổi:**
```
retrieval_mode = "hybrid"    # thay vì "dense"
dense_weight   = 0.6
sparse_weight  = 0.4
RRF_K          = 60
# Các tham số còn lại giữ nguyên như baseline
top_k_search   = 10
top_k_select   = 3
use_rerank     = False
```

**Kết quả test retrieval (test_questions.json — 10 câu mẫu):**

| ID | Câu hỏi (tóm tắt) | Dense | Hybrid | Ghi chú |
|----|-------------------|-------|--------|---------|
| q01 | SLA ticket P1 | HIT ✅ | HIT ✅ | |
| q02 | Hoàn tiền bao nhiêu ngày | HIT ✅ | HIT ✅ | |
| q03 | Phê duyệt Level 3 | HIT ✅ | HIT ✅ | |
| q04 | Sản phẩm kỹ thuật số hoàn tiền | HIT ✅ | HIT ✅ | |
| q05 | Tài khoản bị khóa sau mấy lần | HIT ✅ | HIT ✅ | |
| q06 | Escalation P1 | HIT ✅ | HIT ✅ | |
| q07 | Approval Matrix là tài liệu nào | HIT ✅ | HIT ✅ | BM25 bắt alias → Hybrid ổn định hơn |
| q08 | Remote tối đa mấy ngày/tuần | HIT ✅ | HIT ✅ | |
| q09 | ERR-403-AUTH | ABSTAIN ✅ | ABSTAIN ✅ | Không có trong docs — abstain đúng |
| q10 | Hoàn tiền VIP khác không | HIT ✅ | HIT ✅ | |

| Mode | HIT | MISS | ABSTAIN | Context Recall |
|------|-----|------|---------|----------------|
| Dense (baseline) | 9 | 0 | 1 | 100% |
| Hybrid (variant) | 9 | 0 | 1 | 100% |

**Scorecard Variant 1:**
| Metric | Baseline (Dense) | Variant 1 (Hybrid) | Delta |
|--------|------------------|--------------------|-------|
| Context Recall | 100% (9/9) | 100% (9/9) | 0 |
| Alias Query (q07) | HIT (Dense may miss) | HIT (BM25 dominant) | ✅ ổn định hơn |
| Abstain chính xác | 1/1 (q09) | 1/1 (q09) | 0 |

**Nhận xét:**
- Hybrid không kém hơn Dense ở bất kỳ câu nào trong 10 câu mẫu.
- **q07** ("Approval Matrix") là câu rủi ro nhất với Dense: embedding của "Approval Matrix" có thể không khớp tốt với "Access Control SOP". BM25S bắt được vì alias đã được inject vào `page_content` chunk đầu tiên.
- Dense hoạt động tốt vì corpus tương đối nhỏ (5 file, ~30 chunks). Ở corpus lớn hơn, khoảng cách Dense vs Hybrid sẽ rõ hơn.

**Kết luận:**
> Chọn **Hybrid** làm mode mặc định. Context Recall giữ nguyên 100%, Hybrid bền vững hơn với alias query (q07) — đặc biệt quan trọng khi tên tài liệu thay đổi nhưng người dùng vẫn dùng tên cũ.

---

## Variant 2 (nếu có thời gian)

**Biến thay đổi:** ___________  
**Config:**
```
# TODO
```

**Scorecard Variant 2:**
| Metric | Baseline | Variant 1 | Variant 2 | Best |
|--------|----------|-----------|-----------|------|
| Faithfulness | ? | ? | ? | ? |
| Answer Relevance | ? | ? | ? | ? |
| Context Recall | ? | ? | ? | ? |
| Completeness | ? | ? | ? | ? |

---

## Tóm tắt học được

> TODO (Sprint 4): Điền sau khi hoàn thành evaluation.

1. **Lỗi phổ biến nhất trong pipeline này là gì?**
   > _____________

2. **Biến nào có tác động lớn nhất tới chất lượng?**
   > _____________

3. **Nếu có thêm 1 giờ, nhóm sẽ thử gì tiếp theo?**
   > _____________
