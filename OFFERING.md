# Working with me — the CFO AI Office Accelerator

> **This is not a chatbot for finance.** It is a documented, working implementation
> of an agentic CFO office: AI agents draft, code-based controls validate, finance
> leaders approve, and the CFO owns the final consolidated sign-off.

I help finance teams design and implement **agentic finance workflows** with
deterministic controls, human-in-the-loop gates, audit trails and CFO-level
accountability — built by a finance operator with 17 years of experience, not a
generic AI shop.

The differentiator is the combination, which is rare: **finance domain expertise +
a real operating model + governance + working code + a demo a non-technical
executive can actually follow.** See it run end to end in [`CASE-STUDY.md`](CASE-STUDY.md).

And the accuracy is not just asserted, it is checked against reality: the model's
deterministic numbers tie **17 of 17** statement-level figures to a real public
company's reported financials (dLocal, NASDAQ: DLO), reproducible by anyone in two
commands with no LLM and no API keys. Full evidence and scope are in
[`test-dlocal/AUDIT_EVIDENCE.md`](test-dlocal/AUDIT_EVIDENCE.md).

## Who this is for

- **CFOs and finance leaders** who want AI in the close, FP&A, treasury or controls
  *without* losing control, auditability or accountability.
- **PE-backed and mid-market companies** under pressure to do more with the same
  finance headcount.
- **Boutique consultancies** that need a finance-native agentic reference architecture.

## What I bring that a generic AI consultant doesn't

- I know **which numbers matter and which controls are load-bearing** — because I've
  owned the close, not just coded around it.
- A design rule that makes it trustworthy: **every figure is computed in code
  (deterministic, auditable); the AI reasons and writes, but never invents a
  number.**
- **Two-tier governance (maker-checker):** each function is signed off by its own
  domain expert; the CFO gives a single final consolidated sign-off. Realistic for
  production, not a demo fantasy of "one human approves everything."

## Why a CFO or auditor can trust it

Three independent angles of assurance, not one marketing claim:

- **Real public-company reconciliation (accuracy):** the model's deterministic
  numbers tie **17 of 17** statement-level figures to dLocal's (NASDAQ: DLO)
  reported FY2024/FY2025 financials (IFRS, USD). A read-only auditor diffs the
  model output against an SEC-derived answer key and returns **17 PASS, 0 FAIL**.
  The figures are P&L subtotals, Adjusted EBITDA, balance-sheet section totals,
  closing cash, margins, and year-over-year growth. The auditor fails closed: a
  wrong value, a missing, extra, or duplicate key, or a non-numeric entry all fail.
- **Adversarial synthetic traps (detection):** the model was run cold against four
  synthetic month-end datasets with roughly 30 seeded errors each. Detection is
  strong, with the large majority of seeded traps caught via planted-ID and
  flag-column scans. The recurring gap is quantifying and classifying the
  adjustments (amounts, P&L-versus-balance-sheet, where credit losses sit), which
  still needed correction against ground truth. That is exactly why a human checker
  stays in the loop.
- **Independent second-model review (dual-model):** Codex independently reviewed the
  repo, the test design, the local eval evidence, and the claim boundaries, external
  to the model-output generation path. The local eval harness passes 33/33 locally
  (Numbers 22/22, Extraction 9/9, Grounding 2/2).

**Scope, stated plainly.** This validates the **deterministic statement-level math**
against a real public company's reported numbers. It is illustrative and uses
**public SEC data only**; dLocal is not affiliated with this project and did not
endorse, sponsor, or review it. No public company discloses transaction-level
subledgers, so the transaction-level AR/AP/tax agents and the multi-entity,
multi-currency consolidation are **not** validated on real data, and the dLocal
pass does not prove the entire operating model on real transaction-level data. The
Codex review is external to the preparer, not a formal external or statutory audit,
a certification, an assurance opinion, or a substitute for a human auditor. Full
evidence and boundaries: [`test-dlocal/AUDIT_EVIDENCE.md`](test-dlocal/AUDIT_EVIDENCE.md).

## How an engagement works

A staged ladder — start small, expand only when value is proven. Scope and pricing
are set per engagement.

| Stage | What you get | Typical duration |
|---|---|---|
| **1 · Assessment** | Map your close, cash, FP&A, reporting and controls; identify the highest-ROI workflow to automate first; AI-readiness and governance review. | ~1–2 weeks |
| **2 · Demo workshop** | Walk your team through the working operating model and demo; translate it to *your* processes; agree the pilot scope. | ~1 day |
| **3 · Pilot** | Adapt **one** real workflow (e.g. cash forecast, close exception review, or the board pack) on your data, with controls, logs and sign-offs. | ~4–6 weeks |
| **4 · Implementation** | Connect real data, harden the controls, wire the audit trail, HITL approvals and the final output into your stack. | ~8–12 weeks |
| **5 · Retainer** | Monitoring, continuous improvement, new agents, governance upkeep. | Ongoing |

## What I always keep in the design

- **Deterministic controls in code:** hard gates that don't depend on the model's opinion.
- **Accuracy checked against reality, not asserted:** the deterministic math is reconciled to a real public company's reported financials (17 of 17), and run cold against adversarial synthetic traps.
- **A domain expert accountable for each function:** the AI augments the expert; it doesn't replace the team.
- **A full audit trail:** every step, every sign-off, timestamped.
- **Honest limitations stated up front:** explicit scope and boundaries, public data only, no inflated claims.

## Let's talk

If you want AI in your finance function that your auditors, your board and you can
trust, get in touch.

- **GitHub:** <https://github.com/ignacioviola1984-spec/ai-finance-engineering>
- **Author:** Ignacio Viola — 17 years in senior finance, now building the systems.

*The published code is source-available for evaluation under a noncommercial
license (see [`LICENSE`](LICENSE)). Commercial use and production implementations
are delivered under a separate agreement.*
