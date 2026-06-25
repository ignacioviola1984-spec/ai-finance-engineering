"""build_snapshots.py - regenerate every committed demo snapshot from live code.

Runs each station's harvester in its own isolated subprocess (so the engine's
module-level state and conflicting sys.path setups never cross-contaminate),
then writes the JSON the Streamlit app reads. Fully offline, no API keys, no
network. Re-run any time to refresh:  python cfo-demo-v2/build_snapshots.py

Every number the demo shows is produced here, by the same code the repo ships -
the app only renders it.
"""

import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
HARVEST = os.path.join(HERE, "harvest")
OUT = os.path.join(HERE, "snapshots")
os.makedirs(OUT, exist_ok=True)


def run_harvester(name):
    path = os.path.join(HARVEST, name)
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    print(f"  -> {name} ...", flush=True)
    proc = subprocess.run([sys.executable, path], cwd=REPO, env=env,
                          capture_output=True, text=True, timeout=900)
    if proc.returncode != 0 or not proc.stdout.strip():
        sys.stderr.write(proc.stderr[-3000:])
        raise SystemExit(f"harvester {name} failed (rc={proc.returncode})")
    return json.loads(proc.stdout)


def write(fname, data):
    with open(os.path.join(OUT, fname), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)


def main():
    print("Building demo snapshots (all offline, every number from live code)...")

    print("[1/5] ERP / data sources")
    sources = run_harvester("harvest_sources.py")
    write("sources.json", sources)

    print("[2/5] Order-to-Cash control tower")
    o2c = run_harvester("harvest_o2c.py")
    write("o2c.json", o2c)

    print("[3/5] Month-end close (reuse the v1 saved run)")
    src_close = os.path.join(REPO, "cfo-demo", "demo_snapshot.json")
    shutil.copyfile(src_close, os.path.join(OUT, "close.json"))

    print("[4/5] Evals (4 scoreboards)")
    evals = {
        "numbers": run_harvester("harvest_eval_numbers.py"),
        "safety": run_harvester("harvest_eval_safety.py"),
        "dlocal": run_harvester("harvest_eval_dlocal.py"),
    }
    o2c_eval = run_harvester("harvest_eval_o2c.py")
    evals["o2c_suite"] = o2c_eval["suite"]
    evals["o2c_blind"] = o2c_eval["blind"]
    write("evals.json", evals)

    print("[5/5] Bounded self-improvement")
    si = run_harvester("harvest_selfimprove.py")
    write("selfimprove.json", si)

    # ---- scoreboard ----
    print("\n" + "=" * 60)
    print("SNAPSHOTS BUILT - headline verification")
    print("=" * 60)
    print(f"  ERP validations     : {sources['clean']['n_ok']}/{sources['clean']['n_total']} pass, "
          f"op income {sources['pnl']['operating_income']:,.0f}")
    print(f"  O2C broken month    : {o2c['2026-05']['final_status']} "
          f"({o2c['2026-05']['controls_summary']['hard_failures']} hard fails, DSO {o2c['2026-05']['summary']['dso']})")
    print(f"  O2C clean month     : {o2c['2026-06']['final_status']} "
          f"({o2c['2026-06']['controls_summary']['hard_failures']} hard fails, DSO {o2c['2026-06']['summary']['dso']})")
    print(f"  Numbers eval        : {evals['numbers']['passed']}/{evals['numbers']['total']}")
    print(f"  Self-improve safety : {evals['safety']['passed']}/{evals['safety']['total']}")
    print(f"  O2C suite           : {evals['o2c_suite']['passed']}/{evals['o2c_suite']['total']}")
    print(f"  O2C blind validation: {evals['o2c_blind']['caught']}/{evals['o2c_blind']['planted']} planted caught")
    print(f"  dLocal real-data    : {evals['dlocal']['passed']}/{evals['dlocal']['total']}")
    print(f"  Self-improvement    : accept ok={si['accept']['ok']}, "
          f"audit events={len(si['audit_trail'])}")
    print(f"\n  Wrote: {', '.join(sorted(os.listdir(OUT)))}")


if __name__ == "__main__":
    main()
