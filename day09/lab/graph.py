"""
graph.py — Supervisor Orchestrator
Sprint 1: Implement AgentState, supervisor_node, route_decision và kết nối graph.

Kiến trúc:
    Input → Supervisor → [retrieval_worker | policy_tool_worker | human_review] → synthesis → Output

Chạy thử:
    python graph.py
"""

import json
import os
from datetime import datetime
from typing import TypedDict, Literal, Optional, cast, Any

import time
from langgraph.graph import StateGraph, START, END

from workers.retrieval import run as retrieval_run
from workers.policy_tool import run as policy_tool_run
from workers.synthesis import run as synthesis_run

# ─────────────────────────────────────────────
# 1. Shared State — dữ liệu đi xuyên toàn graph
# ─────────────────────────────────────────────

class AgentState(TypedDict):
    # Input
    task: str                           # Câu hỏi đầu vào từ user

    # Supervisor decisions
    route_reason: str                   # Lý do route sang worker nào
    risk_high: bool                     # True → cần HITL hoặc human_review
    needs_tool: bool                    # True → cần gọi external tool qua MCP
    hitl_triggered: bool                # True → đã pause cho human review

    # Worker outputs
    retrieved_chunks: list              # Output từ retrieval_worker
    retrieved_sources: list             # Danh sách nguồn tài liệu
    policy_result: dict                 # Output từ policy_tool_worker
    mcp_tools_used: list                # Danh sách MCP tools đã gọi

    # Final output
    final_answer: str                   # Câu trả lời tổng hợp
    sources: list                       # Sources được cite
    confidence: float                   # Mức độ tin cậy (0.0 - 1.0)

    # Trace & history
    history: list                       # Lịch sử các bước đã qua (trace)
    worker_io_logs: list                # Log I/O từng worker (dùng số nhiều để đồng bộ main)
    workers_called: list                # Danh sách workers đã được gọi (không kèm supervisor)
    supervisor_route: str               # Worker được chọn bởi supervisor
    latency_ms: Optional[int]           # Thời gian xử lý tổng cộng (ms)
    run_id: str                         # ID duy nhất cho mỗi lần chạy (dùng cho batch eval)
    needs_tool: bool                    # Sprint 3: True nếu cần gọi tool MCP


def make_initial_state(task: str) -> AgentState:
    """Khởi tạo state cho một run mới."""
    return {
        "task": task,
        "route_reason": "",
        "risk_high": False,
        "needs_tool": False,
        "hitl_triggered": False,
        "retrieved_chunks": [],
        "retrieved_sources": [],
        "policy_result": {},
        "mcp_tools_used": [],
        "final_answer": "",
        "sources": [],
        "confidence": 0.0,
        "history": [],
        "worker_io_logs": [],
        "workers_called": [],
        "supervisor_route": "",
        "latency_ms": None,
        "needs_tool": False,
        "run_id": f"run_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
    }


# ─────────────────────────────────────────────
# 2. Supervisor Node — quyết định route
# ─────────────────────────────────────────────

def supervisor_node(state: AgentState) -> AgentState:
    """
    Supervisor phân tích task và quyết định:
    1. Route sang worker nào
    2. Có cần MCP tool không
    3. Có risk cao cần HITL không

    Thứ tự ưu tiên (cao → thấp): human_review → policy_tool → retrieval → default.
    Mã lỗi / HITL phải xét trước SLA để câu kiểu "P1 + ERR-403" không bị nuốt bởi nhánh retrieval.
    """
    task = state["task"].lower()

    # Routing logic dựa trên keywords của README.md
    route = "retrieval_worker"
    route_reason = "default route — general knowledge query"
    needs_tool = False
    risk_high = False

    if any(kw in task for kw in ["err-", "lỗi không rõ", "unknown error"]):
        route = "human_review"
        route_reason = "unrecognized error code — escalate to human"
        risk_high = True
    elif any(kw in task for kw in ["hoàn tiền", "refund", "flash sale", "license", "kỹ thuật số", "digital"]):
        route = "policy_tool_worker"
        route_reason = "task contains refund/policy keyword"
        needs_tool = True
    elif any(kw in task for kw in ["cấp quyền", "access", "level 3", "level 2", "contractor", "emergency", "khẩn cấp"]):
        route = "policy_tool_worker"
        route_reason = "task contains access control keyword"
        needs_tool = True
    elif any(kw in task for kw in ["p1", "escalation", "sla", "ticket", "on-call", "sự cố"]):
        route = "retrieval_worker"
        route_reason = "task contains SLA/incident keyword"

    state["supervisor_route"] = route
    state["route_reason"] = route_reason
    state["needs_tool"] = needs_tool
    state["risk_high"] = risk_high
    state["history"].append(f"[supervisor] route={route} | reason={route_reason}")

    return state


# ─────────────────────────────────────────────
# 3. Route Decision — conditional edge
# ─────────────────────────────────────────────

def route_decision(state: AgentState) -> Literal["retrieval_worker", "policy_tool_worker", "human_review"]:
    """
    Trả về tên worker tiếp theo dựa vào supervisor_route trong state.
    Đây là conditional edge của graph.
    """
    route = state.get("supervisor_route", "retrieval_worker")
    return route  # type: ignore


# ─────────────────────────────────────────────
# 4. Human Review Node — HITL placeholder
# ─────────────────────────────────────────────

def human_review_node(state: AgentState) -> AgentState:
    """
    HITL node: pause và chờ human approval.
    Trong lab này, implement dưới dạng placeholder (in ra warning).

    TODO Sprint 3 (optional): Implement actual HITL với interrupt_before hoặc
    breakpoint nếu dùng LangGraph.
    """
    state["hitl_triggered"] = True
    state["history"].append("[human_review] HITL triggered — awaiting human input")
    state["workers_called"].append("human_review")

    # Placeholder: tự động approve để pipeline tiếp tục
    print(f"\n⚠️  HITL TRIGGERED")
    print(f"   Task: {state['task']}")
    print(f"   Reason: {state['route_reason']}")
    print(f"   Action: Auto-approving in lab mode (set hitl_triggered=True)\n")

    # Sau khi human approve, route về retrieval để lấy evidence
    state["supervisor_route"] = "retrieval_worker"
    state["route_reason"] += " | human approved → retrieval"

    return state


# ─────────────────────────────────────────────
# 5. Worker nodes — gọi workers thật (retrieval / policy_tool / synthesis)
# ─────────────────────────────────────────────


def _ensure_worker_log(state: AgentState) -> None:
    state.setdefault("worker_io_log", [])


def retrieval_worker_node(state: AgentState) -> AgentState:
    """Chạy retrieval (ChromaDB) — bổ sung evidence vào state."""
    _ensure_worker_log(state)
    return cast(AgentState, retrieval_run(cast(dict[str, Any], state)))


def policy_tool_worker_node(state: AgentState) -> AgentState:
    """Chạy policy + MCP (search_kb, check_access, …)."""
    _ensure_worker_log(state)
    return cast(AgentState, policy_tool_run(cast(dict[str, Any], state)))


def synthesis_worker_node(state: AgentState) -> AgentState:
    """Chạy synthesis (LLM grounded) — final_answer, sources, confidence."""
    _ensure_worker_log(state)
    return cast(AgentState, synthesis_run(cast(dict[str, Any], state)))


# ─────────────────────────────────────────────
# 6. Build Graph
# ─────────────────────────────────────────────

def build_graph():
    """
    Xây dựng graph với supervisor-worker pattern bằng LangGraph StateGraph.
    """
    workflow = StateGraph(AgentState)

    # Thêm các nodes
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("retrieval_worker", retrieval_worker_node)
    workflow.add_node("policy_tool_worker", policy_tool_worker_node)
    workflow.add_node("human_review", human_review_node)
    workflow.add_node("synthesis_worker", synthesis_worker_node)

    # Định nghĩa edges
    workflow.add_edge(START, "supervisor")

    # Conditional routing từ supervisor
    workflow.add_conditional_edges(
        "supervisor",
        route_decision,
        {
            "retrieval_worker": "retrieval_worker",
            "policy_tool_worker": "policy_tool_worker",
            "human_review": "human_review",
        }
    )

    # Kết nối workers → synthesis
    workflow.add_edge("human_review", "retrieval_worker")
    workflow.add_edge("retrieval_worker", "synthesis_worker")
    workflow.add_edge("policy_tool_worker", "synthesis_worker")
    workflow.add_edge("synthesis_worker", END)

    return workflow.compile()


# ─────────────────────────────────────────────
# 7. Public API
# ─────────────────────────────────────────────

_graph = build_graph()


def run_graph(task: str) -> AgentState:
    """
    Entry point: nhận câu hỏi, chạy qua LangGraph và trả về AgentState với full trace.
    """
    state = make_initial_state(task)
    t0 = time.time()
    result = cast(AgentState, _graph.invoke(state))
    result["latency_ms"] = int((time.time() - t0) * 1000)
    return result


def save_trace(state: AgentState, output_dir: str = "./artifacts/traces") -> str:
    """Lưu trace ra file JSON."""
    os.makedirs(output_dir, exist_ok=True)
    filename = f"{output_dir}/{state['run_id']}.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    return filename


# ─────────────────────────────────────────────
# 8. Manual Test
# ─────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("Day 09 Lab — Supervisor-Worker Graph")
    print("=" * 60)

    test_queries = [
        "SLA xử lý ticket P1 là bao lâu?",
        "Khách hàng Flash Sale yêu cầu hoàn tiền vì sản phẩm lỗi — được không?",
        "Cần cấp quyền Level 3 để khắc phục P1 khẩn cấp. Quy trình là gì?",
    ]

    for query in test_queries:
        print(f"\n▶ Query: {query}")
        result = run_graph(query)
        print(f"  Route   : {result['supervisor_route']}")
        print(f"  Reason  : {result['route_reason']}")
        print(f"  Workers : {result['workers_called']}")
        print(f"  Answer  : {result['final_answer'][:100]}...")
        print(f"  Confidence: {result['confidence']}")
        print(f"  Latency : {result['latency_ms']}ms")

        # Lưu trace
        trace_file = save_trace(result)
        print(f"  Trace saved → {trace_file}")

    print("\n✅ graph.py — workers retrieval + policy_tool + synthesis đã nối.")
