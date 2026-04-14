# Báo Cáo Cá Nhân — Lab Day 09: Multi-Agent Orchestration

**Họ và tên:** Nguyễn Tuấn Khải  
**Vai trò trong nhóm:** Worker Owner — Policy Tool + Synthesis  
**Ngày nộp:** 2026-04-14  
**Độ dài:** ~650 từ

---

## 1. Tôi phụ trách phần nào?

Tôi chịu trách nhiệm chính cho hai workers cuối trong pipeline:

- **`workers/policy_tool.py`** — functions `analyze_policy()` và `run()`: phát hiện exception cases (flash_sale, digital_product, activated), gọi MCP tools, ghi `worker_io_logs`
- **`workers/synthesis.py`** — functions `synthesize()`, `_build_context()`, `_estimate_confidence()`, `run()`: gọi LLM với grounded prompt, xử lý abstain khi không có evidence, tính confidence từ retrieval score

Ngoài ra, tôi thực hiện thêm hai thay đổi ngoài kế hoạch ban đầu để fix bug hệ thống:
- Đổi embedding model từ `all-MiniLM-L6-v2` sang `paraphrase-multilingual-MiniLM-L12-v2` trong `workers/retrieval.py`
- Thêm `load_dotenv()` vào cả ba workers (`retrieval.py`, `policy_tool.py`, `synthesis.py`)

Công việc của tôi là **bước cuối** của pipeline — nếu `synthesis.py` sai thì toàn bộ câu trả lời ra ngoài đều sai, bất kể retrieval và routing có đúng hay không. `policy_tool.py` cũng cung cấp `policy_result` để `synthesis.py` đưa vào context khi tổng hợp câu trả lời liên quan đến policy.

**Bằng chứng:** Commit `5d67381` — `[Khai][S2] policy_tool: always call MCP search_kb + check_access_permission; retrieval: multilingual model + top_k=5`

---

## 2. Tôi đã ra một quyết định kỹ thuật gì?

**Quyết định:** Đổi embedding model từ `all-MiniLM-L6-v2` (tiếng Anh) sang `paraphrase-multilingual-MiniLM-L12-v2` (đa ngôn ngữ, đã có sẵn trong cache) khi nhận thấy retrieval trả về kết quả sai cho query tiếng Việt.

**Lý do phát hiện:** Khi chạy pipeline với câu q01 ("SLA xử lý ticket P1 là bao lâu?"), synthesis trả về "Không đủ thông tin" dù collection có đủ data. Debug cho thấy chunk `Ticket P1` chỉ đạt score 0.38 — quá thấp để lọt vào top-3, trong khi header file và các ticket P2/P3 score cao hơn vì model tiếng Anh không hiểu ngữ nghĩa tiếng Việt.

**Các lựa chọn thay thế đã cân nhắc:**
- Dịch toàn bộ query sang tiếng Anh trước khi embed (phức tạp, cần thêm LLM call)
- Tăng `top_k` lên rất cao (không giải quyết gốc rễ)
- Dùng OpenAI embeddings (cần API call, tốn chi phí, chậm hơn)

Model multilingual đã có sẵn trong cache, offline, không cần API key — đây là lựa chọn tốt nhất về tốc độ triển khai.

**Trade-off:** Model multilingual nhỏ hơn OpenAI text-embedding-3, score vẫn chỉ ~0.55–0.65 cho tiếng Việt, nhưng đủ để retrieval trả đúng document.

**Bằng chứng từ trace q14** (`run_20260414_164318.json`):
```
"retrieved_chunks": [
  {"source": "hr_leave_policy.txt", "score": 0.679, "text": "Nhân viên sau probation period có thể làm remote tối đa 2 ngày/tuần..."},
  ...
]
"final_answer": "Nhân viên trong thời gian thử việc không đủ điều kiện làm remote..."
"confidence": 0.46
```
Câu trả lời đúng, lấy đúng nguồn `hr_leave_policy.txt`.

---

## 3. Tôi đã sửa một lỗi gì?

**Lỗi:** Synthesis worker luôn trả về "Không đủ thông tin" dù collection ChromaDB có đủ data.

**Symptom:** Chạy `graph.py`, câu q01 ("SLA ticket P1") cho kết quả `confidence=0.3` và answer là "Không đủ thông tin trong tài liệu nội bộ" — trong khi chạy `workers/retrieval.py` độc lập thì lấy được chunks đúng.

**Root cause:** Hai lỗi chồng nhau:
1. `workers/retrieval.py`, `workers/synthesis.py`, `workers/policy_tool.py` **không có `load_dotenv()`** → `OPENAI_API_KEY` không được load → `_call_llm()` trong synthesis ném exception → fallback về `[SYNTHESIS ERROR]` → synthesis bị coi là "không có answer" → confidence=0.3
2. `policy_tool_worker` trong LangGraph chạy **trước** `retrieval_worker` nhưng không có chunks → cần tự gọi MCP `search_kb`

**Cách sửa:**
```python
# Thêm vào đầu mỗi worker file
from dotenv import load_dotenv
load_dotenv()
```
Và trong `policy_tool.py`, bỏ điều kiện `if not chunks and needs_tool` — luôn gọi MCP `search_kb` để lấy context:
```python
# Luôn gọi MCP search_kb để lấy policy context từ KB
mcp_result = _call_mcp_tool("search_kb", {"query": task, "top_k": 3})
```

**Bằng chứng trước/sau:**

Trước khi sửa (trace `run_20260414_160604.json`):
```
"final_answer": "Không đủ thông tin trong tài liệu nội bộ...",
"confidence": 0.3,
"workers_called": ["retrieval_worker", "synthesis_worker"]
```

Sau khi sửa (trace `run_20260414_164345.json` — câu q15 multi-hop):
```
"history": [
  "[policy_tool_worker] called MCP search_kb",
  "[policy_tool_worker] called MCP check_access_permission level=2",
  "[synthesis_worker] answer generated, confidence=0.3, sources=['access_control_sop.txt']"
],
"mcp_tools_used": [{"tool": "search_kb", ...}, {"tool": "check_access_permission", ...}]
```

---

## 4. Tôi tự đánh giá đóng góp của mình

**Làm tốt nhất:** Exception detection trong `policy_tool.py` hoạt động đúng ngay từ lần đầu — test q07 (license key), q10 (Flash Sale + lỗi nhà sản xuất) đều trả về verdict chính xác không cần chỉnh sửa. Abstain logic trong `synthesis.py` cũng đúng — q09 (ERR-403-AUTH) trigger HITL và synthesis không hallucinate.

**Làm chưa tốt:** Confidence score chỉ dựa vào score của chunk top-1 từ retrieval — không phản ánh đúng chất lượng answer thực tế. Câu q15 (multi-hop, answer đúng) lại chỉ có `confidence=0.3` vì chunk score thấp, dễ gây nhầm lẫn khi đọc metrics.

**Nhóm phụ thuộc vào tôi:** `synthesis_worker` là bước cuối — mọi câu trả lời ra ngoài đều qua tay tôi. Nếu synthesis không load được LLM hoặc hallucinate, toàn bộ grading run sẽ thất bại.

**Tôi phụ thuộc vào:** Nhật (graph.py + AgentState schema) để biết input/output contract; Tấn (mcp_server.py) để gọi `dispatch_tool()` — cả hai đều có sẵn nên tôi không bị block.

---

## 5. Nếu có thêm 2 giờ, tôi sẽ làm gì?

Tôi sẽ thay confidence score bằng **LLM-as-Judge**: sau khi synthesis tạo answer, gọi thêm một LLM call ngắn để chấm điểm answer dựa trên evidence (0.0–1.0). Lý do: trace câu q15 cho thấy answer đúng và đầy đủ nhưng `confidence=0.3` vì chunk retrieval score thấp — đây là tín hiệu sai lệch. Nếu grading dùng confidence để filter câu trả lời, câu q15 có thể bị bỏ sót dù nội dung đúng.
