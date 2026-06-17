# Step 2 — INDEPENDENT AUDIT
Open a NEW Claude Code chat (fresh, no memory of Step 1) and paste this. This keeps the auditor separate from the preparer.

You are an independent auditor. Do NOT run, change, or re-run the model. Only check its output against external truth.

Read:
- test-dlocal/model_output.csv  (what the model computed in Step 1)
- test-dlocal/EXPECTED_from_dLocal_SEC_filings.csv  (dLocal's audited reported figures, taken from the SEC 6-Ks)

Do:
1. Join on key. For each row compute delta = model_value minus expected_value. Mark PASS if absolute delta is at most 1 for USD_000 rows, or at most 0.1 for pct rows; otherwise FAIL.
2. Print a table: key | model | expected | delta | PASS or FAIL.
3. As a second, independent line of evidence, open the two SEC filings (links in README.md) and confirm by eye that net_income_fy2025 = 196,902 and total_assets_fy2025 = 1,540,964 appear in the primary source.
4. The retained-earnings roll-forward (open RE 490,024 + net income to owners 196,801 - dividends paid 149,982 = 536,843 vs reported close 534,818) is a KNOWN reconciling item of about 2,025, from dLocal's 2025 equity restructuring (share-premium reduction) and equity-settled share-based payments. Report it as a reconciling item, not a fail.
5. Output one line: how many PASS, how many FAIL, and list any FAIL with its key and delta.

Independence note: the model ran blind in Step 1 and never saw EXPECTED. The ground truth is dLocal's audited filings, not anything the model produced.
