# Step 1 — RUN THE MODEL BLIND
Paste this into Claude Code, run from the repo root.

Run the CFO multi-agent model on real dLocal inputs. The model must run BLIND: it does not see the reported answers in this step.

Inputs (in test-dlocal/): entities.csv, fx_rates.csv, pnl_activity.csv, balance_sheet.csv, budget.csv, kpis_reference.csv
Do NOT open EXPECTED_from_dLocal_SEC_filings.csv in this step. That file is the audit answer key and the model must not see it.

Rules:
- Amounts are in thousands of USD. In pnl_activity.csv expenses are already negative, so subtotals are plain sums.
- The income-statement subtotals (gross profit, operating profit, profit before tax, net income) are NOT in the inputs on purpose. finance_core must compute them in code. Do not hardcode them.
- Single consolidated entity, USD (fx = 1). Period 2025-12, prior period 2024-12.

Do:
1. Write an adapter test-dlocal/load_dlocal.py that loads these CSVs into the structures finance_core / the agents already expect. Do not modify my synthetic data anywhere else.
2. Run the close end-to-end (cfo_orchestrator) with CFO_AUTO_REVIEW=1, and produce the board pack.
3. Write test-dlocal/model_output.csv with every figure the model COMPUTED, one per row, columns: key,value. Use exactly these keys: gross_profit_fy2025, operating_profit_fy2025, profit_before_tax_fy2025, net_income_fy2025, net_income_fy2024, adjusted_ebitda_fy2025, total_assets_fy2025, total_assets_fy2024, total_liabilities_fy2025, total_equity_fy2025, closing_cash_fy2025, gross_margin_fy2025_pct, net_margin_fy2025_pct, adjusted_ebitda_margin_fy2025_pct, revenue_growth_yoy_pct, gross_profit_growth_yoy_pct, net_income_growth_yoy_pct.
4. Do NOT compare to any reported number. Just compute, save model_output.csv, and stop.
