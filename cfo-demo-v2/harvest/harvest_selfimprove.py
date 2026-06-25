"""harvest_selfimprove.py - Station 5 (bounded self-improvement) snapshot.

Replays the exact sequence in self-improvement/demo.py against an isolated temp
store, capturing structured data: the registry of changeable parameters, the
four steps (accept / reject out-of-bounds / reject eval-regression-despite-human
/ rollback), and the append-only audit trail. No network, no API keys.

Emits one JSON object to stdout.
"""

import io
import json
import os
import sys
import tempfile
from contextlib import redirect_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
SI = os.path.join(REPO, "self-improvement")

# Isolated, reproducible store (never touches the repo's state/).
STATE = tempfile.mkdtemp(prefix="v2_si_state_")
os.environ["SELFIMPROVE_STATE_DIR"] = STATE
sys.path.insert(0, SI)

import registry            # noqa: E402
import propose as proposer  # noqa: E402
import gate as gate_mod     # noqa: E402
import rollback as rollback_mod  # noqa: E402
import audit                # noqa: E402


def _reset_state():
    sd = registry.state_dir()
    for fn in ("champions.json", "proposals.json", "audit_trail.jsonl"):
        p = os.path.join(sd, fn)
        if os.path.exists(p):
            os.remove(p)
    registry.ensure_init()


def _inject(param, proposed, by="proposer"):
    store = proposer.load_proposals()
    store["seq"] += 1
    pid = f"P{store['seq']}"
    store["items"].append({
        "id": pid, "param": param, "old": registry.champion_value(param),
        "proposed": proposed, "raw_candidate": proposed, "evidence": {"note": "raw injected proposal"},
        "rationale": "(injected for demonstration)", "status": "pending", "by": by, "outcomes": [],
    })
    proposer.save_proposals(store)
    audit.record("proposed", f"{param}: {registry.champion_value(param)} -> {proposed} (injected)",
                 proposal_id=pid, param=param, proposed=proposed)
    return pid


def main():
    buf = io.StringIO()
    with redirect_stdout(buf):
        _reset_state()

        params = []
        for n in registry.param_names():
            m = registry.REGISTRY[n]
            params.append({"name": n, "value": registry.champion_value(n),
                           "min": m["min"], "max": m["max"], "max_step": m["max_step"],
                           "cooldown": m.get("cooldown", 1), "owner": m["owner"], "metric": m.get("metric", "")})

        # 1) ACCEPTED
        with open(os.path.join(SI, "demo_data", "ar_outcomes.json"), encoding="utf-8") as f:
            ar_outcomes = json.load(f)["outcomes"]
        p1 = proposer.propose("ar_collection_rate", ar_outcomes, by="proposer")
        res1 = gate_mod.approve(p1["id"], approver="Treasurer")
        step_accept = {
            "param": "ar_collection_rate", "old": p1["old"], "proposed": p1["proposed"],
            "evidence": p1["evidence"], "rationale": p1["rationale"],
            "approver": "Treasurer", "ok": res1["ok"],
            "eval": res1["verdict"]["eval_result"], "backtest": res1["verdict"]["backtest"],
            "new_version": registry.champion_version("ar_collection_rate"),
        }
        registry.bump_cycle()

        # 2) REJECTED - out of bounds
        pid2 = _inject("ar_collection_rate", 1.05)
        res2 = gate_mod.approve(pid2, approver="Treasurer")
        step_oob = {"param": "ar_collection_rate", "old": 0.92, "proposed": 1.05,
                    "bounds": [registry.REGISTRY["ar_collection_rate"]["min"],
                               registry.REGISTRY["ar_collection_rate"]["max"]],
                    "approver": "Treasurer", "ok": res2["ok"], "reasons": res2["reasons"],
                    "champion_after": registry.champion_value("ar_collection_rate")}

        # 3) REJECTED - eval regression despite human approval
        pid3 = _inject("materiality_usd_threshold", 25000.0)
        res3 = gate_mod.approve(pid3, approver="Controller")
        step_regress = {"param": "materiality_usd_threshold", "old": 20000.0, "proposed": 25000.0,
                        "approver": "Controller", "ok": res3["ok"], "reasons": res3["reasons"],
                        "champion_after": registry.champion_value("materiality_usd_threshold")}

        # 4) ROLLBACK
        before = registry.champion_value("ar_collection_rate")
        res4 = rollback_mod.rollback("ar_collection_rate", 1, by="Treasurer")
        step_rollback = {"param": "ar_collection_rate", "before": before,
                         "after": registry.champion_value("ar_collection_rate"),
                         "result": res4}

        trail = []
        for e in audit.read_all():
            trail.append({"ts": e["ts"], "action": e["action"], "detail": e["detail"]})

    result = {
        "params": params,
        "accept": step_accept,
        "reject_out_of_bounds": step_oob,
        "reject_eval_regression": step_regress,
        "rollback": step_rollback,
        "audit_trail": trail,
    }
    sys.__stdout__.write(json.dumps(result, default=str))


if __name__ == "__main__":
    main()
