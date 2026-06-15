"""
cfo_orchestrator.py - El CFO del office.

Instancia un unico estado compartido (CFOContext), corre a los agentes
especializados sobre ese estado, valida la coherencia entre ellos con checks
deterministicos, consolida los escalamientos por severidad, y antes de fijar
el board pack final pide UNA sola aprobacion humana (HITL). Persiste todo a
cfo_state.json.

  1) Controller            -> revisa el cierre y margenes
  2) Treasury              -> caja, burn, runway, forecast 13 semanas
  3) Administration        -> sub-orquesta AR, AP y Tax (capital de trabajo + compliance)
  4) Accounting & Reporting-> sub-orquesta el cierre (recon) y los 3 estados financieros
  5) FP&A                  -> forecast, variance MoM, variance vs presupuesto, anomalias
  6) Strategic Finance     -> run-rate, Rule of 40, burn multiple, camino a breakeven
  7) Internal Controls     -> aseguramiento: integridad de libros, FX, corte, autorizaciones
  8) Audit                 -> re-ejecuta el cierre/estados de forma independiente y opina
  -- Primera linea (maker-checker): cada funcion la firma SU experto de dominio
     (Accounting firma el cierre, Tax firma tax, Treasury firma treasury, etc.).
  9) cross-checks: los agentes deben concordar en los numeros compartidos
 10) consolidar escalamientos
 11) gate FINAL del CFO: firma lo consolidado + lo material (no re-revisa el
     detalle); requiere que la primera linea ya este firmada por sus expertos
 12) board pack consolidado + acciones (Claude), fijados solo si el CFO aprueba

Cada agente deja su analisis y sus flags en el estado compartido; el CFO los
consume. Los numeros los calculan los agentes por codigo (finance_core); el
modelo solo redacta. Una sola fuente de verdad, todo auditable.

Requisitos: ANTHROPIC_API_KEY en el .env de la raiz.
Correr:  python cfo_orchestrator.py
"""

import os
import sys

from dotenv import load_dotenv
from anthropic import Anthropic

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(ROOT, "orchestration"))   # finance_core
sys.path.insert(0, HERE)                                  # shared_state + agentes

import finance_core as fc
from shared_state import CFOContext
import review
import controller_agent
import treasury_agent
import administration_agent
import accounting_reporting_agent
import fpa_agent
import strategic_finance_agent
import internal_controls_agent
import audit_agent

load_dotenv(os.path.join(ROOT, ".env"))
client = Anthropic()
MODEL = "claude-sonnet-4-6"

PERIOD = "2026-05"
# Administration y Accounting & Reporting entran como un solo reporte cada uno:
# ya consolidan sus sub-agentes adentro (AR/AP/Tax y Close/Reporting). Audit es
# independiente (tercera linea) y entra como par de los demas.
AGENTS = ["Controller", "Treasury", "Administration", "Accounting & Reporting",
          "FP&A", "Strategic Finance", "Internal Controls", "Audit"]


def agent(system, prompt, max_tokens=700):
    resp = client.messages.create(
        model=MODEL, max_tokens=max_tokens, system=system,
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.content[0].text


# --- Checks deterministicos de coherencia entre agentes ----------------

def cross_checks(ctx):
    """Verifica que los agentes concuerden en los numeros compartidos.

    Como todos derivan de finance_core, deben coincidir; este check prueba que
    el pipeline esta bien cableado y atrapa derivas futuras (si un agente
    cambia su calculo y deja de concordar, salta aca y no en el board).
    """
    issues = []
    ctrl, trez, fpa = ctx.get("Controller"), ctx.get("Treasury"), ctx.get("FP&A")
    strat = ctx.get("Strategic Finance")

    # 1) op income del Controller == actual de operating income en la varianza de FP&A
    try:
        oi_ctrl = ctrl["pnl"]["operating_income"]
        oi_fpa = next(v for v in fpa["budget_variance"]["rows"]
                      if v["label"] == "Operating income")["actual"]
        if abs(oi_ctrl - oi_fpa) > 1:
            issues.append(f"op income mismatch: Controller {oi_ctrl:,.0f} vs FP&A {oi_fpa:,.0f}")
    except (KeyError, TypeError, StopIteration):
        issues.append("missing data to reconcile op income between Controller and FP&A")

    # 2) burn de Treasury == -op income (cuando hay perdida operativa)
    try:
        oi_ctrl = ctrl["pnl"]["operating_income"]
        expected_burn = -oi_ctrl if oi_ctrl < 0 else 0.0
        if abs(trez["burn"] - expected_burn) > 1:
            issues.append(f"Treasury burn {trez['burn']:,.0f} != -op income {expected_burn:,.0f}")
    except (KeyError, TypeError):
        issues.append("missing data to reconcile Treasury burn")

    # 3) el run-rate de Strategic (revenue mensual x 12) debe atarse al revenue del Controller
    try:
        rev_ctrl = ctrl["pnl"]["revenue"]
        rev_strat = strat["metrics"]["run_rate"] / 12.0
        if abs(rev_ctrl - rev_strat) > 1:
            issues.append(f"revenue mismatch: Controller {rev_ctrl:,.0f} vs Strategic {rev_strat:,.0f}")
    except (KeyError, TypeError, ZeroDivisionError):
        issues.append("missing data to reconcile revenue with Strategic Finance")

    # 4) el AR del agente de Administracion debe atarse al AR del Controller
    try:
        ar_admin = ctx.get("Accounts Receivable")["metrics"]["total"]
        ar_ctrl = ctrl["ar"]["total"]
        if abs(ar_admin - ar_ctrl) > 1:
            issues.append(f"AR mismatch: Controller {ar_ctrl:,.0f} vs AR agent {ar_admin:,.0f}")
    except (KeyError, TypeError):
        issues.append("missing data to reconcile AR with Administration")

    # 5) el resultado neto de Reporting debe atarse al op income del Controller
    try:
        ni_rep = ctx.get("Financial Reporting")["income_statement"]["net_income"]
        oi_ctrl = ctrl["pnl"]["operating_income"]
        if abs(ni_rep - oi_ctrl) > 1:
            issues.append(f"net income mismatch: Controller {oi_ctrl:,.0f} vs Reporting {ni_rep:,.0f}")
    except (KeyError, TypeError):
        issues.append("missing data to reconcile net income with Financial Reporting")

    # 6) la caja del balance de Reporting debe atarse a la caja de Treasury
    try:
        cash_rep = ctx.get("Financial Reporting")["balance_sheet"]["assets"]["cash"]
        if abs(cash_rep - trez["cash"]) > 1:
            issues.append(f"cash mismatch: Treasury {trez['cash']:,.0f} vs Reporting {cash_rep:,.0f}")
    except (KeyError, TypeError):
        issues.append("missing data to reconcile cash with Financial Reporting")

    return issues


def gather_escalations(ctx):
    """Junta los escalamientos de todos los agentes y los ordena por severidad."""
    esc = []
    for a in AGENTS:
        esc.extend(tuple(e) for e in ctx.get(a, "escalations", []))
    order = {"CRITICAL": 0, "HIGH": 1}
    return sorted(esc, key=lambda e: order.get(e[0], 9))


def cfo_final_gate(ctx, esc):
    """The CFO's FINAL sign-off — the second tier, not a detail review.

    Precondition: every function must already be signed off by its domain expert
    (the first line). The CFO does NOT re-review each operational detail (a
    generalist can't); the CFO confirms the first line cleared and signs off on
    the consolidated board pack and the material / cross-cutting items.
    """
    fl = review.first_line_status(ctx)
    print(f"\n  [CFO final sign-off] First line: {len(fl['approved'])}/{fl['total']} "
          "functions signed off by their domain experts.")
    if not fl["all_approved"]:
        print("   NOT cleared by their reviewers (must resolve before the CFO can sign): "
              + ", ".join(fl["rejected"]))
        return False
    serious = [e for e in esc if e[0] in ("HIGH", "CRITICAL")]
    if serious:
        print("   Material / cross-cutting items for the CFO:")
        for sev, msg in serious:
            print(f"     - [{sev}] {msg}")
    if review._auto():
        return True
    try:
        return input("  CFO — approve the consolidated board pack? [y/N]: ").strip().lower() == "y"
    except EOFError:
        return False


def compose_board_pack(ctx):
    ctrl = ctx.get("Controller", "narrative", "")
    trez = ctx.get("Treasury", "narrative", "")
    fpa = ctx.get("FP&A")
    fpa_bits = "\n".join(filter(None, [
        fpa.get("variance_expl", ""), fpa.get("budget_expl", ""), fpa.get("anomaly_expl", ""),
    ]))
    strat = ctx.get("Strategic Finance", "narrative", "")
    admin = ctx.get("Administration", "narrative", "")
    acctrep = ctx.get("Accounting & Reporting", "narrative", "")
    controls = ctx.get("Internal Controls", "narrative", "")
    audit = ctx.get("Audit", "narrative", "")
    prompt = (
        f"--- Controller (close) ---\n{ctrl}\n\n"
        f"--- Treasury (liquidity) ---\n{trez}\n\n"
        f"--- Administration (AR / AP / Tax) ---\n{admin}\n\n"
        f"--- Accounting & Reporting (close + financial statements) ---\n{acctrep}\n\n"
        f"--- FP&A (MoM variance, budget variance, anomalies) ---\n{fpa_bits}\n\n"
        f"--- Strategic Finance (growth, efficiency, path to breakeven) ---\n{strat}\n\n"
        f"--- Internal Controls (assurance) ---\n{controls}\n\n"
        f"--- Audit (independent opinion) ---\n{audit}\n\n"
        "Write the consolidated board pack for the period."
    )
    return agent(
        "You are the CFO. With the inputs from Controller, Treasury, Administration, Accounting & "
        "Reporting, FP&A, Strategic Finance, Internal Controls and Audit, write an executive board "
        "pack of 6-8 sentences, CFO tone, direct, no filler. Do not add new numbers. Write in English.",
        prompt,
    )


def compose_actions(ctx):
    fpa = ctx.get("FP&A")
    esc = gather_escalations(ctx)
    esc_txt = "\n".join(f"  - [{s}] {m}" for s, m in esc) or "  (no escalations)"
    prompt = (
        f"Escalations for the period:\n{esc_txt}\n\n"
        f"FP&A findings:\n{fpa.get('budget_expl', '')}\n{fpa.get('anomaly_expl', '')}\n\n"
        "Propose 3 prioritized actions, one line each."
    )
    return agent(
        "You are the CFO. Propose 3 concrete, actionable, prioritized actions from the "
        "escalations and findings. One line each. Do not add new numbers; use only the figures "
        "in the escalations and findings given. Write in English.",
        prompt,
    )


# --- Pipeline del office -----------------------------------------------

def run(period=PERIOD):
    print("=" * 60)
    print(f"CFO OFFICE | close {period}")
    print("=" * 60)
    ctx = CFOContext()
    ctx.audit("CFO", "start", f"running the office for {period}")

    # Each function runs (the maker) and is signed off by its domain expert (the
    # checker) — first-line maker-checker. Administration and Accounting &
    # Reporting review their own sub-functions inside (AR/AP/Tax, Close/Reporting).
    print("\n[1/8] Controller...")
    controller_agent.run(ctx)
    p = ctx.get("Controller", "pnl", {})
    review.review(ctx, "Controller", f"operating income USD {p.get('operating_income',0):,.0f}")
    print("\n[2/8] Treasury...")
    treasury_agent.run(ctx)
    review.review(ctx, "Treasury",
                  f"cash USD {ctx.get('Treasury','cash',0):,.0f}, runway "
                  + (f"{ctx.get('Treasury','runway') or 0:.1f} months" if ctx.get('Treasury','runway') else "n/a"))
    print("\n[3/8] Administration (AR / AP / Tax)...")
    administration_agent.run(ctx)
    print("\n[4/8] Accounting & Reporting (close + statements)...")
    accounting_reporting_agent.run(ctx)
    print("\n[5/8] FP&A...")
    fpa_agent.run(ctx)
    review.review(ctx, "FP&A", "forecast, MoM and budget variance, anomalies")
    print("\n[6/8] Strategic Finance...")
    strategic_finance_agent.run(ctx)
    sm = ctx.get("Strategic Finance", "metrics", {})
    review.review(ctx, "Strategic Finance",
                  f"Rule of 40 {sm.get('rule_of_40',0):.0f}, burn multiple {sm.get('burn_multiple') or 0:.1f}x")
    print("\n[7/8] Internal Controls...")
    internal_controls_agent.run(ctx)
    cs = ctx.get("Internal Controls", "summary", {})
    review.review(ctx, "Internal Controls",
                  f"{cs.get('n_pass',0)} pass / {cs.get('n_fail',0)} fail / {cs.get('n_exception',0)} exception(s)")
    print("\n[8/8] Audit (independent assurance)...")
    audit_agent.run(ctx)
    review.review(ctx, "Audit", f"opinion {ctx.get('Audit','opinion','?')}")

    # Cross-checks between agents (before escalating or writing).
    issues = cross_checks(ctx)
    if issues:
        for i in issues:
            ctx.audit("cross_check", "FAIL", i)
        print("\n  Pipeline stopped: the agents don't agree on the numbers.")
        ctx.put("CFO", {"status": "halted_inconsistent"})
        ctx.save()
        return ctx
    ctx.audit("cross_check", "ok", "agents consistent on the shared numbers")

    # Record the first-line review status (maker-checker per function).
    fl = review.first_line_status(ctx)
    ctx.put("CFO", {"first_line": fl})
    if not fl["all_approved"]:
        # A function was not signed off by its domain expert -> the close is not
        # ready for the CFO. Do not fabricate a board pack over un-reviewed work.
        ctx.audit("CFO", "blocked", "first-line review incomplete: " + ", ".join(fl["rejected"]))
        ctx.put("CFO", {"status": "blocked_first_line"})
        ctx.save()
        print("\n  Pipeline stopped: a function was not signed off by its domain expert.")
        return ctx

    # Consolidate escalations from all agents.
    esc = gather_escalations(ctx)
    for sev, msg in esc:
        ctx.audit("escalation", sev, msg)

    # Second tier: the CFO's final sign-off on the consolidated pack + material items.
    if not cfo_final_gate(ctx, esc):
        ctx.put("CFO", {"status": "rejected"})
        ctx.audit("CFO", "REJECTED", "CFO did not approve; board pack not fixed")
        ctx.save()
        print("\n  Stopped by CFO decision.")
        return ctx
    ctx.audit("CFO", "approved", "CFO signed off the consolidated board pack")

    board = compose_board_pack(ctx)
    actions = compose_actions(ctx)
    ctx.put("CFO", {"board_pack": board, "actions": actions, "status": "approved"})
    ctx.audit("CFO", "ok", "consolidated board pack and actions fixed")

    path = ctx.save()   # persist state BEFORE displaying it
    print("\n--- BOARD PACK (CFO) ---\n" + board)
    print("\n--- PROPOSED ACTIONS ---\n" + actions)
    print(f"\nShared state saved to: {os.path.basename(path)} "
          f"({len(ctx.state['audit'])} audit events)")
    return ctx


if __name__ == "__main__":
    run()
