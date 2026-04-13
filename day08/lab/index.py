# index.py
"""
Sprint 1: Xây dựng Index (Document Ingestion & Hybrid Indexing)
Mục tiêu: Đọc tài liệu từ data/docs/, parse metadata, split thành chunks, và build Chroma (Dense) + BM25S (Sparse) index.
"""

import os
import re
import pickle
from pathlib import Path
from typing import List, Dict, Any

import bm25s
from langchain.schema import Document
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from dotenv import load_dotenv

load_dotenv()

# --- CẤU HÌNH ---
DOCS_DIR = os.getenv("DOCS_DIR", "./data/docs")
CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "./data/chroma_db")
BM25_INDEX_DIR = os.getenv("BM25_INDEX_DIR", "./data/bm25_index")
EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")

ALIAS_MAP = {
    "it/access-control-sop.md": [
        "approval matrix for system access",
        "approval matrix",
        "access control sop",
    ]
}

def parse_metadata(content: str) -> dict:
    """
    Extract Source, Department, Effective Date, Access từ header của content.
    """
    # TODO: Implement parse_metadata
    pass

def split_into_chunks(content: str, base_meta: dict) -> list[Document]:
    """
    Semantic split theo section headers ===...===.
    Đầu ra là danh sách các object Document chứa chunks text và metadata.
    Nhớ xử lý Append alias vào metadata của chunk đầu tiên nếu file có trong ALIAS_MAP.
    """
    # TODO: Implement split_into_chunks
    pass

def build_vector_index(documents: list[Document]) -> Chroma:
    """
    Build hoặc load Chroma vector store từ danh sách Document.
    """
    # [Khai] build_vector_index
    embedding_fn = OpenAIEmbeddings(model=EMBEDDING_MODEL)
    os.makedirs(CHROMA_PERSIST_DIR, exist_ok=True)

    if Path(CHROMA_PERSIST_DIR).exists() and any(Path(CHROMA_PERSIST_DIR).iterdir()):
        print("[Chroma] Loading existing index...")
        return Chroma(persist_directory=CHROMA_PERSIST_DIR, embedding_function=embedding_fn)

    print(f"[Chroma] Building index from {len(documents)} chunks...")
    return Chroma.from_documents(
        documents=documents,
        embedding=embedding_fn,
        persist_directory=CHROMA_PERSIST_DIR,
    )

def build_bm25_index(documents: list[Document]) -> tuple:
    """
    Build BM25S sparse index và trả về (retriever, documents).
    Phải lưu (persist) ra thư mục BM25_INDEX_DIR.
    """
    # [Khai] build_bm25_index
    index_dir = Path(BM25_INDEX_DIR)
    index_dir.mkdir(parents=True, exist_ok=True)

    corpus = [doc.page_content for doc in documents]
    tokens = bm25s.tokenize(corpus, stopwords=None)

    retriever = bm25s.BM25()
    retriever.index(tokens)

    with open(index_dir / "bm25.pkl", "wb") as f:
        pickle.dump(retriever, f)
    with open(index_dir / "docs.pkl", "wb") as f:
        pickle.dump(documents, f)

    print(f"[BM25S] Index built: {len(documents)} chunks")
    return retriever, documents

def list_chunks(vectorstore):
    """
    In preview 10 chunks đầu tiên từ vector store để kiểm tra.
    """
    # TODO: Implement list_chunks
    pass

def build_all(docs_dir=DOCS_DIR):
    """
    Entry point Sprint 1: orchestrate toàn bộ quá trình xử lý:
    1. Lặp qua các file *.txt trong docs_dir
    2. Gọi parse_metadata
    3. Gọi split_into_chunks để gom toàn bộ chunks
    4. Gọi build_vector_index và build_bm25_index
    5. Gọi list_chunks để xác minh
    """
    # [Khai] build_all
    all_chunks: List[Document] = []
    txt_files = list(Path(docs_dir).glob("*.txt"))

    if not txt_files:
        print(f"[ERROR] Không tìm thấy file .txt trong {docs_dir}")
        return

    for filepath in txt_files:
        content = filepath.read_text(encoding="utf-8")
        meta = parse_metadata(content)
        chunks = split_into_chunks(content, meta)
        all_chunks.extend(chunks)
        print(f"  {filepath.name}: {len(chunks)} chunks")

    print(f"\nTotal: {len(all_chunks)} chunks từ {len(txt_files)} files")

    chroma = build_vector_index(all_chunks)
    bm25, docs = build_bm25_index(all_chunks)
    list_chunks(chroma)

    print("\n✅ Build index hoàn thành.")
    return chroma, bm25, docs

if __name__ == "__main__":
    print("Bắt đầu chạy build_all() cho vòng khởi tạo Index...")
    build_all()
