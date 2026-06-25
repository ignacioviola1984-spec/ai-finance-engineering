"""harvest_eval_dlocal.py - real-data audit vs dLocal (NASDAQ: DLO) SEC filings (17/17).

Regenerates model_output.csv from the public input CSVs, then diffs all 17
figures against the SEC-derived answer key with the repo's tolerances
(USD_000 +/-1, pct +/-0.1). Emits {"passed","total","rows":[...],"headline":{...}}.
"""

import csv
import io
import json
import os
import sys
from contextlib import redirect_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
DL = os.path.join(REPO, "test-dlocal")
sys.path.insert(0, DL)

import run_dlocal_test  # noqa: E402


def _read(path, key_col, val_col, extra=None):
    out = {}
    with open(path, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            rec = {"value": row[val_col]}
            if extra:
                for e in extra:
                    rec[e] = row.get(e, "")
            out[row[key_col]] = rec
    return out


def _num(x):
    try:
        return float(str(x).replace(",", ""))
    except (TypeError, ValueError):
        return None


def main():
    buf = io.StringIO()
    with redirect_stdout(buf):
        try:
            run_dlocal_test.main()
        except SystemExit:
            pass

    model = _read(os.path.join(DL, "model_output.csv"), "key", "value")
    expected = _read(os.path.join(DL, "EXPECTED_from_dLocal_SEC_filings.csv"),
                     "key", "expected_value", extra=["unit"])

    rows, n_pass = [], 0
    for key, exp in expected.items():
        unit = exp.get("unit", "")
        mv = _num(model.get(key, {}).get("value"))
        ev = _num(exp["value"])
        delta = None if mv is None or ev is None else round(mv - ev, 4)
        tol = 1.0 if unit == "USD_000" else (0.1 if unit == "pct" else 0.0)
        ok = delta is not None and abs(delta) <= tol
        n_pass += ok
        rows.append({"key": key, "model": mv, "expected": ev, "delta": delta,
                     "unit": unit, "status": "PASS" if ok else "FAIL"})

    def g(k):
        return _num(model.get(k, {}).get("value"))

    headline = {
        "net_income_fy2025": g("net_income_fy2025"),
        "adjusted_ebitda_fy2025": g("adjusted_ebitda_fy2025"),
        "revenue_growth_pct": g("revenue_growth_yoy_pct") or g("revenue_growth_fy2025_pct"),
        "total_assets_fy2025": g("total_assets_fy2025"),
    }
    result = {"passed": n_pass, "total": len(rows), "rows": rows, "headline": headline}
    sys.__stdout__.write(json.dumps(result, default=str))


if __name__ == "__main__":
    main()
