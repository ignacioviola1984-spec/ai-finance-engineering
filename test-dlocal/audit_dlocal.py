"""
audit_dlocal.py - Independent audit. Reads ONLY model_output.csv (what the model
computed) and EXPECTED_from_dLocal_SEC_filings.csv (dLocal's reported figures
from the SEC 6-Ks). Does not run the model. Prints a PASS/FAIL table.
"""
import os, csv
HERE = os.path.dirname(os.path.abspath(__file__))

def read(name):
    with open(os.path.join(HERE, name), newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))

model = {r["key"]: float(r["value"]) for r in read("model_output.csv")}
expected = read("EXPECTED_from_dLocal_SEC_filings.csv")

rows = []; npass = nfail = 0
for r in expected:
    k = r["key"]; ev = float(r["expected_value"]); unit = r["unit"]
    if k not in model:
        rows.append((k, "NA", ev, "NA", "MISSING")); continue
    mv = model[k]; delta = round(mv - ev, 2)
    tol = 1.0 if unit == "USD_000" else 0.1
    res = "PASS" if abs(delta) <= tol else "FAIL"
    rows.append((k, mv, ev, delta, res))
    npass += res == "PASS"; nfail += res == "FAIL"

with open(os.path.join(HERE, "audit_result.csv"), "w", newline="") as f:
    w = csv.writer(f); w.writerow(["key", "model", "expected", "delta", "result"])
    for x in rows: w.writerow(x)

print("INDEPENDENT AUDIT - model computed vs dLocal reported (SEC filings):")
print(f"  {'key':40} {'model':>14} {'expected':>14} {'delta':>9}  result")
for k, mv, ev, d, res in rows:
    mvs = f"{mv:,.1f}" if isinstance(mv, float) else str(mv)
    evs = f"{ev:,.1f}" if isinstance(ev, float) else str(ev)
    print(f"  {k:40} {mvs:>14} {evs:>14} {str(d):>9}  {res}")
print(f"\nRESULT: PASS {npass} / FAIL {nfail} / total {len(rows)}")
print("Wrote test-dlocal/audit_result.csv")
