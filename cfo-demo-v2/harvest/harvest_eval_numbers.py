"""harvest_eval_numbers.py - the deterministic Numbers regression eval (22/22).

Runs evals/eval_runner.suite_numbers() fully offline (finance_core only, no
model) against a clean parameter store, captures the per-check pass/fail lines.
Emits {"passed","total","checks":[{"label","ok"}]}.
"""

import io
import json
import os
import re
import sys
import tempfile
from contextlib import redirect_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))

# Force documented default parameters (no champions store) so the eval matches
# the ground-truth answer key.
os.environ["SELFIMPROVE_STATE_DIR"] = tempfile.mkdtemp(prefix="v2_eval_state_")

for p in ("orchestration", "document-intelligence", "evals"):
    sys.path.insert(0, os.path.join(REPO, p))

import eval_runner as er  # noqa: E402


def main():
    buf = io.StringIO()
    with redirect_stdout(buf):
        passed, total = er.suite_numbers()
    checks = []
    for line in buf.getvalue().splitlines():
        m = re.search(r"\[(PASS|FALLA)\]\s*(.*)", line)
        if m:
            label = m.group(2).strip()
            checks.append({"label": label, "ok": m.group(1) == "PASS"})
    result = {"passed": passed, "total": total, "checks": checks}
    sys.__stdout__.write(json.dumps(result, default=str))


if __name__ == "__main__":
    main()
