# LinkedIn article (DRAFT, for your review — not published)

Pick one title:
- I ran my AI finance model on a real company's audited numbers. It tied out to the dollar.
- I tested my AI finance model on real audited financials, not synthetic data. Here is what happened.
- Does the finance AI actually work on real numbers? I tested mine against a public company's filings.

---

Over the past months I built something I had been thinking about for a long time: an AI finance operating model. A set of specialized agents that run a month-end close over a shared state, with every number computed in code and a human signing off at the points that matter.

The honest question anyone in finance asks is the right one. Fine, but does it work on real numbers, or only on the synthetic data you built it with?

So I tested it on a real company.

I pointed the model at dLocal's audited public financials for 2024 and 2025 (NASDAQ: DLO), taken from their SEC filings. I fed it the atomic income-statement and balance-sheet lines and let the model compute everything else: gross profit, operating profit, net income, the balance-sheet identity, margins, growth. Then I checked every figure against what dLocal actually reported.

## How I kept the test honest

A model that grades its own homework proves nothing. So I ran it the way an auditor would.

The model computed blind. It never saw the reported answers while it ran. A separate pass then compared its output to dLocal's reported numbers. And the ground truth was not my opinion or the model's. It was dLocal's audited financial statements, signed by their auditors.

I also did not let a single AI be the only check. Claude Code built and ran the workflow; a second model, Codex, then independently reviewed the design, the evidence, and exactly what the test does and does not prove. Call it a dual-model review, external to the part that generates the numbers. It is AI-assisted, not a formal external audit, and it does not replace a human auditor.

## The result

Seventeen checks. All seventeen tied to dLocal's reported figures, to the dollar.

A few of them:
- Net income: 196.9M USD, computed from the lines, matches reported.
- Operating profit: 219.9M USD, matches.
- Adjusted EBITDA: 278.1M USD, rebuilt from the bottom up, matches.
- The balance sheet balances both years: assets of 1,540.9M USD equal liabilities plus equity.
- The model reconciles to the reported closing cash of 719.9M USD.

## Why it held

One design choice does the heavy lifting: every number is computed in code, deterministically. The model routes, reasons, and writes the narrative, but it never produces a figure on its own. That is the line between a finance system you can trust and a chatbot that sounds confident. No invented numbers, every figure traceable.

## What this is not

I want to be precise, because precision is the point.

This ran on dLocal's public, consolidated filings. The agents that work at invoice level (receivables, payables, tax by jurisdiction) and the multi-entity, multi-currency consolidation still run on representative data, because no public company discloses transaction-level detail. Net income and Adjusted EBITDA came from a deterministic extension over the same reported lines, since the core engine computes to operating profit and validates the balance. And I am not affiliated with dLocal here. Public filings only.

None of that weakens the result. It defines it. Knowing exactly what a test can and cannot prove is the job.

## Why I am sharing it

I am a finance operator, not a career software engineer, and I am deliberate about that. I design the architecture and the controls, I build with AI coding tools, and I read and audit the output, because in finance the number has to be right. The value here is not an autonomous CFO. It is a governed co-pilot for the close: assist, detect, draft, with the human owning judgment and approval.

If you run a finance function and you are trying to separate what AI can actually do today from the noise, I would be glad to compare notes.

The code is on GitHub: [your link]. Public data only, for noncommercial study. Not affiliated with or endorsed by dLocal.

---

Notes for you before posting:
- Add the GitHub link, and consider a screenshot of the 17/17 PASS table (run `py -3 test-dlocal\audit_dlocal_test.py`) as the article image. The visual proof lands.
- If you would rather post in Spanish, tell me and I translate keeping the same tone.
- Optional first comment (drives reach): "Happy to walk through the method or the code. The honest part, what it cannot do yet, is in the post on purpose."
