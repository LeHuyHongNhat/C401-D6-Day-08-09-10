"""
eval_trace.py — Trace Evaluation & Comparison
Sprint 4: Chạy pipeline với test questions, phân tích trace, so sánh single vs multi.

Chạy:
    python eval_trace.py                  # Chạy 15 test questions
    python eval_trace.py --grading        # Chạy grading questions (sau 17:00)
    python eval_trace.py --analyze        # Phân tích trace đã có
    python eval_trace.py --compare        # So sánh single vs multi
    python eval_trace.py --compare --day08-results day08/lab/results/day08_single_agent_metrics.json

Outputs:
    artifacts/traces/          — trace của từng câu hỏi
    artifacts/grading_run.jsonl — log câu hỏi chấm điểm
    artifacts/eval_report.json  — báo cáo tổng kết
"""

import csv
import json
import os
import sys
import argparse
from datetime import datetime
from typing import Any, Optional

# Import graph
_LAB_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _LAB_ROOT)
from graph import run_graph, save_trace


def _lab_path(path: str) -> str:
    """Đường dẫn tương đối repo/CWD → luôn resolve theo thư mục day09/lab (file này)."""
    if os.path.isabs(path):
        return os.path.normpath(path)
    return os.path.normpath(os.path.join(_LAB_ROOT, path))


def _repo_root() -> str:
    """Root của repo (cha của day09/lab)."""
    return os.path.normpath(os.path.join(_LAB_ROOT, "..", ".."))


def _default_day08_json_paths() -> list[str]:
    """Các file JSON metrics Day 08 (ưu tiên từ trên xuống)."""
    r = _repo_root()
    return [
        os.path.join(r, "day08", "lab", "results", "day08_single_agent_metrics.json"),
        _lab_path(os.path.join("artifacts", "day08_baseline.json")),
    ]


def _day08_ab_csv_path() -> str:
    return os.path.join(_repo_root(), "day08", "lab", "results", "ab_comparison_test_questions.csv")


def _day08_test_questions_path() -> str:
    return os.path.join(_repo_root(), "day08", "lab", "data", "test_questions.json")


def _load_day08_metrics_from_json(path: str) -> Optional[dict[str, Any]]:
    if not os.path.isfile(path):
        return None
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    if not isinstance(raw, dict):
        return None
    out: dict[str, Any] = dict(raw)
    out.setdefault("source", path)
    return out


def _load_day08_from_ab_csv() -> Optional[dict[str, Any]]:
    """
    Tổng hợp metrics Day 08 từ CSV A/B (cùng bộ câu test) — hàng config_label=baseline_dense.
    Không có latency (single-agent CSV không ghi) → để None.
    """
    csv_path = _day08_ab_csv_path()
    if not os.path.isfile(csv_path):
        return None

    meta_by_id: dict[str, dict[str, Any]] = {}
    tq = _day08_test_questions_path()
    if os.path.isfile(tq):
        with open(tq, encoding="utf-8") as f:
            for q in json.load(f):
                meta_by_id[q["id"]] = q

    baseline_rows: list[dict[str, str]] = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row.get("config_label") == "baseline_dense":
                baseline_rows.append(row)

    if not baseline_rows:
        return None

    # Chỉ lấy một bản mỗi id (CSV có thể lặp baseline+variant)
    seen: set[str] = set()
    uniq: list[dict[str, str]] = []
    for row in baseline_rows:
        qid = row.get("id", "")
        if not qid or qid in seen:
            continue
        seen.add(qid)
        uniq.append(row)

    metrics = ("faithfulness", "relevance", "context_recall", "completeness")

    def _avg(key: str) -> float:
        vals: list[float] = []
        for row in uniq:
            try:
                vals.append(float(row[key]))
            except (TypeError, ValueError, KeyError):
                pass
        return round(sum(vals) / len(vals), 4) if vals else 0.0

    avgs = {m: _avg(m) for m in metrics}
    # Proxy 0–1 để so sánh với confidence Day 09 (cùng thang gần đúng)
    avg_quality_0_1 = round(
        sum(avgs[m] for m in metrics) / (4 * 5),
        4,
    )

    # Abstain: category Insufficient Context
    abstain = [r for r in uniq if r.get("category") == "Insufficient Context"]
    abstain_ok = 0
    for r in abstain:
        ans = (r.get("answer") or "").lower()
        if (
            "không tìm thấy" in ans
            or "không đủ" in ans
            or "không có thông tin" in ans
        ):
            abstain_ok += 1
    abstain_rate: str
    if abstain:
        pct = round(100 * abstain_ok / len(abstain))
        abstain_rate = f"{abstain_ok}/{len(abstain)} ({pct}%)"
    else:
        abstain_rate = "N/A (không có câu abstain trong tập)"

    # Multi-hop proxy: độ khó hard trong test_questions
    hard_ids = {i for i, m in meta_by_id.items() if m.get("difficulty") == "hard"}
    hard_rows = [r for r in uniq if r.get("id") in hard_ids]
    if hard_rows:
        hc = [_float_row(r, "completeness") for r in hard_rows]
        hc = [x for x in hc if x is not None]
        mh = round(sum(hc) / len(hc) / 5.0, 4) if hc else None
        multi_hop_accuracy = f"{mh:.2f} (trung bình completeness/5 trên {len(hard_rows)} câu hard)" if mh is not None else "N/A"
    else:
        multi_hop_accuracy = "N/A"

    return {
        "total_questions": len(uniq),
        "avg_confidence": avg_quality_0_1,
        "avg_confidence_note": "Trung bình (faithfulness+relevance+context_recall+completeness)/20 — proxy so với confidence Day 09",
        "avg_latency_ms": None,
        "avg_scores": avgs,
        "abstain_rate": abstain_rate,
        "multi_hop_accuracy": multi_hop_accuracy,
        "source": f"derived:{os.path.basename(csv_path)} (baseline_dense)",
    }


def _float_row(row: dict[str, str], key: str) -> Optional[float]:
    try:
        return float(row[key])
    except (TypeError, ValueError, KeyError):
        return None


def _merge_analysis_deltas(
    day08: dict[str, Any],
    multi: dict[str, Any],
) -> dict[str, str]:
    """Tính chênh lệch số liệu Day 09 vs Day 08 (khi đủ dữ liệu)."""
    m_conf = multi.get("avg_confidence")
    d_conf = day08.get("avg_confidence")

    m_lat = multi.get("avg_latency_ms")
    d_lat = day08.get("avg_latency_ms")

    lines: dict[str, str] = {}

    if isinstance(m_conf, (int, float)) and isinstance(d_conf, (int, float)):
        delta = float(m_conf) - float(d_conf)
        lines["confidence_delta"] = (
            f"avg proxy: Day09={m_conf:.3f} vs Day08={d_conf:.3f} → Δ {delta:+.3f} "
            f"(confidence multi-agent vs điểm chất lượng 0–1 từ scorecard Day 08)"
        )
    elif isinstance(m_conf, (int, float)) and d_conf is None:
        lines["confidence_delta"] = (
            f"Day09 avg confidence={m_conf:.3f}; Day08 thiếu baseline — thêm JSON hoặc ab_comparison_test_questions.csv."
        )
    else:
        lines["confidence_delta"] = (
            "Chưa so sánh được: thiếu avg_confidence Day 08 (tạo day08/lab/results/day08_single_agent_metrics.json "
            "hoặc đảm bảo có ab_comparison_test_questions.csv)."
        )

    if isinstance(m_lat, (int, float)) and isinstance(d_lat, (int, float)):
        dlt = int(m_lat) - int(d_lat)
        slower = "chậm hơn" if dlt > 0 else "nhanh hơn" if dlt < 0 else "tương đương"
        lines["latency_delta"] = (
            f"avg latency: Day09={int(m_lat)}ms vs Day08={int(d_lat)}ms → Δ {dlt:+d}ms (Day09 {slower} Day08)"
        )
    elif isinstance(m_lat, (int, float)):
        lines["latency_delta"] = (
            f"Day09 avg latency={int(m_lat)}ms; Day08 không có latency trong CSV — chạy Day 08 với instrument hoặc bổ sung JSON."
        )
    else:
        lines["latency_delta"] = "Thiếu latency trung bình Day 09 (chưa có trace) hoặc Day 08."

    lines["routing_visibility"] = (
        "Day 09: mỗi trace có supervisor_route + route_reason + workers_called → debug routing dễ hơn Day 08 (single agent không tách bước)."
    )
    lines["debuggability"] = (
        "Multi-agent: test độc lập retrieval / policy / synthesis. Single-agent: chỉ một pipeline RAG."
    )
    lines["mcp_benefit"] = (
        "Day 09 mở rộng qua MCP tools; Day 08 cần sửa code pipeline nếu thêm nguồn/tool."
    )
    lines["accuracy_delta"] = (
        "Độ chính xác theo rubric grading: so khớp grading_run.jsonl sau khi chấm — không thay bằng confidence tự động."
    )

    return lines


def _resolve_metrics_path(p: str) -> str:
    """Resolve path metrics: abs, hoặc repo-relative (day08/..., day09/...), hoặc relative day09/lab."""
    if os.path.isabs(p):
        return os.path.normpath(p)
    if p.startswith(("day08/", "day09/")):
        return os.path.normpath(os.path.join(_repo_root(), p))
    return _lab_path(p)


def _load_day08_baseline(day08_results_file: Optional[str]) -> dict[str, Any]:
    """Ưu tiên: file truyền vào → JSON mặc định → suy ra từ CSV Day 08."""
    if day08_results_file:
        p = _resolve_metrics_path(day08_results_file)
        loaded = _load_day08_metrics_from_json(p)
        if loaded:
            return loaded
    for p in _default_day08_json_paths():
        loaded = _load_day08_metrics_from_json(p)
        if loaded:
            return loaded
    derived = _load_day08_from_ab_csv()
    if derived:
        return derived
    return {
        "total_questions": 15,
        "avg_confidence": None,
        "avg_latency_ms": None,
        "abstain_rate": "N/A",
        "multi_hop_accuracy": "N/A",
        "source": "not_found — chạy Day08 eval để tạo CSV hoặc nộp day08_single_agent_metrics.json",
    }


# ─────────────────────────────────────────────
# 1. Run Pipeline on Test Questions
# ─────────────────────────────────────────────

def run_test_questions(questions_file: str = "data/test_questions.json") -> list:
    """
    Chạy pipeline với danh sách câu hỏi, lưu trace từng câu.

    Returns:
        list of (question, result) tuples
    """
    questions_file = _lab_path(questions_file)
    with open(questions_file, encoding="utf-8") as f:
        questions = json.load(f)

    print(f"\n📋 Running {len(questions)} test questions from {questions_file}")
    print("=" * 60)

    results = []
    for i, q in enumerate(questions, 1):
        question_text = q["question"]
        q_id = q.get("id", f"q{i:02d}")

        print(f"[{i:02d}/{len(questions)}] {q_id}: {question_text[:65]}...")

        try:
            result = run_graph(question_text)
            result["question_id"] = q_id

            # Save individual trace
            trace_file = save_trace(result, _lab_path("artifacts/traces"))
            print(f"  ✓ route={result.get('supervisor_route', '?')}, "
                  f"conf={result.get('confidence', 0):.2f}, "
                  f"{result.get('latency_ms', 0)}ms")

            results.append({
                "id": q_id,
                "question": question_text,
                "expected_answer": q.get("expected_answer", ""),
                "expected_sources": q.get("expected_sources", []),
                "difficulty": q.get("difficulty", "unknown"),
                "category": q.get("category", "unknown"),
                "result": result,
            })

        except Exception as e:
            print(f"  ✗ ERROR: {e}")
            results.append({
                "id": q_id,
                "question": question_text,
                "error": str(e),
                "result": None,
            })

    print(f"\n✅ Done. {sum(1 for r in results if r.get('result'))} / {len(results)} succeeded.")
    return results


# ─────────────────────────────────────────────
# 2. Run Grading Questions (Sprint 4)
# ─────────────────────────────────────────────

def run_grading_questions(questions_file: str = "data/grading_questions.json") -> str:
    """
    Chạy pipeline với grading questions và lưu JSONL log.
    Dùng cho chấm điểm nhóm (chạy sau khi grading_questions.json được public lúc 17:00).

    Returns:
        path tới grading_run.jsonl
    """
    questions_file = _lab_path(questions_file)
    if not os.path.exists(questions_file):
        print(f"❌ {questions_file} chưa được public (sau 17:00 mới có).")
        return ""

    with open(questions_file, encoding="utf-8") as f:
        questions = json.load(f)

    output_file = _lab_path("artifacts/grading_run.jsonl")
    os.makedirs(os.path.dirname(output_file), exist_ok=True)

    print(f"\n🎯 Running GRADING questions — {len(questions)} câu")
    print(f"   Output → {output_file}")
    print("=" * 60)

    with open(output_file, "w", encoding="utf-8") as out:
        for i, q in enumerate(questions, 1):
            q_id = q.get("id", f"gq{i:02d}")
            question_text = q["question"]
            print(f"[{i:02d}/{len(questions)}] {q_id}: {question_text[:65]}...")

            try:
                result = run_graph(question_text)
                # Ưu tiên sources từ synthesis (cite trong answer); fallback retrieved_sources
                _cite = result.get("sources") or []
                _ret = result.get("retrieved_sources") or []
                _merged = list(dict.fromkeys([*(_cite or []), *(_ret or [])]))
                record = {
                    "id": q_id,
                    "question": question_text,
                    "answer": result.get("final_answer", "PIPELINE_ERROR: no answer"),
                    "sources": _merged if _merged else (_cite or _ret or []),
                    "supervisor_route": result.get("supervisor_route", "") or "MISSING",
                    "route_reason": result.get("route_reason", "") or "MISSING",
                    "workers_called": result.get("workers_called", []),
                    "mcp_tools_used": result.get("mcp_tools_used", []),
                    "confidence": result.get("confidence", 0.0),
                    "hitl_triggered": result.get("hitl_triggered", False),
                    "latency_ms": result.get("latency_ms"),
                    "timestamp": datetime.now().isoformat(),
                }
                if record["supervisor_route"] == "MISSING":
                    print(f"  ⚠️ WARNING [{q_id}]: supervisor_route missing — sẽ bị trừ 20%/câu")
                if record["route_reason"] == "MISSING":
                    print(f"  ⚠️ WARNING [{q_id}]: route_reason missing — sẽ bị trừ 20%/câu")
                if not record["workers_called"]:
                    print(f"  ⚠️ WARNING [{q_id}]: workers_called missing (required)")
                print(f"  ✓ route={record['supervisor_route']}, conf={record['confidence']:.2f}")
            except Exception as e:
                record = {
                    "id": q_id,
                    "question": question_text,
                    "answer": f"PIPELINE_ERROR: {e}",
                    "sources": [],
                    "supervisor_route": "error",
                    "route_reason": str(e),
                    "workers_called": [],
                    "mcp_tools_used": [],
                    "confidence": 0.0,
                    "hitl_triggered": False,
                    "latency_ms": None,
                    "timestamp": datetime.now().isoformat(),
                }
                print(f"  ✗ ERROR: {e}")

            out.write(json.dumps(record, ensure_ascii=False) + "\n")

    print(f"\n✅ Grading log saved → {output_file}")
    return output_file


# ─────────────────────────────────────────────
# 3. Analyze Traces
# ─────────────────────────────────────────────

def analyze_traces(traces_dir: str = "artifacts/traces") -> dict:
    """
    Đọc tất cả trace files và tính metrics tổng hợp.

    Metrics:
    - routing_distribution: % câu đi vào mỗi worker
    - avg_confidence: confidence trung bình
    - avg_latency_ms: latency trung bình
    - mcp_usage_rate: % câu có MCP tool call
    - hitl_rate: % câu trigger HITL
    - source_coverage: các tài liệu nào được dùng nhiều nhất

    Returns:
        dict of metrics
    """
    traces_dir = _lab_path(traces_dir)
    if not os.path.exists(traces_dir):
        print(f"⚠️  {traces_dir} không tồn tại. Chạy run_test_questions() trước.")
        return {}

    trace_files = [f for f in os.listdir(traces_dir) if f.endswith(".json")]
    if not trace_files:
        print(f"⚠️  Không có trace files trong {traces_dir}.")
        return {}

    traces = []
    for fname in trace_files:
        fpath = os.path.join(traces_dir, fname)
        if os.path.getsize(fpath) == 0:
            continue
        with open(fpath) as f:
            try:
                traces.append(json.load(f))
            except json.JSONDecodeError:
                print(f"⚠️  Skipping invalid JSON: {fname}")
                continue

    # Compute metrics
    routing_counts = {}
    confidences = []
    latencies = []
    mcp_calls = 0
    hitl_triggers = 0
    source_counts = {}

    for t in traces:
        route = t.get("supervisor_route", "unknown")
        routing_counts[route] = routing_counts.get(route, 0) + 1

        conf = t.get("confidence", 0)
        if conf:
            confidences.append(conf)

        lat = t.get("latency_ms")
        if lat:
            latencies.append(lat)

        if t.get("mcp_tools_used"):
            mcp_calls += 1

        if t.get("hitl_triggered"):
            hitl_triggers += 1

        for src in t.get("retrieved_sources", []):
            source_counts[src] = source_counts.get(src, 0) + 1

    total = len(traces)
    metrics = {
        "total_traces": total,
        "routing_distribution": {k: f"{v}/{total} ({100*v//total}%)" for k, v in routing_counts.items()},
        "avg_confidence": round(sum(confidences) / len(confidences), 3) if confidences else 0,
        "avg_latency_ms": round(sum(latencies) / len(latencies)) if latencies else 0,
        "mcp_usage_rate": f"{mcp_calls}/{total} ({100*mcp_calls//total}%)" if total else "0%",
        "hitl_rate": f"{hitl_triggers}/{total} ({100*hitl_triggers//total}%)" if total else "0%",
        "top_sources": sorted(source_counts.items(), key=lambda x: -x[1])[:5],
    }

    return metrics


# ─────────────────────────────────────────────
# 4. Compare Single vs Multi Agent
# ─────────────────────────────────────────────

def compare_single_vs_multi(
    multi_traces_dir: str = "artifacts/traces",
    day08_results_file: Optional[str] = None,
) -> dict:
    """
    So sánh Day 08 (single-agent RAG) vs Day 09 (multi-agent).

    Nguồn Day 08 (theo thứ tự):
    1. `day08_results_file` nếu truyền vào và tồn tại (JSON).
    2. `day08/lab/results/day08_single_agent_metrics.json`
    3. `day09/lab/artifacts/day08_baseline.json`
    4. Suy ra từ `day08/lab/results/ab_comparison_test_questions.csv` (hàng baseline_dense).

    JSON gợi ý cho (1–3), có thể thêm tay sau khi chạy Day08 eval:
    {
      "total_questions": 15,
      "avg_confidence": 0.82,
      "avg_latency_ms": 2100,
      "abstain_rate": "2/2 (100%)",
      "multi_hop_accuracy": "0.75"
    }

    Returns:
        dict có day08_single_agent, day09_multi_agent, analysis (delta có điều kiện).
    """
    multi_metrics = analyze_traces(multi_traces_dir)
    day08_baseline = _load_day08_baseline(day08_results_file)

    analysis = _merge_analysis_deltas(day08_baseline, multi_metrics)

    return {
        "generated_at": datetime.now().isoformat(),
        "day08_single_agent": day08_baseline,
        "day09_multi_agent": multi_metrics,
        "analysis": analysis,
    }


# ─────────────────────────────────────────────
# 5. Save Eval Report
# ─────────────────────────────────────────────

def save_eval_report(comparison: dict) -> str:
    """Lưu báo cáo eval tổng kết ra file JSON."""
    output_file = _lab_path("artifacts/eval_report.json")
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(comparison, f, ensure_ascii=False, indent=2)
    return output_file


# ─────────────────────────────────────────────
# 6. CLI Entry Point
# ─────────────────────────────────────────────

def run_smoke_test():
    """Chạy 3 câu smoke test và in ra warning."""
    SMOKE_TESTS = [
        ("sq01", "SLA ticket P1 là bao lâu?"),
        ("sq02", "Khách hàng Flash Sale yêu cầu hoàn tiền"),
        ("sq03", "Mức phạt tài chính vi phạm SLA P1?"),
    ]
    print("\n💨 Running SMOKE TESTS")
    print("=" * 60)
    for q_id, text in SMOKE_TESTS:
        print(f"\n▶ Query [{q_id}]: {text}")
        try:
            res = run_graph(text)
            r_route = res.get("supervisor_route", "")
            r_reason = res.get("route_reason", "")
            w_called = res.get("workers_called", [])
            print(f"  Route: {r_route}")
            print(f"  Reason: {r_reason}")
            print(f"  Workers: {w_called}")
            
            if not r_route or r_route == "MISSING":
                print(f"  ⚠️ WARNING: supervisor_route is MISSING!")
            if not r_reason or r_reason == "MISSING":
                print(f"  ⚠️ WARNING: route_reason is MISSING!")
            if not w_called:
                print(f"  ⚠️ WARNING: workers_called is empty!")
            answer = res.get('final_answer') or ""
            print(f"  Answer: {answer[:60]}...")
        except Exception as e:
            print(f"  ❌ ERROR: {e}")
    print("\n✅ Smoke tests done.")

def print_metrics(metrics: dict):
    """Print metrics đẹp."""
    if not metrics:
        return
    print("\n📊 Trace Analysis:")
    for k, v in metrics.items():
        if isinstance(v, list):
            print(f"  {k}:")
            for item in v:
                print(f"    • {item}")
        elif isinstance(v, dict):
            print(f"  {k}:")
            for kk, vv in v.items():
                print(f"    {kk}: {vv}")
        else:
            print(f"  {k}: {v}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Day 09 Lab — Trace Evaluation")
    parser.add_argument("--grading", action="store_true", help="Run grading questions")
    parser.add_argument("--analyze", action="store_true", help="Analyze existing traces")
    parser.add_argument("--compare", action="store_true", help="Compare single vs multi")
    parser.add_argument("--smoke-test", action="store_true", help="Run quick smoke test")
    parser.add_argument("--test-file", default="data/test_questions.json", help="Test questions file")
    parser.add_argument(
        "--day08-results",
        default=None,
        metavar="PATH",
        help="JSON metrics Day 08 (tùy chọn). Mặc định: day08/lab/results/day08_single_agent_metrics.json hoặc suy từ ab_comparison CSV.",
    )
    args = parser.parse_args()

    if args.grading:
        # Chạy grading questions
        log_file = run_grading_questions()
        if log_file:
            print(f"\n✅ Grading log: {log_file}")
            print("   Nộp file này trước 18:00!")

    elif args.smoke_test:
        run_smoke_test()

    elif args.analyze:
        # Phân tích traces
        metrics = analyze_traces()
        print_metrics(metrics)

    elif args.compare:
        # So sánh single vs multi
        comparison = compare_single_vs_multi(day08_results_file=args.day08_results)
        report_file = save_eval_report(comparison)
        print(f"\n📊 Comparison report saved → {report_file}")
        print("\n=== Day 08 vs Day 09 ===")
        for k, v in comparison.get("analysis", {}).items():
            print(f"  {k}: {v}")

    else:
        # Default: chạy test questions
        results = run_test_questions(args.test_file)

        # Phân tích trace
        metrics = analyze_traces()
        print_metrics(metrics)

        # Lưu báo cáo
        comparison = compare_single_vs_multi(day08_results_file=args.day08_results)
        report_file = save_eval_report(comparison)
        print(f"\n📄 Eval report → {report_file}")
        print("\n✅ Sprint 4 complete!")
        print("   Next: Điền docs/ templates và viết reports/")
