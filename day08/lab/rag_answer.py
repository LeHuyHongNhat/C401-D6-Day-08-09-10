"""
rag_answer.py — Sprint 2 + Sprint 3: Retrieval & Grounded Answer
================================================================
Sprint 2 (60 phút): Baseline RAG
  - Dense retrieval từ ChromaDB
  - Grounded answer function với prompt ép citation
  - Trả lời được ít nhất 3 câu hỏi mẫu, output có source

Sprint 3 (60 phút): Tuning tối thiểu
  - Thêm hybrid retrieval (dense + sparse/BM25)
  - Hoặc thêm rerank (cross-encoder)
  - Hoặc thử query transformation (expansion, decomposition, HyDE)
  - Tạo bảng so sánh baseline vs variant

Definition of Done Sprint 2:
  ✓ rag_answer("SLA ticket P1?") trả về câu trả lời có citation
  ✓ rag_answer("Câu hỏi không có trong docs") trả về "Không đủ dữ liệu"

Definition of Done Sprint 3:
  ✓ Có ít nhất 1 variant (hybrid / rerank / query transform) chạy được
  ✓ Giải thích được tại sao chọn biến đó để tune
"""

import os
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dotenv import load_dotenv

load_dotenv()

# =============================================================================
# CẤU HÌNH
# =============================================================================

TOP_K_SEARCH = 10    # Số chunk lấy từ vector store trước rerank (search rộng)
TOP_K_SELECT = 3     # Số chunk gửi vào prompt sau rerank/select (top-3 sweet spot)

LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")


# =============================================================================
# RETRIEVAL — DENSE (Vector Search)
# =============================================================================

def retrieve_dense(query: str, top_k: int = TOP_K_SEARCH) -> List[Dict[str, Any]]:
    """
    Dense retrieval: tìm kiếm theo embedding similarity trong ChromaDB.
    """
    from index import get_embeddings_fn, CHROMA_PERSIST_DIR
    
    # Initialize embeddings using fallback logic
    embedding_fn = get_embeddings_fn()
    
    # Load Chroma
    from langchain_community.vectorstores import Chroma
    vectorstore = Chroma(
        persist_directory=CHROMA_PERSIST_DIR,
        embedding_function=embedding_fn
    )
    
    # Search
    results = vectorstore.similarity_search_with_score(query, k=top_k)
    
    # Convert to expected format
    formatted_results = []
    for doc, distance in results:
        # Distance to score (similarity)
        # Similarity approx = 1 - distance
        score = 1.0 - distance
        
        formatted_results.append({
            "text": doc.page_content,
            "metadata": doc.metadata,
            "score": score
        })
        
    return formatted_results


# =============================================================================
# RETRIEVAL — SPARSE / BM25 (Keyword Search)
# Dùng cho Sprint 3 Variant hoặc kết hợp Hybrid
# =============================================================================

def retrieve_sparse(query: str, top_k: int = TOP_K_SEARCH) -> List[Dict[str, Any]]:
    """
    Sparse retrieval: tìm kiếm theo keyword (BM25S).
    """
    import bm25s
    import pickle
    from index import BM25_INDEX_DIR
    
    index_dir = Path(BM25_INDEX_DIR)
    
    # Load retriever and documents (from pickle as saved in index.py)
    try:
        with open(index_dir / "bm25.pkl", "rb") as f:
            retriever = pickle.load(f)
        with open(index_dir / "docs.pkl", "rb") as f:
            documents = pickle.load(f)
    except FileNotFoundError:
        print(f"[Error] BM25 Index not found at {index_dir}. Please run index.py first.")
        return []

    # Tokenize query
    tokenized_query = bm25s.tokenize(query)
    
    # Search
    # bm25s.retrieve returns indices of the corpus if we indexed tokens
    results, scores = retriever.retrieve(tokenized_query, k=top_k)
    
    formatted_results = []
    for i in range(len(results[0])):
        idx = results[0][i]
        doc = documents[idx]
        formatted_results.append({
            "text": doc.page_content,
            "metadata": doc.metadata,
            "score": float(scores[0][i])
        })
        
    return formatted_results


def retrieve_hybrid(
    query: str,
    top_k: int = TOP_K_SEARCH,
    dense_weight: float = 0.6,
    sparse_weight: float = 0.4,
) -> List[Dict[str, Any]]:
    """
    Hybrid retrieval: kết hợp dense và sparse bằng Reciprocal Rank Fusion (RRF).
    Hỗ trợ xử lý:
    - Tìm kiếm theo ý nghĩa (Dense)
    - Tìm kiếm theo từ khóa (Sparse): các tên riêng, mã lỗi, điều khoản
    - Query dùng alias/tên cũ (ví dụ: "Approval Matrix" → "Access Control SOP")
    """
    dense_results = retrieve_dense(query, top_k=top_k)
    sparse_results = retrieve_sparse(query, top_k=top_k)
    
    # RRF Algorithm
    rrf_scores = {}
    k_constant = 60
    
    # Process Dense
    for rank, doc in enumerate(dense_results, 1):
        doc_text = doc["text"]
        rrf_scores[doc_text] = rrf_scores.get(doc_text, 0) + dense_weight * (1.0 / (k_constant + rank))
    
    # Process Sparse
    for rank, doc in enumerate(sparse_results, 1):
        doc_text = doc["text"]
        if doc_text not in rrf_scores:
            rrf_scores[doc_text] = 0
            
        rrf_scores[doc_text] += sparse_weight * (1.0 / (k_constant + rank))
    
    # Combine back with full data
    all_docs = {d["text"]: d for d in dense_results + sparse_results}
    
    ranked_chunks = []
    for text, score in sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True):
        doc_data = all_docs[text].copy()
        doc_data["score"] = score
        ranked_chunks.append(doc_data)
        
    return ranked_chunks[:top_k]


# =============================================================================
# RERANK (Sprint 3 alternative)
# =============================================================================

def rerank(
    query: str,
    candidates: List[Dict[str, Any]],
    top_k: int = TOP_K_SELECT,
) -> List[Dict[str, Any]]:
    """
    Rerank các candidate chunks bằng cross-encoder.
    """
    if not candidates:
        return []
        
    from sentence_transformers import CrossEncoder
    
    # Model nhỏ, chạy nhanh trên CPU
    model = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
    
    pairs = [[query, c["text"]] for c in candidates]
    scores = model.predict(pairs)
    
    # Sắp xếp lại dựa trên score của Cross-Encoder
    ranked_candidates = []
    for i in range(len(candidates)):
        c = candidates[i].copy()
        c["rerank_score"] = float(scores[i])
        ranked_candidates.append(c)
        
    ranked_candidates.sort(key=lambda x: x["rerank_score"], reverse=True)
    return ranked_candidates[:top_k]


# =============================================================================
# QUERY TRANSFORMATION (Sprint 3 alternative)
# =============================================================================

def transform_query(query: str, strategy: str = "expansion") -> List[str]:
    """
    Biến đổi query để tăng recall.

    Strategies:
      - "expansion": Thêm từ đồng nghĩa, alias, tên cũ
      - "decomposition": Tách query phức tạp thành 2-3 sub-queries
      - "hyde": Sinh câu trả lời giả (hypothetical document) để embed thay query

    TODO Sprint 3 (nếu chọn query transformation):
    Gọi LLM với prompt phù hợp với từng strategy.

    Ví dụ expansion prompt:
        "Given the query: '{query}'
         Generate 2-3 alternative phrasings or related terms in Vietnamese.
         Output as JSON array of strings."

    Ví dụ decomposition:
        "Break down this complex query into 2-3 simpler sub-queries: '{query}'
         Output as JSON array."

    Khi nào dùng:
    - Expansion: query dùng alias/tên cũ (ví dụ: "Approval Matrix" → "Access Control SOP")
    - Decomposition: query hỏi nhiều thứ một lúc
    - HyDE: query mơ hồ, search theo nghĩa không hiệu quả
    """
    # TODO Sprint 3: Implement query transformation
    # Tạm thời trả về query gốc
    return [query]


# =============================================================================
# GENERATION — GROUNDED ANSWER FUNCTION
# =============================================================================

def build_context_block(chunks: List[Dict[str, Any]]) -> str:
    """
    Đóng gói danh sách chunks thành context block để đưa vào prompt.
    """
    context_parts = []
    for i, chunk in enumerate(chunks, 1):
        meta = chunk.get("metadata", {})
        source = meta.get("source", "unknown")
        section = meta.get("section", "")
        text = chunk.get("text", "")

        header = f"[{i}] Nguồn: {source}"
        if section:
            header += f" | Section: {section}"

        context_parts.append(f"{header}\n{text}")

    return "\n\n".join(context_parts)

def format_citations(sources: List[str]) -> str:
    """
    Tạo citation list ở cuối câu trả lời (Dành riêng cho Sprint 2 requirements).
    """
    if not sources:
        return ""
    lines = ["\n\n**Nguồn tham khảo:**"]
    for i, src in enumerate(sources, 1):
        lines.append(f"[{i}] {src}")
    return "\n".join(lines)


def build_grounded_prompt(query: str, context_block: str) -> str:
    """
    Xây dựng grounded prompt theo 4 quy tắc từ slide:
    1. Evidence-only: Chỉ trả lời từ retrieved context
    2. Abstain: Thiếu context thì nói không đủ dữ liệu
    3. Citation: Gắn source/section khi có thể
    4. Short, clear, stable: Output ngắn, rõ, nhất quán

    TODO Sprint 2:
    Đây là prompt baseline. Trong Sprint 3, bạn có thể:
    - Thêm hướng dẫn về format output (JSON, bullet points)
    - Thêm ngôn ngữ phản hồi (tiếng Việt vs tiếng Anh)
    - Điều chỉnh tone phù hợp với use case (CS helpdesk, IT support)
    """
    prompt = f"""Answer only from the retrieved context below.
If the context is insufficient to answer the question, say you do not know and do not make up information.
Cite the source field (in brackets like [1]) when possible.
Keep your answer short, clear, and factual.
Respond in the same language as the question.

Question: {query}

Context:
{context_block}

Answer:"""
    return prompt


def call_llm(prompt: str) -> str:
    """
    Gọi LLM để sinh câu trả lời sử dụng OpenAI.
    """
    from openai import OpenAI
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    model_name = os.getenv("LLM_MODEL", "gpt-4o-mini")
    
    response = client.chat.completions.create(
        model=model_name,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        max_tokens=1024,
    )
    return response.choices[0].message.content


def rag_answer(
    query: str,
    retrieval_mode: str = "dense",
    top_k_search: int = TOP_K_SEARCH,
    top_k_select: int = TOP_K_SELECT,
    use_rerank: bool = False,
    verbose: bool = False,
) -> Dict[str, Any]:
    """
    Pipeline RAG hoàn chỉnh: query → retrieve → (rerank) → generate.

    Args:
        query: Câu hỏi
        retrieval_mode: "dense" | "sparse" | "hybrid"
        top_k_search: Số chunk lấy từ vector store (search rộng)
        top_k_select: Số chunk đưa vào prompt (sau rerank/select)
        use_rerank: Có dùng cross-encoder rerank không
        verbose: In thêm thông tin debug

    Returns:
        Dict với:
          - "answer": câu trả lời grounded
          - "sources": list source names trích dẫn
          - "chunks_used": list chunks đã dùng
          - "query": query gốc
          - "config": cấu hình pipeline đã dùng

    TODO Sprint 2 — Implement pipeline cơ bản:
    1. Chọn retrieval function dựa theo retrieval_mode
    2. Gọi rerank() nếu use_rerank=True
    3. Truncate về top_k_select chunks
    4. Build context block và grounded prompt
    5. Gọi call_llm() để sinh câu trả lời
    6. Trả về kết quả kèm metadata

    TODO Sprint 3 — Thử các variant:
    - Variant A: đổi retrieval_mode="hybrid"
    - Variant B: bật use_rerank=True
    - Variant C: thêm query transformation trước khi retrieve
    """
    config = {
        "retrieval_mode": retrieval_mode,
        "top_k_search": top_k_search,
        "top_k_select": top_k_select,
        "use_rerank": use_rerank,
    }

    # --- Bước 1: Retrieve ---
    if retrieval_mode == "dense":
        candidates = retrieve_dense(query, top_k=top_k_search)
    elif retrieval_mode == "sparse":
        candidates = retrieve_sparse(query, top_k=top_k_search)
    elif retrieval_mode == "hybrid":
        candidates = retrieve_hybrid(query, top_k=top_k_search)
    else:
        raise ValueError(f"retrieval_mode không hợp lệ: {retrieval_mode}")

    if verbose:
        print(f"\n[RAG] Query: {query}")
        print(f"[RAG] Retrieved {len(candidates)} candidates (mode={retrieval_mode})")
        for i, c in enumerate(candidates[:3]):
            print(f"  [{i+1}] score={c.get('score', 0):.3f} | {c['metadata'].get('source', '?')}")

    # --- Bước 2: Rerank (optional) ---
    if use_rerank:
        candidates = rerank(query, candidates, top_k=top_k_select)
    else:
        candidates = candidates[:top_k_select]

    if verbose:
        print(f"[RAG] After select: {len(candidates)} chunks")

    # --- Bước 3: Build context và prompt ---
    context_block = build_context_block(candidates)
    prompt = build_grounded_prompt(query, context_block)

    if verbose:
        print(f"\n[RAG] Prompt:\n{prompt[:500]}...\n")

    # --- Bước 4: Generate ---
    answer = call_llm(prompt)
    
    # --- Bước 5: Extract sources ---
    sources = []
    seen_sources = set()
    for c in candidates:
        src = c["metadata"].get("source", "unknown")
        if src not in seen_sources:
            sources.append(src)
            seen_sources.add(src)

    # Append citation list to answer (Khánh's Sprint 2 task)
    answer += format_citations(sources)

    return {
        "query": query,
        "answer": answer,
        "sources": sources,
        "chunks_used": candidates,
        "config": config,
    }


# =============================================================================
# SPRINT 3: SO SÁNH BASELINE VS VARIANT
# =============================================================================

def compare_retrieval_strategies(query: str) -> None:
    """
    So sánh các retrieval strategies với cùng một query.

    TODO Sprint 3:
    Chạy hàm này để thấy sự khác biệt giữa dense, sparse, hybrid.
    Dùng để justify tại sao chọn variant đó cho Sprint 3.

    A/B Rule (từ slide): Chỉ đổi MỘT biến mỗi lần.
    """
    print(f"\n{'='*60}")
    print(f"Query: {query}")
    print('='*60)

    strategies = ["dense", "hybrid"]  # Thêm "sparse" sau khi implement

    for strategy in strategies:
        print(f"\n--- Strategy: {strategy} ---")
        try:
            result = rag_answer(query, retrieval_mode=strategy, verbose=False)
            print(f"Answer: {result['answer']}")
            print(f"Sources: {result['sources']}")
        except NotImplementedError as e:
            print(f"Chưa implement: {e}")
        except Exception as e:
            print(f"Lỗi: {e}")


# =============================================================================
# MAIN — Demo và Test
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("Sprint 2 + 3: RAG Answer Pipeline")
    print("=" * 60)

    # Test queries từ data/test_questions.json
    test_queries = [
        "SLA xử lý ticket P1 là bao lâu?",
        "Khách hàng có thể yêu cầu hoàn tiền trong bao nhiêu ngày?",
        "Ai phải phê duyệt để cấp quyền Level 3?",
        "ERR-403-AUTH là lỗi gì?",  # Query không có trong docs → kiểm tra abstain
    ]

    print("\n--- Sprint 2: Test Baseline (Dense) ---")
    # --- Sprint 3: Hybrid Search + Rerank ---
    print("\n" + "="*60)
    print("--- Sprint 3: Hybrid Search + Rerank ---")
    print("="*60)
    
    # Query khó: dùng tên cũ (alias) hoặc mã lỗi không có trong embedding tốt
    query_s3 = "Làm sao để có Approval Matrix và cấp quyền hệ thống?"
    print(f"\nQuery: {query_s3}")
    
    result_s3 = rag_answer(
        query_s3, 
        retrieval_mode="hybrid", 
        use_rerank=True, 
        verbose=True
    )
    print(f"\nAnswer: {result_s3['answer']}")

    # Uncomment sau khi Sprint 3 hoàn thành:
    # print("\n--- Sprint 3: So sánh strategies ---")
    # compare_retrieval_strategies("Approval Matrix để cấp quyền là tài liệu nào?")
    # compare_retrieval_strategies("ERR-403-AUTH")

    print("\n\nViệc cần làm Sprint 2:")
    print("  1. Implement retrieve_dense() — query ChromaDB")
    print("  2. Implement call_llm() — gọi OpenAI hoặc Gemini")
    print("  3. Chạy rag_answer() với 3+ test queries")
    print("  4. Verify: output có citation không? Câu không có docs → abstain không?")

    print("\nViệc cần làm Sprint 3:")
    print("  1. Chọn 1 trong 3 variants: hybrid, rerank, hoặc query transformation")
    print("  2. Implement variant đó")
    print("  3. Chạy compare_retrieval_strategies() để thấy sự khác biệt")
    print("  4. Ghi lý do chọn biến đó vào docs/tuning-log.md")
