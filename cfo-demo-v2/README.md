# AI Finance Operating Model - Live Demo (v2)

An HR-friendly, click-through demo of the whole `ai-finance-engineering` operating
model. It follows one synthetic company's data through the full finance lifecycle,
in five stations:

1. **ERP - data in** · pull from QuickBooks Online (read-only) into a vendor-neutral
   canonical layer, run 10 deterministic validations, freeze an sha256-stamped
   immutable snapshot. Includes a "tamper a number, watch a named control fire" toggle
   and a Synthetic ⇄ QuickBooks source swap.
2. **O2C control tower** · the Order-to-Cash sub-orchestration. Toggle a broken month
   (blocked, adverse audit, DSO 169) against a clean one (passes, unqualified, DSO 55).
   DSO, unapplied cash, aging, a bookings→cash bridge, 25 controls, 35 metrics, 10 agents.
3. **Month-end close** · eight specialist agents produce the three articulating financial
   statements and a board pack, with two-tier maker-checker sign-off - you act as CFO for
   the final gate.
4. **Evals - does it hold?** · four offline scoreboards: 22/22 deterministic numbers,
   12/12 self-improvement safety proofs, 48/48 O2C tests (incl. 10/10 planted blind
   validation), and 17/17 figures reproduced against dLocal's real audited SEC filings.
5. **Self-improvement** · the bounded, eval-gated, human-approved, reversible loop that
   retunes four whitelisted parameters and nothing else.

## Design

- **Every number is computed by code.** The AI agents read the numbers and write the
  commentary; they never invent a figure. The app only *renders* pre-computed snapshots.
- **Instant, free, no API key.** Like v1, the deployed app reads saved snapshots, so it
  needs no secrets and makes no network calls.
- **Honest by default.** Where a human approval is simulated in the public replay, or a
  data/claim boundary applies, the UI says so plainly.

## Reproduce the numbers

Every snapshot in `snapshots/` is produced from the live engine, fully offline:

```bash
python cfo-demo-v2/build_snapshots.py
```

This runs each station's harvester (`harvest/`) in an isolated subprocess and rewrites
`snapshots/*.json`. No API key, no network. The `harvest/` scripts are the audit trail
from "what the engine computes" to "what the demo shows".

## Run locally

```bash
pip install -r cfo-demo-v2/requirements.txt
python -m streamlit run cfo-demo-v2/app.py
```

## Deploy (Streamlit Community Cloud)

- Repo: `ignacioviola1984-spec/ai-finance-engineering`, branch `main`
- Main file path: `cfo-demo-v2/app.py`
- No secrets required.

(v1 - the CFO-only demo - remains at `cfo-demo/app.py`.)

---

Built by **Ignacio Viola** · 17 years in senior finance, now building the AI systems.
Synthetic data throughout, except the dLocal station which uses real public SEC filings.
