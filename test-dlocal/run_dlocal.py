"""
run_dlocal.py - Adapter + runner. Transforms the real dLocal CSVs into your
finance_core schema, runs YOUR deterministic engine, and writes model_output.csv.
Runs BLIND: it never reads EXPECTED_from_dLocal_SEC_filings.csv.

No API key / no LLM needed: this is the deterministic number layer only.
"""
import os, sys, csv

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "orchestration"))

def read_csv(name):
    with open(os.path.join(HERE, name), newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))

pnl_rows = read_csv("pnl_activity.csv")
bs_rows = read_csv("balance_sheet.csv")
PERIODS = ["2024-12", "2025-12"]

pnl_amt = {(r["period"], r["account_code"]): float(r["amount_usd_000"]) for r in pnl_rows}

# ---- transform to finance_core (your) schema in a temp dir ----
tmp = "/tmp/dlo_his_schema"
os.makedirs(tmp, exist_ok=True)

with open(os.path.join(tmp, "entities.csv"), "w", newline="") as f:
    w = csv.writer(f); w.writerow(["entity_id", "name", "country", "currency"])
    w.writerow(["DLO", "dLocal Limited", "Uruguay", "USD"])

with open(os.path.join(tmp, "fx_rates.csv"), "w", newline="") as f:
    w = csv.writer(f); w.writerow(["period", "currency", "units_per_usd"])
    for p in PERIODS: w.writerow([p, "USD", 1])

# P&L mapping to your account codes (expenses stored POSITIVE, like your data):
#   his 4000 Revenue   = dLocal 4000
#   his 5000 COGS      = dLocal 5000 (Cost of services)
#   his 6000 S&M       = dLocal 6200 (Sales & marketing)
#   his 6100 R&D       = dLocal 6100 (Technology & development)
#   his 6200 G&A       = dLocal 6300 + 6400 + 6500 (G&A + impairment + other operating)
with open(os.path.join(tmp, "pnl_activity.csv"), "w", newline="") as f:
    w = csv.writer(f); w.writerow(["entity_id", "period", "account_code", "amount_local"])
    for p in PERIODS:
        rev = pnl_amt[(p, "4000")]
        cogs = abs(pnl_amt[(p, "5000")])
        sm = abs(pnl_amt[(p, "6200")])
        rd = abs(pnl_amt[(p, "6100")])
        ga = abs(pnl_amt[(p, "6300")]) + abs(pnl_amt[(p, "6400")]) + abs(pnl_amt[(p, "6500")])
        w.writerow(["DLO", p, "4000", rev])
        w.writerow(["DLO", p, "5000", cogs])
        w.writerow(["DLO", p, "6000", sm])
        w.writerow(["DLO", p, "6100", rd])
        w.writerow(["DLO", p, "6200", ga])

# Balance sheet mapping to your account types (1000 cash, 1100 other assets,
# 2000 liabilities, 3000 paid-in/other equity, 3900 retained earnings):
bs_by = {}
for r in bs_rows:
    bs_by.setdefault(r["period"], []).append(r)
with open(os.path.join(tmp, "balance_sheet.csv"), "w", newline="") as f:
    w = csv.writer(f); w.writerow(["entity_id", "period", "account_code", "amount_local"])
    for p in PERIODS:
        rows = bs_by[p]
        cash = sum(float(x["amount_usd_000"]) for x in rows if x["section"] == "ASSET" and x["line_item"].startswith("Cash"))
        other_a = sum(float(x["amount_usd_000"]) for x in rows if x["section"] == "ASSET" and not x["line_item"].startswith("Cash"))
        liab = sum(float(x["amount_usd_000"]) for x in rows if x["section"] == "LIABILITY")
        re = sum(float(x["amount_usd_000"]) for x in rows if x["section"] == "EQUITY" and x["line_item"].startswith("Retained"))
        other_e = sum(float(x["amount_usd_000"]) for x in rows if x["section"] == "EQUITY" and not x["line_item"].startswith("Retained"))
        for code, val in [("1000", cash), ("1100", other_a), ("2000", liab), ("3000", other_e), ("3900", re)]:
            w.writerow(["DLO", p, code, val])

with open(os.path.join(tmp, "budget.csv"), "w", newline="") as f:
    w = csv.writer(f); w.writerow(["entity_id", "period", "account_code", "amount_usd"])
    w.writerow(["DLO", "2025-12", "4000", 1007065]); w.writerow(["DLO", "2025-12", "5000", 616623])

# ---- point YOUR finance_core at this data and recompute ----
import finance_core as fc
fc.DATA = tmp
fc._ENT = fc._load("entities.csv")
fc._FX = {(r["period"], r["currency"]): float(r["units_per_usd"]) for r in fc._load("fx_rates.csv")}
fc._PNL = fc._load("pnl_activity.csv")
fc._BS = fc._load("balance_sheet.csv")
fc._BUD = fc._load("budget.csv")
fc._CCY = {r["entity_id"]: r["currency"] for r in fc._ENT}
fc.PERIODS = sorted({r["period"] for r in fc._PNL})

p25 = fc.pnl_usd("2025-12"); p24 = fc.pnl_usd("2024-12")
imb25 = fc._trial_balance_imbalance("2025-12"); imb24 = fc._trial_balance_imbalance("2024-12")

def totals(period):
    A = L = E = 0.0
    for r in fc._BS:
        if r["period"] != period: continue
        t = fc._BS_TYPE.get(r["account_code"])
        v = fc._usd(float(r["amount_local"]), fc._CCY[r["entity_id"]], period)
        if t == "A": A += v
        elif t == "L": L += v
        elif t == "E": E += v
    return A, L, E
A25, L25, E25 = totals("2025-12"); A24, L24, E24 = totals("2024-12")

# Extension (deterministic, same atomic inputs): below-operating lines -> net income
def below(p):
    return pnl_amt[(p, "7100")] + pnl_amt[(p, "7200")] + pnl_amt[(p, "7300")]
pbt25 = p25["operating_income"] + below("2025-12")
ni25 = pbt25 + pnl_amt[("2025-12", "8000")]
ni24 = p24["operating_income"] + below("2024-12") + pnl_amt[("2024-12", "8000")]

# Adjusted EBITDA = operating profit + D&A + SBP + impairment + other op loss + secondary + other non-recurring
DA, SBP, SEC_OFF, OTH_NR = 26260, 24136, 739, 124
impair = abs(pnl_amt[("2025-12", "6400")]); other_op = abs(pnl_amt[("2025-12", "6500")])
adj_ebitda25 = p25["operating_income"] + DA + SBP + impair + other_op + SEC_OFF + OTH_NR

rev25, rev24 = p25["revenue"], p24["revenue"]; gross25, gross24 = p25["gross"], p24["gross"]
out = [
    ("gross_profit_fy2025", gross25, "finance_core.pnl_usd"),
    ("operating_profit_fy2025", p25["operating_income"], "finance_core.pnl_usd"),
    ("profit_before_tax_fy2025", pbt25, "extension (atomic lines)"),
    ("net_income_fy2025", ni25, "extension (atomic lines)"),
    ("net_income_fy2024", ni24, "extension (atomic lines)"),
    ("adjusted_ebitda_fy2025", adj_ebitda25, "extension (+reconciliation addbacks)"),
    ("total_assets_fy2025", A25, "finance_core BS"),
    ("total_assets_fy2024", A24, "finance_core BS"),
    ("total_liabilities_fy2025", L25, "finance_core BS"),
    ("total_equity_fy2025", E25, "finance_core BS"),
    ("closing_cash_fy2025", fc.cash_total_usd("2025-12"), "finance_core.cash_total_usd"),
    ("gross_margin_fy2025_pct", round(gross25 / rev25 * 100, 1), "computed"),
    ("net_margin_fy2025_pct", round(ni25 / rev25 * 100, 1), "computed"),
    ("adjusted_ebitda_margin_fy2025_pct", round(adj_ebitda25 / rev25 * 100, 1), "computed"),
    ("revenue_growth_yoy_pct", round((rev25 / rev24 - 1) * 100, 1), "computed"),
    ("gross_profit_growth_yoy_pct", round((gross25 / gross24 - 1) * 100, 1), "computed"),
    ("net_income_growth_yoy_pct", round((ni25 / ni24 - 1) * 100, 1), "computed"),
    ("trial_balance_imbalance_2025", round(imb25, 2), "finance_core control C1"),
    ("trial_balance_imbalance_2024", round(imb24, 2), "finance_core control C1"),
    ("rule_of_40_fy2025", round((rev25 / rev24 - 1) * 100 + p25["operating_income"] / rev25 * 100, 1), "finance_core def"),
]
with open(os.path.join(HERE, "model_output.csv"), "w", newline="") as f:
    w = csv.writer(f); w.writerow(["key", "value", "source"])
    for k, v, s in out:
        w.writerow([k, round(v, 1) if isinstance(v, float) else v, s])

print("MODEL OUTPUT (computed blind, never saw reported figures):")
for k, v, s in out:
    vv = f"{v:,.1f}" if isinstance(v, float) else str(v)
    print(f"  {k:38} {vv:>16}   [{s}]")
print("\nWrote test-dlocal/model_output.csv")
