# Retrieval Worker Technical Specs for Group Report

**Lead:** Nguyễn Quốc Khánh

## Core Capabilities
- **Search Engine:** ChromaDB with `text-embedding-3-small` (OpenAI).
- **Indexing Strategy:** 
    - Auto-indexing logic in `_build_index()`. 
    - Clears old collection and re-indexes from `data/docs/*.txt` on first run or empty db.
- **Chunking Strategy:** 
    - **Semantic Splitting**: Regex-based partitioning via section headers (`=== Section Name ===`).
    - Ensures context integrity for policies and SLAs.
- **Search Logic:**
    - Default `top_k=5` (Tuned in Sprint 3 for multi-hop recall).
    - Uses `ALIAS_MAP` for keyword augmentation (e.g., "SLA" -> "cam kết SLA", "escalation process").

## Key Metrics (Lab Internal)
- **Indexing Speed:** ~150ms per document.
- **Retrieval Latency:** ~500-600ms per query.
- **Recall @ 5:** 100% on 15 test questions (verified through manual trace analysis).

## Integration Details
- **Contract Compliance:** Adheres to `worker_contracts.yaml`.
- **Trace Support:** Populates `retrieved_chunks`, `retrieved_sources`, and `worker_io_log` for full system transparency.
