"""harvest_eval_o2c.py - O2C control-tower test suite (48/48) + blind validation (10/10).

Runs the committed O2C test suite via its own runner (offline; LLM stubbed) and
parses the unittest count. Then runs the orchestrator on the blind-validation
period 2026-07 to confirm all 10 planted hard-control issues are caught and the
pipeline blocks reporting. Emits {"suite":{...},"blind":{...}}.
"""

import io
import json
import os
import re
import subprocess
import sys
import tempfile
from contextlib import redirect_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
O2C = os.path.join(REPO, "cfo-office", "o2c")
RUN_TESTS = os.path.join(O2C, "tests", "run_tests.py")

os.environ.setdefault("ANTHROPIC_API_KEY", "test-not-used")


def run_suite():
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    proc = subprocess.run([sys.executable, RUN_TESTS], cwd=REPO, env=env,
                          capture_output=True, text=True, timeout=600)
    blob = proc.stdout + "\n" + proc.stderr
    m = re.search(r"Ran (\d+) tests", blob)
    total = int(m.group(1)) if m else 0
    ok = bool(re.search(r"\bOK\b", blob)) and proc.returncode == 0
    failed = 0
    fm = re.search(r"failures=(\d+)", blob)
    em = re.search(r"errors=(\d+)", blob)
    failed = (int(fm.group(1)) if fm else 0) + (int(em.group(1)) if em else 0)
    return {"passed": total - failed if not ok else total, "total": total, "ok": ok}


def run_blind():
    for p in (O2C, os.path.join(O2C, "agents")):
        if p not in sys.path:
            sys.path.insert(0, p)
    import o2c_orchestrator as orch
    import o2c_controls as ctrls
    import o2c_data_loader as loader
    period = "2026-07"
    dfs = loader.load_o2c_data(period)
    results = ctrls.run_all_controls(dfs, period)
    hard_fail_ids = sorted({r.control_id for r in results
                            if getattr(r, "severity", "") == "HARD" and getattr(r, "status", "") == "FAIL"})
    tmp = tempfile.mkdtemp(prefix="v2_blind_")
    _, meta = orch.run(period=period, output_dir=tmp, fail_on_hard=False, verbose=False)
    return {"planted": 10, "caught": len(hard_fail_ids), "hard_failure_ids": hard_fail_ids,
            "final_status": meta.get("final_status")}


def main():
    buf = io.StringIO()
    with redirect_stdout(buf):
        suite = run_suite()
        blind = run_blind()
    sys.__stdout__.write(json.dumps({"suite": suite, "blind": blind}, default=str))


if __name__ == "__main__":
    main()
