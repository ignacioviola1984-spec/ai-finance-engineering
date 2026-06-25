"""harvest_o2c.py - Station 2 (Order-to-Cash control tower) snapshot.

Runs the O2C sub-orchestrator end to end for the broken month (2026-05) and the
clean month (2026-06), capturing the full deterministic result for each: final
status + audit opinion, the controls register (25), the governed metrics (35),
AR aging, the bookings->cash bridge, the executive summary, and the top
severity-ranked issues from the 10 agents. No network, no API keys (the agents
are deterministic Python; any LLM narration is stubbed).

Emits one JSON object to stdout: {"2026-05": {...}, "2026-06": {...}}.
"""

import dataclasses
import io
import json
import os
import sys
import tempfile
from contextlib import redirect_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
O2C = os.path.join(REPO, "cfo-office", "o2c")
for p in (O2C, os.path.join(O2C, "agents")):
    sys.path.insert(0, p)

os.environ.setdefault("ANTHROPIC_API_KEY", "test-not-used")  # construct-only, never called

import o2c_orchestrator as orch  # noqa: E402

PERIODS = ("2026-05", "2026-06")


def _as_dict(obj):
    if dataclasses.is_dataclass(obj):
        return dataclasses.asdict(obj)
    return dict(getattr(obj, "__dict__", {}))


def _num(x):
    try:
        return round(float(x), 2)
    except (TypeError, ValueError):
        return x


def harvest_period(period):
    tmp = tempfile.mkdtemp(prefix="v2_o2c_")
    ctx, meta = orch.run(period=period, output_dir=tmp, fail_on_hard=False, verbose=False)
    calc = ctx.calc
    cs = calc["controls_summary"]
    summary = calc["summary"]

    # controls register (compact)
    controls = []
    for c in calc["controls"]:
        d = _as_dict(c)
        controls.append({
            "control_id": d.get("control_id"), "name": d.get("control_name"),
            "severity": d.get("severity"), "status": d.get("status"),
            "owner": d.get("owner"), "failing_amount_usd": _num(d.get("failing_amount_usd", 0)),
            "failing_count": d.get("failing_record_count", 0),
            "blocks_reporting": d.get("blocks_reporting", False),
            "action": d.get("recommended_action", ""),
            "description": d.get("description", ""),
        })

    # governed metrics (compact)
    metrics = []
    for m in calc["metrics"]:
        d = _as_dict(m)
        metrics.append({
            "name": d.get("metric_name"), "value": _num(d.get("value")),
            "unit": d.get("currency"), "status": d.get("status"),
            "owner": d.get("owner"), "threshold": _num(d.get("threshold")),
            "definition": d.get("business_definition", ""),
        })

    # AR aging
    aging = calc.get("aging", {})
    by_bucket = aging.get("by_bucket")
    aging_rows = by_bucket.to_dict("records") if by_bucket is not None and hasattr(by_bucket, "to_dict") else []
    for r in aging_rows:
        for k in list(r):
            r[k] = _num(r[k]) if isinstance(r[k], (int, float)) else r[k]

    # bookings -> cash bridge
    bridge_raw = calc.get("bridge", {})
    bridge = bridge_raw.get("bridge", bridge_raw) if isinstance(bridge_raw, dict) else bridge_raw
    bridge = [[label, _num(amt)] for label, amt in bridge] if bridge else []

    # top issues from the agents
    try:
        escal = ctx.escalations()
    except Exception:
        escal = []
    top_issues = [{"agent": e.get("agent"), "severity": e.get("severity"), "message": e.get("message")}
                  for e in escal[:10]]
    sev_counts = {}
    for e in escal:
        sev_counts[e.get("severity", "?")] = sev_counts.get(e.get("severity", "?"), 0) + 1

    # one-line headline per agent
    agents = []
    for name, f in (ctx.findings or {}).items():
        headline = ""
        if isinstance(f, dict):
            headline = f.get("headline") or f.get("summary") or ""
            if not headline:
                esc = f.get("escalations") or []
                if esc and isinstance(esc[0], dict):
                    headline = esc[0].get("message", "")
        agents.append({"name": name, "headline": headline})

    return {
        "period": period,
        "final_status": meta.get("final_status"),
        "audit_opinion": meta.get("audit_opinion"),
        "audit_score": _num(meta.get("audit_score")),
        "blocks_reporting": cs.get("blocks_reporting"),
        "controls_summary": {
            "total": cs.get("total"), "hard": cs.get("hard"), "soft": cs.get("soft"),
            "hard_failures": cs.get("hard_failures"), "soft_warnings": cs.get("soft_warnings"),
            "pass_count": cs.get("pass_count"), "pass_rate_pct": _num(cs.get("control_pass_rate_pct")),
            "hard_failure_ids": cs.get("hard_failure_ids", []),
        },
        "summary": {
            "open_ar_usd": _num(summary.get("open_ar_usd")),
            "current_ar_usd": _num(summary.get("current_ar_usd")),
            "overdue_ar_usd": _num(summary.get("overdue_ar_usd")),
            "ar_90_plus_usd": _num(summary.get("ar_90_plus_usd")),
            "dso": _num(summary.get("dso")),
            "best_possible_dso": _num(summary.get("best_possible_dso")),
            "billing_completeness_pct": _num(summary.get("billing_completeness_pct")),
            "unbilled_revenue_usd": _num(summary.get("unbilled_revenue_usd")),
            "revenue_leakage_usd": _num(summary.get("revenue_leakage_usd")),
            "cash_application_rate_pct": _num(summary.get("cash_application_rate_pct")),
            "unapplied_cash_usd": _num(summary.get("unapplied_cash_usd")),
            "disputed_ar_usd": _num(summary.get("disputed_ar_usd")),
            "disputed_ar_pct": _num(summary.get("disputed_ar_pct")),
            "credit_exposure_usd": _num(summary.get("credit_exposure_usd")),
            "credit_breach_amount_usd": _num(summary.get("credit_breach_amount_usd")),
            "expected_cash_7d_usd": _num(summary.get("expected_cash_7d_usd")),
            "expected_cash_30d_usd": _num(summary.get("expected_cash_30d_usd")),
            "expected_cash_13w_usd": _num(summary.get("expected_cash_13w_usd")),
            "bookings_usd": _num(summary.get("bookings_usd")),
            "billings_usd": _num(summary.get("billings_usd")),
            "cash_collected_usd": _num(summary.get("cash_collected_usd")),
        },
        "aging": aging_rows,
        "bridge": bridge,
        "controls": controls,
        "metrics": metrics,
        "top_issues": top_issues,
        "severity_counts": sev_counts,
        "agents": agents,
        "input_record_counts": meta.get("input_record_counts", {}),
        "n_agents": len(agents),
    }


def main():
    buf = io.StringIO()
    out = {}
    with redirect_stdout(buf):
        for period in PERIODS:
            out[period] = harvest_period(period)
    sys.__stdout__.write(json.dumps(out, default=str))


if __name__ == "__main__":
    main()
