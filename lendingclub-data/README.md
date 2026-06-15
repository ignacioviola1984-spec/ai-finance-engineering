# LendingClub data

Real-data foundation for the **credit operating model**. The deterministic engine
([`orchestration/credit_core.py`](../orchestration/credit_core.py)) reads the CSVs
here; the credit agents narrate over those numbers (they never invent a figure).

## Files

| File | What it is | Source |
|---|---|---|
| `accepted_sample.csv` | Funded loans (the loan book) — **sample** with the real schema | mirrors `accepted_2007_to_2018Q4.csv` |
| `rejected_sample.csv` | Declined applications — **sample** with the real schema | mirrors `rejected_2007_to_2018Q4.csv` |
| `public_filings.csv` | LendingClub public KPIs to benchmark against (originations, charge-off rate, …) | **placeholders** — replace with actual 10-K / 10-Q figures |
| `generate_sample.py` | Reproducible (seeded) generator for the two sample files | — |

## Pointing at the REAL data

1. Download the LendingClub dataset (Kaggle: `wordsforthewise/lending-club`).
2. Drop the real files in this folder. The engine first looks for the real
   filenames and falls back to the `_sample` files, so either name works:
   - `accepted_2007_to_2018Q4.csv`  (or keep `accepted_sample.csv`)
   - `rejected_2007_to_2018Q4.csv`   (or keep `rejected_sample.csv`)
3. Replace the **placeholder** rows in `public_filings.csv` with the real figures
   from LendingClub's 10-K / 10-Q so the benchmark and variance agents compare
   against true disclosures.

No API key is needed to read the data; the agents need `ANTHROPIC_API_KEY` only to
write the narrative.

> The sample exists so the credit operating model is built and verified **now**.
> Numbers computed on the sample are illustrative; the real test runs on the full
> Kaggle files.
