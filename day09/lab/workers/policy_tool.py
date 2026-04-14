import re
from datetime import datetime
from typing import List, Dict, Any, Optional

WORKER_NAME = "policy_tool_worker"

# ─────────────────────────────────────────────
# MCP Client — Sprint 3: Thay bằng real MCP call
# ─────────────────────────────────────────────

def _call_mcp_tool(tool_name: str, tool_input: dict) -> dict:
    """
    Gọi MCP tool thông qua module singleton dispatch_tool.
    """
    try:
        from mcp_server import dispatch_tool
        result = dispatch_tool(tool_name, tool_input)
        return result
    except Exception as e:
        return {
            "tool": tool_name,
            "input": tool_input,
            "output": None,
            "error": {"code": "MCP_CALL_FAILED", "reason": str(e)},
            "timestamp": datetime.now().isoformat(),
        }


# ─────────────────────────────────────────────
# Policy Analysis Logic
# ─────────────────────────────────────────────

def analyze_policy(task: str, chunks: list) -> dict:
    """
    Phân tích policy dựa trên context chunks.

    Returns:
        dict with: policy_applies, policy_name, exceptions_found, source, rule, explanation
    """
    task_lower = task.lower()
    policy_result = {
        "policy_applies": False,
        "policy_name": "refund_policy_v4",
        "exceptions_found": [],
        "source": [],
        "policy_version_note": "",
        "explanation": "Analyzed via rule-based policy check. TODO: upgrade to LLM-based analysis."
    }

    # 1. Kiểm tra ngày tháng đơn hàng (Temporal policy)
    # Giả định câu hỏi có ngày tháng định dạng dd/mm/yyyy
    date_match = re.search(r"(\d{2}/\d{2}/\d{4})", task)
    if date_match:
        date_str = date_match.group(1)
        try:
            order_date = datetime.strptime(date_str, "%d/%m/%Y")
            v4_start_date = datetime(2026, 2, 1)
            if order_date < v4_start_date:
                policy_result["policy_version_note"] = "Order before 01/02/2026 — Applying Refund Policy V3 logic."
        except:
            pass

    # 2. Kiểm tra các ngoại lệ (Flash Sale, Digital, Activated)
    if "flash sale" in task_lower:
        policy_result["exceptions_found"].append("Flash Sale orders are non-refundable.")
        policy_result["policy_applies"] = True
    
    if any(k in task_lower for k in ["mã giảm giá", "discount code"]):
         policy_result["exceptions_found"].append("Discounted items may have restricted refund policy.")
         policy_result["policy_applies"] = True

    if any(k in task_lower for k in ["digital", "kỹ thuật số", "key", "tài khoản", "subscription"]):
        policy_result["exceptions_found"].append("Digital products and subscriptions are non-refundable.")
        policy_result["policy_applies"] = True

    if any(k in task_lower for k in ["kích hoạt", "activated", "mở seal", "opened"]):
        policy_result["exceptions_found"].append("Activated or opened products are non-refundable.")
        policy_result["policy_applies"] = True

    # Trích xuất nguồn nếu có chunks
    policy_result["source"] = list({c.get("source") for c in chunks if c.get("source")})

    return policy_result


# ─────────────────────────────────────────────
# Worker Entry Point
# ─────────────────────────────────────────────

def run(state: dict) -> dict:
    """
    Policy Tool Worker:
    - Nhận task và retrieved_chunks.
    - Gọi MCP tool 'check_access_permission' nếu liên quan đến quyền.
    - Gọi 'search_kb' bổ sung nếu cần context sâu hơn.
    - Thực hiện analyze_policy với rule-based logic.
    """
    task = state.get("task", "")
    chunks = state.get("retrieved_chunks", [])
    start_time = datetime.now()

    state.setdefault("workers_called", [])
    state.setdefault("history", [])
    if WORKER_NAME not in state["workers_called"]:
        state["workers_called"].append(WORKER_NAME)

    worker_io = {
        "worker": WORKER_NAME,
        "input": {"task": task, "chunks_count": len(chunks), "needs_tool": state.get("needs_tool", False)},
        "output": None,
        "timestamp": start_time.isoformat(),
    }

    try:
        # 1. Gọi MCP tool nếu cần (Example: search_kb bổ sung hoặc check permissions)
        # Giả định supervisor set needs_tool=True ở Sprint 3
        if state.get("needs_tool"):
            # Gọi bổ sung KB search nếu context ban đầu ít
            if len(chunks) < 2:
                mcp_result = _call_mcp_tool("search_kb", {"query": task, "top_k": 3})
                if mcp_result.get("output") and mcp_result["output"].get("chunks"):
                    chunks = mcp_result["output"]["chunks"]
                    state["retrieved_chunks"] = chunks
                    state["history"].append(f"[{WORKER_NAME}] called MCP search_kb")
                    state.setdefault("mcp_tools_used", []).append("search_kb")

            # Check permissions nếu task liên quan đến access control
            if any(k in task.lower() for k in ["access", "quyền", "permission", "level"]):
                # Logic giả định để extract level từ task
                lvl_match = re.search(r"level\s*(\d)", task.lower())
                requested_lvl = int(lvl_match.group(1)) if lvl_match else 1
                
                perm_result = _call_mcp_tool("check_access_permission", {
                    "access_level": requested_lvl,
                    "requester_role": "employee", # Mock
                    "is_emergency": "khẩn cấp" in task.lower() or "emergency" in task.lower()
                })
                state.setdefault("mcp_tools_used", []).append("check_access_permission")
                state["history"].append(f"[{WORKER_NAME}] called MCP check_access_permission level={requested_lvl}")
                
                # Append perm info to explanation later or use it in results
                if perm_result.get("output"):
                    state["policy_result"] = perm_result["output"]
                    state["policy_result"]["policy_applies"] = True

        # 2. Chức năng chính: Analyze Policy
        if "policy_result" not in state or not state["policy_result"]:
            result = analyze_policy(task, chunks)
            state["policy_result"] = result
            state["history"].append(
                f"[{WORKER_NAME}] policy_applies={result['policy_applies']}, exceptions={len(result['exceptions_found'])}"
            )

        worker_io["output"] = {
            "policy_applies": state["policy_result"].get("policy_applies", False),
            "exceptions_count": len(state["policy_result"].get("exceptions_found", [])),
            "mcp_calls": len(state.get("mcp_tools_used", [])),
            "chunks_used": len(chunks)
        }

    except Exception as e:
        worker_io["error"] = {"code": "POLICY_WORKER_FAILED", "reason": str(e)}
        state["policy_result"] = {"error": str(e)}
        state["history"].append(f"[{WORKER_NAME}] ERROR: {e}")

    worker_io["latency_ms"] = int((datetime.now() - start_time).total_seconds() * 1000)
    state.setdefault("worker_io_logs", []).append(worker_io)
    return state


if __name__ == "__main__":
    # Test độc lập
    test_state = {
        "task": "Khách hàng mua hàng Flash Sale muốn hoàn tiền vì lỗi sản xuất?",
        "retrieved_chunks": [
            {"text": "Flash Sale orders are non-refundable.", "source": "policy_v4.txt", "score": 0.9}
        ],
        "needs_tool": True
    }
    final_state = run(test_state)
    print(f"Policy Applies: {final_state['policy_result']['policy_applies']}")
    print(f"Exceptions: {final_state['policy_result']['exceptions_found']}")
    print(f"Log: {final_state['worker_io_logs']}")
