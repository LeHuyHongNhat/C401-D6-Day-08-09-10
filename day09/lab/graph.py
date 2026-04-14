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
from typing import TypedDict, List, Optional, Literal

# Load LangGraph components
from langgraph.graph import StateGraph, START, END

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
    history: List[dict]              # lịch sử các bước đã chạy (trace)


def make_initial_state(task: str) -> AgentState:
    """Khởi tạo state cho một run mới."""
    return {
        "task": task,
        "supervisor_route": "",
        "route_reason": "",
        "risk_high": False,
        "retrieved_chunks": [],
        "policy_result": None,
        "worker_io_log": [],
        "mcp_tools_used": [],
        "mcp_results": [],
        "final_answer": "",
        "sources": [],
        "confidence": 0.0,
        "hitl_triggered": False,
        "history": []
    }


# ─────────────────────────────────────────────
# 2. Supervisor Node — quyết định route
# ─────────────────────────────────────────────

def supervisor_node(state: AgentState) -> AgentState:
    """
    Supervisor phân tích task và quyết định:
    1. Route sang worker nào
    2. Có risk cao cần HITL không

    Cập nhật logic routing dựa trên các từ khóa (keywords) trong câu hỏi.
    """
    task = state["task"].lower()

    # Routing logic mặc định
    route = "retrieval_worker"
    reason = "default route — general knowledge query"
    risk_high = False

    # Logic phân loại dựa trên keywords
    if any(kw in task for kw in ["hoàn tiền", "refund", "flash sale", "digital", "license"]):
        route = "policy_tool_worker"
        reason = "task contains refund/policy keyword"
    elif any(kw in task for kw in ["cấp quyền", "access", "level", "contractor", "emergency"]):
        route = "policy_tool_worker"
        reason = "task contains access control keyword"
    elif any(kw in task for kw in ["p1", "escalation", "sla", "ticket", "on-call"]):
        route = "retrieval_worker"
        reason = "task contains SLA/incident keyword"
    elif any(kw in task for kw in ["err-", "lỗi không rõ", "unknown error"]):
        route = "human_review"
        reason = "unrecognized error code — escalate to human"

    state["supervisor_route"] = route
    state["route_reason"] = reason
    state["risk_high"] = risk_high

    # Log history - đơn giản hóa thành chuỗi cho lab
    state["history"].append({"node": "supervisor", "action": "route", "route": route, "reason": reason})

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
    state["history"].append({"node": "human_review", "action": "trigger_hitl"})

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

# TODO Sprint 2: Uncomment sau khi implement workers
# from workers.retrieval import run as retrieval_run
# from workers.policy_tool import run as policy_tool_run
# from workers.synthesis import run as synthesis_run


def retrieval_worker_node(state: AgentState) -> AgentState:
    """Wrapper gọi retrieval worker."""
    # TODO Sprint 2: Thay bằng retrieval_run(state)
    state["history"].append({"node": "retrieval_worker", "action": "start"})

    # Placeholder output để test graph chạy được
    state["retrieved_chunks"] = [
        {"text": "SLA P1: phản hồi 15 phút, xử lý 4 giờ.", "source": "sla_p1_2026.txt", "score": 0.92}
    ]
    state["history"].append({"node": "retrieval_worker", "action": "completed", "num_chunks": len(state["retrieved_chunks"])})
    return state


def policy_tool_worker_node(state: AgentState) -> AgentState:
    """Wrapper gọi policy/tool worker."""
    # TODO Sprint 2: Thay bằng policy_tool_run(state)
    state["history"].append({"node": "policy_tool_worker", "action": "start"})

    # Placeholder output
    state["policy_result"] = {
        "verdict": "standard_policy",
        "exception_case": None,
        "evidence": "policy_refund_v4.txt",
        "mcp_tool_called": None
    }
    state["history"].append({"node": "policy_tool_worker", "action": "completed"})
    return state


def synthesis_worker_node(state: AgentState) -> AgentState:
    """Wrapper gọi synthesis worker."""
    # TODO Sprint 2: Thay bằng synthesis_run(state)
    state["history"].append({"node": "synthesis_worker", "action": "start"})

    # Placeholder output
    chunks = state.get("retrieved_chunks", [])
    state["final_answer"] = f"[PLACEHOLDER] Câu trả lời được tổng hợp từ {len(chunks)} chunks."
    state["sources"] = list({c["source"] for c in chunks})
    state["confidence"] = 0.75
    state["history"].append({"node": "synthesis_worker", "action": "completed", "confidence": state["confidence"]})
    return state


# ─────────────────────────────────────────────
# 6. Build Graph
# ─────────────────────────────────────────────

def build_graph():
    """
    Xây dựng graph với supervisor-worker pattern bằng LangGraph.
    """
    # 1. Khởi tạo StateGraph với AgentState
    workflow = StateGraph(AgentState)

    # 2. Thêm các Nodes
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("retrieval_worker", retrieval_worker_node)
    workflow.add_node("policy_tool_worker", policy_tool_worker_node)
    workflow.add_node("human_review", human_review_node)
    workflow.add_node("synthesis_worker", synthesis_worker_node)

    # 3. Định nghĩa các Edges
    workflow.add_edge(START, "supervisor")

    # Conditional logic cho supervisor
    workflow.add_conditional_edges(
        "supervisor",
        route_decision,
        {
            "retrieval_worker": "retrieval_worker",
            "policy_tool_worker": "policy_tool_worker",
            "human_review": "human_review"
        }
    )

    # Kết nối các workers
    workflow.add_edge("human_review", "retrieval_worker")
    workflow.add_edge("retrieval_worker", "synthesis_worker")
    workflow.add_edge("policy_tool_worker", "synthesis_worker")

    # Kết thúc tại synthesis
    workflow.add_edge("synthesis_worker", END)

    # 4. Compile graph
    return workflow.compile()


# ─────────────────────────────────────────────
# 7. Public API
# ─────────────────────────────────────────────

_graph = build_graph()


def run_graph(task: str) -> AgentState:
    """
    Entry point: nhận câu hỏi, chạy qua LangGraph và trả về AgentState.
    """
    state = make_initial_state(task)
    # LangGraph returns the full final state
    result = _graph.invoke(state)
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
