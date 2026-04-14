"""
day09/lab/workers/retrieval.py — Retrieval Worker
Sprint 2: Implement full RAG with Semantic Splitting & ChromaDB.
Feature: Tracing, Auto-indexing, and Metadata Parsing.

Author: Nguyen Quoc Khanh [Khanh]
"""

import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import chromadb
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ─────────────────────────────────────────────
# Cấu hình & Contract
# ─────────────────────────────────────────────

WORKER_NAME = "retrieval_worker"
DEFAULT_TOP_K = int(os.getenv("RETRIEVAL_TOP_K", 5))

# ALIAS_MAP: Hỗ trợ tìm kiếm theo từ khóa cũ/tên khác (Tham khảo Day 8)
ALIAS_MAP = {
    "access_control_sop.txt": ["approval matrix", "quy trình cấp quyền", "access control"],
    "policy_refund_v4.txt": ["hoàn tiền", "refund policy", "trả hàng"],
    "sla_p1_2026.txt": ["escalation process", "cam kết SLA", "xử lý sự cố P1"]
}

# ─────────────────────────────────────────────
# Helper Functions (Metadata & Splitting)
# ─────────────────────────────────────────────

def parse_metadata(content: str) -> dict:
    """
    Extract metadata (Source, Department, Date) từ header của file .txt.
    """
    metadata = {
        "source": "unknown",
        "department": "unknown",
        "effective_date": "unknown"
    }
    
    # Metadata extraction pattern (Key: Value)
    meta_pattern = re.compile(r"^(Source|Department|Effective Date):\s*(.+)$", re.IGNORECASE)
    
    lines = content.strip().split("\n")
    for line in lines:
        match = meta_pattern.match(line)
        if match:
            key = match.group(1).lower().replace(" ", "_")
            metadata[key] = match.group(2).strip()
        elif line.startswith("==="):
            break
            
    return metadata


def split_into_chunks(content: str, base_meta: dict) -> List[Dict[str, Any]]:
    """
    Semantic split theo section headers === Section Name ===.
    """
    # Xoá phần header trước section đầu tiên
    first_section = re.search(r"===", content)
    if first_section:
        cleaned_content = content[first_section.start():].strip()
    else:
        cleaned_content = content.strip()

    # Split theo header === ... ===
    section_parts = re.split(r"(===\s*.+?\s*===)", cleaned_content)

    chunks = []
    current_section = "General"

    i = 0
    while i < len(section_parts):
        part = section_parts[i].strip()
        if not part:
            i += 1
            continue

        if re.match(r"===\s*.+?\s*===", part):
            current_section = part.strip("= ").strip()
            i += 1
            if i < len(section_parts):
                section_content = section_parts[i].strip()
                if section_content:
                    chunks.append({
                        "text": section_content,
                        "metadata": {**base_meta, "section": current_section}
                    })
                i += 1
        else:
            i += 1

    # Apply ALIAS_MAP vào chunk đầu tiên
    source_filename = base_meta.get("source", "").split("/")[-1]
    if source_filename in ALIAS_MAP and chunks:
        alias_text = f"[Keywords: {', '.join(ALIAS_MAP[source_filename])}]\n"
        chunks[0]["text"] = alias_text + chunks[0]["text"]

    return chunks

# ─────────────────────────────────────────────
# Embedding & Collection Helpers
# ─────────────────────────────────────────────

def _get_embedding_fn():
    """
    Khởi tạo OpenAI Embedding function từ cấu hình .env.
    Dùng LangChain OpenAIEmbeddings hoặc fallback Sentence Transformers.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key and not api_key.startswith("sk-..."):
        from langchain_openai import OpenAIEmbeddings
        return OpenAIEmbeddings(
            model=os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"),
            openai_api_key=api_key
        )
    
    # Fallback to Sentence Transformers if OpenAI key is missing
    try:
        from langchain_community.embeddings import SentenceTransformerEmbeddings
        return SentenceTransformerEmbeddings(model_name="all-MiniLM-L6-v2")
    except ImportError:
        # Final fallback: direct SentenceTransformer
        try:
            from sentence_transformers import SentenceTransformer
            model = SentenceTransformer("all-MiniLM-L6-v2")
            class SimpleEmbedder:
                def embed_documents(self, texts): return model.encode(texts).tolist()
                def embed_query(self, text): return model.encode([text])[0].tolist()
            return SimpleEmbedder()
        except ImportError:
            raise ValueError("Yêu cầu OPENAI_API_KEY hoặc cài đặt sentence-transformers.")


def _get_collection():
    """
    Kết nối ChromaDB collection.
    """
    db_path = os.getenv("CHROMA_DB_PATH", "./day09/lab/chroma_db")
    client = chromadb.PersistentClient(path=db_path)
    return client.get_or_create_collection(
        name=os.getenv("CHROMA_COLLECTION", "day09_docs"),
        metadata={"hnsw:space": "cosine"}
    )


def _build_index() -> None:
    """
    Xóa collection cũ và build index mới từ data/docs/ dùng Semantic Splitting.
    """
    print("🚀 Bắt đầu quá trình Indexing cho Day 09...")
    collection = _get_collection()
    
    # 1. Clear collection (Xóa dữ liệu cũ)
    doc_count = collection.count()
    if doc_count > 0:
        print(f"🗑️ Đang xóa {doc_count} bản ghi cũ...")
        # Lấy tất cả IDs và xóa
        all_data = collection.get()
        if all_data["ids"]:
            collection.delete(ids=all_data["ids"])

    # 2. Load và xử lý tài liệu
    # Xác định docs_dir tương đối so với vị trí file retrieval.py
    base_dir = Path(__file__).parent.parent.resolve()
    docs_dir = base_dir / "data" / "docs"
    
    if not docs_dir.exists():
        print(f"❌ Không tìm thấy thư mục tài liệu: {docs_dir}")
        return

    all_chunks = []
    for file_path in docs_dir.glob("*.txt"):
        content = file_path.read_text(encoding="utf-8")
        meta = parse_metadata(content)
        meta["source"] = file_path.name # Đảm bảo source là tên file
        
        chunks = split_into_chunks(content, meta)
        all_chunks.extend(chunks)
        print(f"  - {file_path.name}: {len(chunks)} chunks")

    if not all_chunks:
        print("⚠️ Không có dữ liệu để index.")
        return

    # 3. Embedding và Lưu trữ
    embed_fn = _get_embedding_fn()
    
    texts = [c["text"] for c in all_chunks]
    metadatas = [c["metadata"] for c in all_chunks]
    ids = [f"id_{i}" for i in range(len(all_chunks))]
    
    # Tính toán embeddings
    embeddings = embed_fn.embed_documents(texts)
    
    collection.add(
        ids=ids,
        embeddings=embeddings,
        metadatas=metadatas,
        documents=texts
    )
    
    print(f"✅ Đã index thành công {len(all_chunks)} chunks vào ChromaDB.")

# ─────────────────────────────────────────────
# Search & Worker Logic
# ─────────────────────────────────────────────

def search_chromadb(query: str, top_k: int = DEFAULT_TOP_K) -> List[Dict[str, Any]]:
    """
    Thực hiện tìm kiếm ngữ nghĩa. Tự động build index nếu cần.
    """
    collection = _get_collection()
    
    if collection.count() == 0:
        _build_index()
        
    embed_fn = _get_embedding_fn()
    query_vector = embed_fn.embed_query(query)
    
    results = collection.query(
        query_embeddings=[query_vector],
        n_results=top_k,
        include=["documents", "metadatas", "distances"]
    )
    
    formatted_chunks = []
    if results["documents"]:
        for i in range(len(results["documents"][0])):
            dist = results["distances"][0][i]
            formatted_chunks.append({
                "text": results["documents"][0][i],
                "source": results["metadatas"][0][i].get("source", "unknown"),
                "section": results["metadatas"][0][i].get("section", "General"),
                "score": round(1 - dist, 4), # Cosine similarity
                "metadata": results["metadatas"][0][i]
            })
            
    return formatted_chunks

# Alias cho retrieve_dense
retrieve_dense = search_chromadb


def run(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Retrieval Worker — Entry point gọi từ graph.
    """
    task: str = state.get("task", "")
    top_k: int = state.get("retrieval_top_k", DEFAULT_TOP_K)
    start_time = datetime.now()

    state.setdefault("workers_called", [])
    state.setdefault("history", [])
    state["workers_called"].append(WORKER_NAME)

    worker_io = {
        "worker": WORKER_NAME,
        "input": {"task": task, "top_k": top_k},
        "output": None,
        "timestamp": start_time.isoformat(),
    }

    try:
        chunks = search_chromadb(task, top_k=top_k)
        sources = list({c["source"] for c in chunks})

        state["retrieved_chunks"] = chunks
        state["retrieved_sources"] = sources

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

    worker_io["latency_ms"] = int((datetime.now() - start_time).total_seconds() * 1000)
    
    if "worker_io_log" not in state or not isinstance(state["worker_io_log"], list):
        state["worker_io_log"] = []
    state["worker_io_log"].append(worker_io)

    return state


if __name__ == "__main__":
    # Test độc lập
    print("=" * 50)
    print("Retrieval Worker — Standalone Test (Sprint 2 Full RAG)")
    print("=" * 50)

    # Thử nghiệm với query cụ thể giúp Khánh verify báo cáo
    test_queries = [
        "SLA ticket P1 là bao lâu?",
        "Khi nào thì một ticket P1 được coi là quá hạn?",
        "Tần suất cập nhật trạng thái của ticket P1?"
    ]

    for query in test_queries:
        print(f"\n▶ Query: {query}")
        result = run({"task": query, "worker_io_log": []})
        chunks = result.get("retrieved_chunks", [])
        print(f"  Retrieved: {len(chunks)} chunks")
        for i, c in enumerate(chunks[:2], 1):
             print(f"    [{i}] ({c['score']:.4f}) {c['source']} > {c['section']}: {c['text'][:100]}...")
        
    print("\n✅ retrieval_worker Sprint 2 integration done.")
