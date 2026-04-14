"""
day09/lab/workers/retrieval.py — Retrieval Worker
Sprint 1: Setup & Skeleton - Định nghĩa cấu trúc worker và tracing logic.
Author: Nguyen Quoc Khanh [Khanh]
"""

import os
from datetime import datetime
from typing import Any, Dict, List, Optional


def _get_embedding_fn():
    """
    Helper function để lấy embedding function (Sprint 2 implementation).
    """
    # Sprint 2: Implement OpenAI or Sentence Transformers here
    pass


def _build_index() -> None:
    """
    Stub function: Xây dựng index từ tài liệu (Sprint 2 implementation).
    """
    pass


def search_chromadb(query: str, top_k: int = 5) -> List[Dict[str, Any]]:
    """
    Stub function: Tìm kiếm chunks từ ChromaDB.
    Trả về list of {text, source, section, score}.
    """
    # Sprint 2: Implement real connection to ChromaDB
    return []


def run(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Retrieval Worker — Entry point gọi từ graph.
    Tuân thủ contract trong worker_contracts.yaml.
    
    Input: state["task"]
    Output: state["retrieved_chunks"], state["worker_io_log"]
    """
    task: str = state.get("task", "")
    start_time = datetime.now()

    # Sprint 1: Thực hiện gọi stub search
    chunks = search_chromadb(task, top_k=5)

    # Ghi worker_io_log — BẮT BUỘC để trace hoạt động đúng theo contract
    log_entry = {
        "worker": "retrieval_worker",
        "input": {"task": task},
        "output": {
            "num_chunks": len(chunks),
            "sources": list({c.get("source", "unknown") for c in chunks})
        },
        "timestamp": start_time.isoformat(),
        "latency_ms": int((datetime.now() - start_time).total_seconds() * 1000)
    }

    # Cập nhật state theo contract
    state["retrieved_chunks"] = chunks
    
    # Đảm bảo worker_io_log là một list và append kết quả mới vào
    if "worker_io_log" not in state or not isinstance(state["worker_io_log"], list):
        state["worker_io_log"] = []
    
    state["worker_io_log"].append(log_entry)

    return state


if __name__ == "__main__":
    # Test độc lập (Standalone test block)
    print("=" * 50)
    print("Retrieval Worker — Sprint 1 Skeleton Test")
    print("=" * 50)

    test_state = {"task": "SLA ticket P1 là bao lâu?", "worker_io_log": []}
    result = run(test_state)

    print(f"Task: {result['task']}")
    print(f"Retrieved Chunks Count: {len(result['retrieved_chunks'])}")
    print(f"Log Entry: {result['worker_io_log'][-1]}")
    print("\n✅ Sprint 1 Skeleton verified.")
