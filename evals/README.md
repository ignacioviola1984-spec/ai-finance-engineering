# Evals, Guardrails & Reliability

How I make a finance AI agent trustworthy. In finance the number has to be
right, so "it works most of the time" is not a standard. This is the layer
that turns that requirement into something measured, not hoped for.

## What this runs

`eval_runner.py` runs three suites and prints a scorecard. It exits with a
non-zero code if anything fails, so it doubles as a regression test: run it
before and after a change to see whether you broke something.

- **Numbers** — regression on the consolidated figures (operating income,
  cash, AR overdue %). These are computed in code, so this guards against a
  change silently moving a number.
- **Extraction** — accuracy of contract-term extraction against a known
  ground truth (`eval_set.py`). Validated by "contains", since the model may
  phrase a field differently.
- **Grounding guardrail** — asks questions with no answer in the documents
  and checks that the agent refuses instead of inventing. This is the control
  that stops a fabricated number from passing as real.

## Run it

```bash
pip install -r ../document-intelligence/requirements.txt
python eval_runner.py
```

(Numbers needs no API key; Extraction and Grounding use `ANTHROPIC_API_KEY`
from the repo-root `.env`.)

## How I make a finance agent reliable

1. **Compute, don't guess.** Numbers come from code; the model routes,
   reasons, and writes, but never produces a figure on its own.
2. **Ground every answer.** The model answers only from retrieved or provided
   context and cites the source. If the context is insufficient, it says so.
3. **Measure with an eval set.** Known-correct cases turn "seems fine" into a
   number. The cross-lingual retrieval miss in the RAG project (documented in
   `document-intelligence/`) is exactly the kind of failure you only catch
   this way, not by spot-checking.
4. **Guardrails and a second look on risk.** Deterministic checks between
   stages, severity-based escalation, and a human-in-the-loop gate on
   high-risk items (built in `orchestration/`).
5. **Regression testing.** This harness exits non-zero on failure, so a
   prompt or code change that breaks a known-good behavior is caught before
   it ships.

## Stack
Python, evaluation harness, regression testing, grounding guardrails,
deterministic checks. Reuses the agents in `orchestration/` and
`document-intelligence/`.
