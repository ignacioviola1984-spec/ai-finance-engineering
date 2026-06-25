"""harvest_sources.py - Station 1 (ERP / Data sources) snapshot.

Maps the committed QuickBooks sandbox fixture into the canonical layer, runs the
10 deterministic validations on the clean data and on three tampered copies
(so the demo can show a named control firing), writes one immutable snapshot to
a temp dir to capture its sha256 manifest, and records the synthetic-source
scale for the "swap" contrast. No network, no API keys.

Emits one JSON object to stdout.
"""

import copy
import csv
import io
import json
import os
import sys
import tempfile
from contextlib import redirect_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
SOURCES = os.path.join(REPO, "sources")
for sub in ("canonical", "quickbooks", "snapshots"):
    sys.path.insert(0, os.path.join(SOURCES, sub))

import mapper            # noqa: E402
import validate as V     # noqa: E402
import writer as snap    # noqa: E402

PERIOD = "2026-05"
ENTITY_ID = "US"
ENTITY_NAME = "QuickBooks Sandbox Co."
REALM = "sandbox"
TS = "2026-05-31T12:00:00+00:00"

FIXTURE = os.path.join(SOURCES, "fixtures", "quickbooks_sandbox", "sandbox_extract_2026_05.json")
SYN_DATA = os.path.join(REPO, "finance-mcp", "data")


def _checks(tables):
    r = V.validate_canonical(tables, PERIOD)
    return {
        "pass": r["pass"],
        "n_ok": sum(1 for c in r["checks"] if c["ok"]),
        "n_total": len(r["checks"]),
        "checks": [{"name": c["name"], "ok": c["ok"], "detail": c["detail"]} for c in r["checks"]],
        "broken": [c["name"] for c in r["checks"] if not c["ok"]],
        "record_counts": r["record_counts"],
    }


def _rowcount(path):
    if not os.path.exists(path):
        return 0
    with open(path, encoding="utf-8", newline="") as f:
        return max(0, sum(1 for _ in csv.reader(f)) - 1)


def main():
    buf = io.StringIO()
    with redirect_stdout(buf):
        raw = json.load(open(FIXTURE, encoding="utf-8"))
        clean = mapper.build_canonical(raw, ENTITY_ID, ENTITY_NAME, PERIOD)

        # P&L and balance-sheet headline straight off the canonical rows.
        pnl = {"4000": 0.0, "5000": 0.0, "6000": 0.0, "6100": 0.0, "6200": 0.0}
        for r in clean["pnl_activity"]:
            pnl[r["account_code"]] = pnl.get(r["account_code"], 0.0) + float(r["amount_local"])
        pnl_view = {
            "revenue": pnl["4000"], "cogs": pnl["5000"], "sm": pnl["6000"],
            "rd": pnl["6100"], "ga": pnl["6200"],
            "operating_income": pnl["4000"] - pnl["5000"] - pnl["6000"] - pnl["6100"] - pnl["6200"],
        }
        bs = {}
        for r in clean["balance_sheet"]:
            bs[r["account_code"]] = bs.get(r["account_code"], 0.0) + float(r["amount_local"])
        assets = bs.get("1000", 0) + bs.get("1100", 0) + bs.get("1500", 0)
        liab = bs.get("2000", 0) + bs.get("2500", 0)
        equity = bs.get("3000", 0) + bs.get("3900", 0)
        bs_view = {
            "cash": bs.get("1000", 0), "ar": bs.get("1100", 0), "fixed": bs.get("1500", 0),
            "ap": bs.get("2000", 0), "deferred": bs.get("2500", 0),
            "paid_in": bs.get("3000", 0), "retained": bs.get("3900", 0),
            "total_assets": assets, "total_liabilities": liab, "total_equity": equity,
            "check": round(assets - liab - equity, 2),
        }
        tb_debits = sum(float(r.get("debit", 0)) for r in clean["trial_balance"])
        tb_credits = sum(float(r.get("credit", 0)) for r in clean["trial_balance"])

        clean_checks = _checks(clean)

        # --- three tampers (mirror sources/tests/test_validate.py) ---
        t_cash = copy.deepcopy(clean)
        for r in t_cash["balance_sheet"]:
            if r["account_code"] == "1000":
                r["amount_local"] = 999999.0
        tamper_cash = _checks(t_cash)

        t_eur = copy.deepcopy(clean)
        t_eur["ar_invoices"][0]["currency"] = "EUR"
        tamper_eur = _checks(t_eur)

        t_fut = copy.deepcopy(clean)
        t_fut["ar_invoices"].append({
            "invoice_id": "INV-FUTURE", "entity_id": ENTITY_ID, "customer": "Acme",
            "currency": "USD", "amount_local": 5000.0,
            "issue_date": "2026-09-01", "due_date": "2026-09-30", "status": "open"})
        tamper_future = _checks(t_fut)

        # --- immutable snapshot -> manifest with sha256 ---
        tmp = tempfile.mkdtemp(prefix="v2_snap_")
        _, manifest = snap.write_snapshot(tmp, REALM, PERIOD, raw, clean,
                                          V.validate_canonical(clean, PERIOD), TS)
        raw_hashes = manifest["hashes"]["raw"]
        canon_hashes = manifest["hashes"]["canonical"]
        manifest_view = {
            "realm_id": manifest["realm_id"],
            "period": manifest["period"],
            "extract_timestamp": manifest["extract_timestamp"],
            "n_raw_files": len(raw_hashes),
            "n_canonical_files": len(canon_hashes),
            "record_counts": manifest["record_counts"],
            "validation_pass": manifest["validation_result"]["pass"],
            "sample_hashes": {
                "raw/profit_and_loss.json": raw_hashes.get("profit_and_loss.json", ""),
                "canonical/pnl_activity.csv": canon_hashes.get("pnl_activity.csv", ""),
                "canonical/balance_sheet.csv": canon_hashes.get("balance_sheet.csv", ""),
            },
        }

        # --- canonical preview tables for display ---
        coa = {r["account_code"]: r.get("account_name", r.get("name", "")) for r in clean["chart_of_accounts"]}
        bs_preview = [{"code": r["account_code"], "account": coa.get(r["account_code"], ""),
                       "amount_usd": float(r["amount_local"])} for r in clean["balance_sheet"]]
        ar_preview = [{"invoice_id": r.get("invoice_id", ""), "customer": r.get("customer", ""),
                       "amount_usd": float(r.get("amount_local", 0)), "status": r.get("status", ""),
                       "due_date": r.get("due_date", "")} for r in clean["ar_invoices"]]
        coa_preview = [{"code": r["account_code"], "account": r.get("account_name", r.get("name", "")),
                        "type": r.get("account_type", r.get("type", ""))} for r in clean["chart_of_accounts"]]

        synthetic_scale = {
            "entities": _rowcount(os.path.join(SYN_DATA, "entities.csv")),
            "fx_rate_rows": _rowcount(os.path.join(SYN_DATA, "fx_rates.csv")),
            "pnl_rows": _rowcount(os.path.join(SYN_DATA, "pnl_activity.csv")),
            "ar_invoices": _rowcount(os.path.join(SYN_DATA, "ar_invoices.csv")),
            "currencies": 6,
        }

    result = {
        "period": PERIOD, "entity": ENTITY_NAME, "realm": REALM,
        "pnl": pnl_view, "balance_sheet": bs_view,
        "trial_balance": {"debits": round(tb_debits, 2), "credits": round(tb_credits, 2)},
        "clean": clean_checks,
        "tampers": [
            {"key": "cash", "label": "Set Balance Sheet cash to 999,999",
             "fires": "balance_sheet_foots", "owner": "Internal Controls", **tamper_cash},
            {"key": "eur", "label": "Post an invoice in EUR (an unknown currency)",
             "fires": "currency_present_and_known", "owner": "Controller", **tamper_eur},
            {"key": "future", "label": "Post an invoice dated 2026-09 (a future period)",
             "fires": "no_future_dated_postings", "owner": "Controller", **tamper_future},
        ],
        "manifest": manifest_view,
        "preview": {"balance_sheet": bs_preview, "ar_invoices": ar_preview, "chart_of_accounts": coa_preview},
        "synthetic_scale": synthetic_scale,
    }
    sys.__stdout__.write(json.dumps(result, default=str))


if __name__ == "__main__":
    main()
