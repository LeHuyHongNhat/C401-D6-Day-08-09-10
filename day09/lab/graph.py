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
import time
from datetime import datetime
from typing import TypedDict, List, Optional, Literal

from dotenv import load_dotenv
from langgraph.graph import StateGraph, START, END

# Load environment variables
load_dotenv()

# ─────────────────────────────────────────────
# 1. Shared State — dữ liệu đi xuyên toàn graph
# ─────────────────────────────────────────────

# 1. AgentState — Định nghĩa cấu trúc dữ liệu chung
class AgentState(TypedDict):
    # Input
    task: str                        # câu hỏi gốc từ user

    # Routing
    supervisor_route: str            # "retrieval_worker" | "policy_tool_worker" | "human_review"
    route_reason: str                # VD: "task contains P1 SLA keyword"
    risk_high: bool                  # True nếu cần human review

    # Worker outputs
    retrieved_chunks: List[dict]     # output của retrieval worker
    policy_result: Optional[dict]    # output của policy worker
    worker_io_log: List[dict]        # log I/O của từng worker

    # MCP
    mcp_tools_used: List[str]        # tên tools đã gọi
    mcp_results: List[dict]          # kết quả từng MCP call

    # Final
    final_answer: str
    sources: List[str]
    confidence: float
    hitl_triggered: bool
    history: List[str]               # lịch sử các bước đã chạy (trace) - dùng string để tương thích main
    latency_ms: Optional[int]
    needs_tool: bool                 # Sprint 3: True nếu supervisor định gọi MCP tool
    workers_called: List[str]        # Sprint 4: Danh sách các worker đã tham gia xử lý


def make_initial_state(task: str) -> AgentState:
    """Khởi tạo state cho một run mới."""
    return {
        "task": task,
        "supervisor_route": "",
        "route_reason": "",
        "risk_high": False,
        "retrieved_chunks": [],
        "policy_result": {},
        "worker_io_log": [],
        "mcp_tools_used": [],
        "mcp_results": [],
        "final_answer": "",
        "sources": [],
        "confidence": 0.0,
        "hitl_triggered": False,
        "history": [],
        "needs_tool": False,
        "workers_called": []
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
    """
    task = state["task"].lower()

    # Routing logic dựa trên keywords của README.md
    route = "retrieval_worker"
    route_reason = "default route — general knowledge query"
    risk_high = False

    if any(kw in task for kw in ["hoàn tiền", "refund", "flash sale", "license", "kỹ thuật số", "digital"]):
        route = "policy_tool_worker"
        route_reason = "task contains refund/policy keyword"
    elif any(kw in task for kw in ["cấp quyền", "access", "level 3", "level 2", "contractor", "emergency", "khẩn cấp"]):
        route = "policy_tool_worker"
        route_reason = "task contains access control keyword"
    elif any(kw in task for kw in ["p1", "escalation", "sla", "ticket", "on-call", "sự cố"]):
        route = "retrieval_worker"
        route_reason = "task contains SLA/incident keyword"
    elif any(kw in task for kw in ["err-", "lỗi không rõ", "unknown error"]):
        route = "human_review"
        route_reason = "unrecognized error code — escalate to human"
        risk_high = True

    state["supervisor_route"] = route
    state["route_reason"] = route_reason
    state["risk_high"] = risk_high

    # Sprint 3 Logic: quyết định dùng MCP tool hay không
    needs_tool = False
    if route == "policy_tool_worker" or "p1" in task:
        needs_tool = True
    
    state["needs_tool"] = needs_tool
    state["route_reason"] += f" | needs_tool={needs_tool}"

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
    """
    state["hitl_triggered"] = True
    state["history"].append("[human_review] trigger_hitl")

    # Placeholder: tự động approve để pipeline tiếp tục
    print(f"\n⚠️  HITL TRIGGERED")
    print(f"   Task: {state['task']}")
    print(f"   Reason: {state['route_reason']}")
    print(f"   Action: Auto-approving in lab mode\n")

    # Sau khi human approve, route về retrieval để lấy evidence
    state["supervisor_route"] = "retrieval_worker"
    state["route_reason"] += " | human approved → retrieval"

    return state


# ─────────────────────────────────────────────
# 5. Import Workers
# ─────────────────────────────────────────────

# Thêm path để import từ project root
import sys
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

from workers.retrieval import run as retrieval_run
from workers.policy_tool import run as policy_tool_run
from workers.synthesis import run as synthesis_run


def retrieval_worker_node(state: AgentState) -> AgentState:
    """Wrapper gọi retrieval worker thật."""
    return retrieval_run(state)


def policy_tool_worker_node(state: AgentState) -> AgentState:
    """Wrapper gọi policy/tool worker."""
    return policy_tool_run(state)


def synthesis_worker_node(state: AgentState) -> AgentState:
    """Wrapper gọi synthesis worker."""
    return synthesis_run(state)


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
    result = _graph.invoke(state)
    result["latency_ms"] = int((time.time() - t0) * 1000)
    return result


def save_trace(state: AgentState, output_dir: str = "./artifacts/traces") -> str:
    """Lưu trace ra file JSON."""
    os.makedirs(output_dir, exist_ok=True)
    filename = f"{output_dir}/trace_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
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
        print(f"  Answer  : {result['final_answer'][:100]}...")
        print(f"  Confidence: {result['confidence']}")

        # Lưu trace
        trace_file = save_trace(result)
        print(f"  Trace saved → {trace_file}")

    print("\n✅ graph.py test complete. Implement TODO sections in Sprint 1 & 2.")
