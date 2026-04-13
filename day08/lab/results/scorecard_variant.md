# Scorecard Variant — Hybrid Retrieval (Sprint 3)

**Date:** 2026-04-13  
**Variant:** `retrieval_mode = "hybrid"` (Dense + BM25S + RRF k=60)  
**Test set:** `data/test_questions.json` (10 câu mẫu)

---

## Retrieval Results

| ID | Câu hỏi (tóm tắt) | Dense | Hybrid |
|----|-------------------|-------|--------|
| q01 | SLA ticket P1 | HIT ✅ | HIT ✅ |
| q02 | Hoàn tiền bao nhiêu ngày | HIT ✅ | HIT ✅ |
| q03 | Phê duyệt Level 3 | HIT ✅ | HIT ✅ |
| q04 | Sản phẩm kỹ thuật số hoàn tiền | HIT ✅ | HIT ✅ |
| q05 | Tài khoản bị khóa sau mấy lần | HIT ✅ | HIT ✅ |
| q06 | Escalation P1 | HIT ✅ | HIT ✅ |
| q07 | Approval Matrix là tài liệu nào | HIT ✅ | HIT ✅ |
| q08 | Remote tối đa mấy ngày/tuần | HIT ✅ | HIT ✅ |
| q09 | ERR-403-AUTH (abstain) | ABSTAIN ✅ | ABSTAIN ✅ |
| q10 | Hoàn tiền VIP khác không | HIT ✅ | HIT ✅ |

## Summary

| Metric | Baseline (Dense) | Variant (Hybrid) | Delta |
|--------|-----------------|-----------------|-------|
| HIT | 9/9 | 9/9 | 0 |
| MISS | 0/9 | 0/9 | 0 |
| Abstain Accuracy | 1/1 | 1/1 | 0 |
| **Context Recall** | **100%** | **100%** | **0** |

## Config

```
# Baseline
retrieval_mode = "dense"
top_k_search   = 10
top_k_select   = 3
use_rerank     = False

# Variant 1 (chỉ đổi 1 biến)
retrieval_mode = "hybrid"
dense_weight   = 0.6
sparse_weight  = 0.4
RRF_K          = 60
```

## Analysis

- **q07** (alias query: "Approval Matrix") là câu hưởng lợi nhất từ Hybrid: BM25S bắt được keyword alias đã inject vào chunk đầu tiên, Dense có thể bỏ lỡ nếu embedding space không gần.
- **q09** (ERR-403-AUTH): cả hai mode đều abstain đúng — không có chunk nào vượt threshold.
- Hybrid không làm kém bất kỳ câu nào so với Dense.

## Conclusion

Hybrid được chọn làm mode mặc định vì:
1. Context Recall không giảm (100% → 100%)
2. Bền vững hơn với alias/keyword query (q07)
3. Chi phí tăng nhỏ (thêm BM25S lookup ~ms) so với lợi ích về độ tin cậy
