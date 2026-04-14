"""
day09/lab/workers/retrieval.py — Retrieval Worker
Sprint 1: Setup & Skeleton - Định nghĩa cấu trúc worker và tracing logic.
Sprint 2: Implement retrieval từ ChromaDB, trả về chunks + sources.

Author: Nguyen Quoc Khanh [Khanh] (Integrated with Tech Lead [Nhat] core)
"""

import os
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional

# ─────────────────────────────────────────────
# Worker Contract (xem contracts/worker_contracts.yaml)
# Input:  {"task": str}
# Output: {"retrieved_chunks": List[dict], "worker_io_log": List[dict]}
# ─────────────────────────────────────────────

WORKER_NAME = "retrieval_worker"
DEFAULT_TOP_K = 3


def _get_embedding_fn():
    """
    Trả về embedding function.
    TODO Sprint 1: Implement dùng OpenAI hoặc Sentence Transformers.
    """
    # Option A: Sentence Transformers (offline, không cần API key)
    try:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer("all-MiniLM-L6-v2")
        def embed(text: str) -> list:
            return model.encode([text])[0].tolist()
        return embed
    except ImportError:
        pass

    # Option B: OpenAI (cần API key)
    try:
        from openai import OpenAI
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        def embed(text: str) -> list:
            resp = client.embeddings.create(input=text, model="text-embedding-3-small")
            return resp.data[0].embedding
        return embed
    except ImportError:
        pass

    # Fallback: random embeddings cho test (KHÔNG dùng production)
    import random
    def embed(text: str) -> list:
        return [random.random() for _ in range(384)]
    print("⚠️  WARNING: Using random embeddings (test only). Install sentence-transformers.")
    return embed


def _get_collection():
    """
    Kết nối ChromaDB collection.
    TODO Sprint 2: Đảm bảo collection đã được build từ Step 3 trong README.
    """
    import chromadb
    client = chromadb.PersistentClient(path="./chroma_db")
    try:
        collection = client.get_collection("day09_docs")
    except Exception:
        # Auto-create nếu chưa có
        collection = client.get_or_create_collection(
            "day09_docs",
            metadata={"hnsw:space": "cosine"}
        )
        print(f"⚠️  Collection 'day09_docs' chưa có data. Chạy index script trong README trước.")
    return collection


def _build_index() -> None:
    """
    Stub function: Xây dựng index từ tài liệu (Sprint 2 implementation).
    """
    pass


def search_chromadb(query: str, top_k: int = DEFAULT_TOP_K) -> List[Dict[str, Any]]:
    """
    Dense retrieval: embed query → query ChromaDB → trả về top_k chunks.
    Alias cho retrieve_dense để khớp với requirement trong individual_tasks.md.
    """
    # TODO: Implement dense retrieval hoàn chỉnh trong Sprint 2
    embed = _get_embedding_fn()
    query_embedding = embed(query)

    try:
        collection = _get_collection()
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=["documents", "distances", "metadatas"]
        )

        chunks = []
        for i, doc in enumerate(results["documents"][0]):
            dist = results["distances"][0][i]
            meta = results["metadatas"][0][i]
            chunks.append({
                "text": doc,
                "source": meta.get("source", "unknown"),
                "score": round(1 - dist, 4),  # cosine similarity
                "metadata": meta,
            })
        return chunks

    except Exception as e:
        print(f"⚠️  ChromaDB query failed: {e}")
        # Fallback: return empty (abstain)
        return []

# Alias để giữ tương thích với template của Tech Lead
retrieve_dense = search_chromadb


def run(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Retrieval Worker — Entry point gọi từ graph.
    Tuân thủ contract trong worker_contracts.yaml.
    
    Input: state["task"]
    Output: state["retrieved_chunks"], state["worker_io_log"]
    """
    task: str = state.get("task", "")
    top_k: int = state.get("retrieval_top_k", DEFAULT_TOP_K)
    start_time = datetime.now()

    state.setdefault("workers_called", [])
    state.setdefault("history", [])
    state["workers_called"].append(WORKER_NAME)

    # Log worker IO (theo contract)
    worker_io = {
        "worker": WORKER_NAME,
        "input": {"task": task, "top_k": top_k},
        "output": None,
        "error": None,
        "timestamp": start_time.isoformat(),
    }

    try:
        # Sprint 1: Thực hiện gọi search
        chunks = search_chromadb(task, top_k=top_k)
        sources = list({c["source"] for c in chunks})

        state["retrieved_chunks"] = chunks
        state["retrieved_sources"] = sources  # Bổ sung so với contract

        worker_io["output"] = {
            "chunks_count": len(chunks),
            "sources": sources,
        }
        state["history"].append(
            f"[{WORKER_NAME}] retrieved {len(chunks)} chunks from {sources}"
        )

    except Exception as e:
        worker_io["error"] = {"code": "RETRIEVAL_FAILED", "reason": str(e)}
        state["retrieved_chunks"] = []
        state["retrieved_sources"] = []
        state["history"].append(f"[{WORKER_NAME}] ERROR: {e}")

    # Ghi worker_io_log — BẮT BUỘC theo contract
    worker_io["latency_ms"] = int((datetime.now() - start_time).total_seconds() * 1000)
    
    if "worker_io_log" not in state or not isinstance(state["worker_io_log"], list):
        state["worker_io_log"] = []
    state["worker_io_log"].append(worker_io)

    return state


if __name__ == "__main__":
    # Test độc lập
    print("=" * 50)
    print("Retrieval Worker — Standalone Test (Sprint 1 Skeleton)")
    print("=" * 50)

    test_queries = [
        "SLA ticket P1 là bao lâu?",
        "Điều kiện được hoàn tiền là gì?",
    ]

    for query in test_queries:
        print(f"\n▶ Query: {query}")
        result = run({"task": query, "worker_io_log": []})
        chunks = result.get("retrieved_chunks", [])
        print(f"  Retrieved: {len(chunks)} chunks")
        print(f"  Log Entry: {result['worker_io_log'][-1]}")

    print("\n✅ retrieval_worker test done.")
