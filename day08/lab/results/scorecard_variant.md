# Scorecard Variant — Hybrid Retrieval (Sprint 3)

**Date:** 2026-04-13  
**Variant:** `retrieval_mode = "hybrid"` (Dense + BM25S + RRF k=60) + LLM rerank  
**Test set:** `data/test_questions.json` (10 câu mẫu)  
**Judge:** `gpt-4o-mini` LLM-as-Judge

---

## Per-Question Results

| ID | Category | Faithful | Relevant | Recall | Complete | Config |
|----|----------|----------|----------|--------|----------|--------|
| q01 | SLA | 5 | 5 | 5 | 4 | baseline_dense |
| q02 | Refund | 5 | 5 | 5 | 5 | baseline_dense |
| q03 | Access Control | 5 | 5 | 5 | 5 | baseline_dense |
| q04 | Refund | 5 | 5 | 5 | 5 | baseline_dense |
| q05 | IT Helpdesk | 5 | 5 | 5 | 5 | baseline_dense |
| q06 | SLA | 5 | 5 | 5 | 4 | baseline_dense |
| q07 | Access Control | 5 | 5 | 5 | 4 | baseline_dense |
| q08 | HR Policy | 5 | 5 | 5 | 5 | baseline_dense |
| q09 | Insufficient Context | 1 | 1 | 3 | 2 | baseline_dense |
| q10 | Refund | 1 | 1 | 5 | 1 | baseline_dense |
| q01 | SLA | 5 | 5 | 5 | 5 | variant_hybrid |
| q02 | Refund | 5 | 5 | 5 | 5 | variant_hybrid |
| q03 | Access Control | 5 | 5 | 5 | 5 | variant_hybrid |
| q04 | Refund | 5 | 5 | 5 | 5 | variant_hybrid |
| q05 | IT Helpdesk | 5 | 5 | 5 | 5 | variant_hybrid |
| q06 | SLA | 5 | 5 | 5 | 5 | variant_hybrid |
| q07 | Access Control | 5 | 5 | 5 | 4 | variant_hybrid |
| q08 | HR Policy | 5 | 5 | 5 | 5 | variant_hybrid |
| q09 | Insufficient Context | 5 | 1 | 3 | 2 | variant_hybrid |
| q10 | Refund | 5 | 1 | 5 | 1 | variant_hybrid |

## A/B Summary

| Metric | Baseline (Dense) | Variant (Hybrid) | Delta |
|--------|-----------------|-----------------|-------|
| Faithfulness | 4.20/5 | **5.00/5** | **+0.80** ✅ |
| Answer Relevance | 4.20/5 | 4.20/5 | 0 |
| Context Recall | 4.80/5 | 4.80/5 | 0 |
| Completeness | 4.00/5 | **4.20/5** | **+0.20** ✅ |

## Config

```
# Baseline
retrieval_mode = "dense"
top_k_search   = 10  (TOP_K_RETRIEVAL)
top_k_select   = 3   (TOP_K_RERANK)
use_rerank     = False

# Variant (chỉ đổi 2 biến)
retrieval_mode = "hybrid"   # Dense + BM25S + RRF k=60
use_rerank     = True       # LLM-as-reranker (gpt-4o-mini)
```

## Key Findings

- **Faithfulness +0.80**: Cải thiện lớn nhất ở abstain cases (q09, q10). Hybrid xử lý "không có thông tin" đúng hơn — judge xác nhận abstain là faithful thay vì chấm thấp.
- **Completeness +0.20**: q01, q06 — LLM rerank sắp xếp chunks cross-section đúng thứ tự ưu tiên, answer đầy đủ hơn.
- **q07 (alias query)**: Cả hai đều HIT (4/5 completeness) — BM25S bắt alias inject đúng.
- **Relevance không đổi**: q09/q10 abstain đúng nhưng judge vẫn chấm Relevance=1 vì answer không giải thích thêm.
