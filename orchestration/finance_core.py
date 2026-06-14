"""
finance_core.py - Calculo financiero deterministico (numeros crudos).

Lee los mismos CSV que el MCP server y devuelve numeros (no texto), para
que el orquestador pueda hacer cuentas (ej: runway = caja / burn) sin
depender del modelo. Una sola fuente de datos: ../finance-mcp/data.

Nota de arquitectura: en un refactor "de produccion", el MCP server
importaria estas funciones en vez de tener su propia copia de la logica.
Aca lo mantengo separado para no tocar el server ya validado.
"""

import csv
import os
import datetime

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "finance-mcp", "data")
LATEST = "2026-05"


def _load(name):
    with open(os.path.join(DATA, name), newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


_ENT = _load("entities.csv")
_FX = {(r["period"], r["currency"]): float(r["units_per_usd"]) for r in _load("fx_rates.csv")}
_PNL = _load("pnl_activity.csv")
_BS = _load("balance_sheet.csv")
_BUD = _load("budget.csv")
_INV = _load("ar_invoices.csv")
_AP = _load("ap_invoices.csv")
_TAX = _load("tax_obligations.csv")
_CCY = {r["entity_id"]: r["currency"] for r in _ENT}


def _usd(amount_local, currency, period):
    return amount_local / _FX[(period, currency)]


def pnl_usd(period):
    """P&L consolidado en USD para un periodo. Devuelve numeros."""
    agg = {}
    for r in _PNL:
        if r["period"] != period:
            continue
        usd = _usd(float(r["amount_local"]), _CCY[r["entity_id"]], period)
        agg[r["account_code"]] = agg.get(r["account_code"], 0.0) + usd
    rev = agg.get("4000", 0.0)
    cogs = agg.get("5000", 0.0)
    gross = rev - cogs
    sm = agg.get("6000", 0.0)
    rd = agg.get("6100", 0.0)
    ga = agg.get("6200", 0.0)
    opex = sm + rd + ga
    return {
        "revenue": rev,
        "cogs": cogs,
        "gross": gross,
        "sm": sm,
        "rd": rd,
        "ga": ga,
        "opex": opex,
        "operating_income": gross - opex,
    }


def cash_total_usd():
    """Caja consolidada en USD al ultimo cierre."""
    return sum(
        _usd(float(r["amount_local"]), _CCY[r["entity_id"]], LATEST)
        for r in _BS if r["account_code"] == "1000"
    )


def ar_overdue_usd(as_of="2026-05-31"):
    """Cartera por cobrar en USD: corriente vs vencida (todo lo pasado de fecha).

    Aplica la definicion correcta: 'vencido' = cualquier factura abierta
    pasada su fecha de vencimiento (incluye el tramo 1-30).
    """
    asof = datetime.date.fromisoformat(as_of)
    current = 0.0
    overdue = 0.0
    for r in _INV:
        if r["status"] != "open":
            continue
        due = datetime.date.fromisoformat(r["due_date"])
        amt = _usd(float(r["amount_local"]), r["currency"], LATEST)
        if (asof - due).days <= 0:
            current += amt
        else:
            overdue += amt
    total = current + overdue
    return {"current": current, "overdue": overdue, "total": total,
            "overdue_pct": (overdue / total * 100) if total else 0}


# --------------------------------------------------------------------------
# Presupuesto y varianza (FP&A). Numeros deterministicos, calculados aca.
# --------------------------------------------------------------------------

def _budget_lines_usd(period):
    """Lineas del presupuesto consolidadas en USD (detalle por cuenta).

    El budget ya esta en USD (plan del grupo), no se convierte por FX.
    """
    agg = {}
    for r in _BUD:
        if r["period"] != period:
            continue
        agg[r["account_code"]] = agg.get(r["account_code"], 0.0) + float(r["amount_usd"])
    return agg


def _pnl_lines_usd(period):
    """Lineas de P&L (actuals) consolidadas en USD, detalle por cuenta."""
    agg = {}
    for r in _PNL:
        if r["period"] != period:
            continue
        usd = _usd(float(r["amount_local"]), _CCY[r["entity_id"]], period)
        agg[r["account_code"]] = agg.get(r["account_code"], 0.0) + usd
    return agg


def budget_usd(period):
    """Presupuesto consolidado en USD para un periodo (mismo shape que pnl_usd)."""
    b = _budget_lines_usd(period)
    rev = b.get("4000", 0.0)
    cogs = b.get("5000", 0.0)
    gross = rev - cogs
    opex = b.get("6000", 0.0) + b.get("6100", 0.0) + b.get("6200", 0.0)
    return {
        "revenue": rev,
        "cogs": cogs,
        "gross": gross,
        "opex": opex,
        "operating_income": gross - opex,
    }


def variance_usd(period):
    """Varianza presupuestaria consolidada en USD (actual vs budget) por linea.

    Para cada linea devuelve budget, actual, var ($) y var (%), y clasifica la
    varianza como 'F' (favorable) o 'U' (desfavorable) segun el tipo de linea:
    en ingresos/utilidad, mayor que el plan es favorable; en costos, mayor que
    el plan es desfavorable.

    El % usa el valor ABSOLUTO del budget en el denominador, para que el signo
    del % siga al signo del $ aun cuando el budget de un subtotal sea negativo
    (ej: una perdida operativa planificada). Asi no confunde la lectura.
    """
    a = _pnl_lines_usd(period)
    b = _budget_lines_usd(period)

    def line(label, actual, budget, kind):
        var = actual - budget
        favorable = (var >= 0) if kind == "income" else (var <= 0)
        pct = (var / abs(budget) * 100) if budget else 0.0
        return {
            "label": label, "actual": actual, "budget": budget,
            "var": var, "var_pct": pct, "kind": kind,
            "flag": "F" if favorable else "U",
        }

    rev_a, rev_b = a.get("4000", 0.0), b.get("4000", 0.0)
    cogs_a, cogs_b = a.get("5000", 0.0), b.get("5000", 0.0)
    sm_a, sm_b = a.get("6000", 0.0), b.get("6000", 0.0)
    rd_a, rd_b = a.get("6100", 0.0), b.get("6100", 0.0)
    ga_a, ga_b = a.get("6200", 0.0), b.get("6200", 0.0)
    gross_a, gross_b = rev_a - cogs_a, rev_b - cogs_b
    opex_a, opex_b = sm_a + rd_a + ga_a, sm_b + rd_b + ga_b
    oi_a, oi_b = gross_a - opex_a, gross_b - opex_b

    return [
        line("Revenue",           rev_a,   rev_b,   "income"),
        line("Cost of revenue",   cogs_a,  cogs_b,  "cost"),
        line("Gross profit",      gross_a, gross_b, "income"),
        line("Sales & marketing", sm_a,    sm_b,    "cost"),
        line("R&D",               rd_a,    rd_b,    "cost"),
        line("G&A",               ga_a,    ga_b,    "cost"),
        line("Total opex",        opex_a,  opex_b,  "cost"),
        line("Operating income",  oi_a,    oi_b,    "income"),
    ]


def material_variances(period, pct_threshold=5.0, usd_threshold=20000.0):
    """Lineas cuya varianza es material: |%| >= umbral Y |$| >= umbral.

    El doble umbral evita marcar lineas chicas con % alto o lineas grandes con
    % chico. Default 5% para una revision MENSUAL (10% dejaria pasar sobregastos
    reales de opex); el piso de USD 20k (~1.5% del revenue mensual consolidado)
    suprime swings absolutos triviales. Se pueden ajustar por argumento.
    """
    out = []
    for v in variance_usd(period):
        if abs(v["var_pct"]) >= pct_threshold and abs(v["var"]) >= usd_threshold:
            out.append(v)
    return out


# --------------------------------------------------------------------------
# Metricas estrategicas (Strategic Finance). Numeros deterministicos, sin
# cliente: el agente solo las narra; el eval harness las puede testear.
# --------------------------------------------------------------------------

PERIODS = sorted({r["period"] for r in _PNL})


def _avg_mom_growth(values):
    growths = [(values[i] / values[i - 1] - 1) for i in range(1, len(values))
               if values[i - 1]]
    return sum(growths) / len(growths) if growths else 0.0


def strategic_scenarios(rev_latest, base_growth, op_margin):
    """3 escenarios de crecimiento; el margen se mantiene constante a proposito:
    crecer mueve el run-rate y el Rule of 40, pero no el margen, que es el
    verdadero cuello de botella estructural."""
    out = []
    for name, g in [("Low", base_growth * 0.5), ("Base", base_growth), ("High", base_growth * 1.5)]:
        ann = (1 + g) ** 12 - 1
        out.append({
            "name": name, "mom_growth": g,
            "run_rate_12m": rev_latest * ((1 + g) ** 12) * 12,
            "rule_of_40": ann * 100 + op_margin * 100,
        })
    return out


def strategic_metrics(periods=None):
    """Metricas SaaS estrategicas, todas deterministicas:
    run-rate (ARR proxy), Rule of 40, burn multiple, magic number, mix de
    gasto, gap de margen a breakeven y escenarios de crecimiento.

    El crecimiento se anualiza componiendo el promedio MoM (proxy; no hay
    historico YoY con pocos meses). burn_multiple/magic_number son None si no
    hay revenue nuevo o S&M previo (evita dividir por cero).
    """
    periods = periods or PERIODS
    series = {p: pnl_usd(p) for p in periods}
    rev = [series[p]["revenue"] for p in periods]
    op = [series[p]["operating_income"] for p in periods]
    sm = [series[p]["sm"] for p in periods]
    rev_latest, rev_prev, op_latest, sm_prev = rev[-1], rev[-2], op[-1], sm[-2]
    latest = series[periods[-1]]

    g = _avg_mom_growth(rev)
    ann_growth = (1 + g) ** 12 - 1
    op_margin = (op_latest / rev_latest) if rev_latest else 0.0
    net_new = rev_latest - rev_prev
    burn = -op_latest if op_latest < 0 else 0.0
    return {
        "run_rate": rev_latest * 12,
        "mom_growth": g, "ann_growth": ann_growth,
        "op_margin": op_margin,
        "rule_of_40": ann_growth * 100 + op_margin * 100,
        "net_new_rev": net_new, "monthly_burn": burn,
        "burn_multiple": (burn / net_new) if net_new > 0 else None,
        "magic_number": (net_new / sm_prev) if sm_prev > 0 else None,
        "mix": {k: (latest[k] / rev_latest if rev_latest else 0.0)
                for k in ("cogs", "sm", "rd", "ga")},
        "breakeven_gap_pp": (-op_margin * 100) if op_margin < 0 else 0.0,
        "scenarios": strategic_scenarios(rev_latest, g, op_margin),
    }


# --------------------------------------------------------------------------
# Administration: AR, AP y Tax. Numeros deterministicos en USD (a tasa de
# cierre LATEST, igual que el aging). El agente de Administracion narra; aca
# se calculan las cifras.
# --------------------------------------------------------------------------

def ar_metrics(period=LATEST, as_of="2026-05-31"):
    """Cuentas por cobrar: corriente/vencida (reusa ar_overdue_usd) + DSO."""
    ar = ar_overdue_usd(as_of)
    rev = pnl_usd(period)["revenue"]
    asof = datetime.date.fromisoformat(as_of)
    n_overdue = sum(1 for r in _INV if r["status"] == "open"
                    and datetime.date.fromisoformat(r["due_date"]) < asof)
    return {**ar, "dso": (ar["total"] / rev * 30) if rev else 0.0, "n_overdue": n_overdue}


def ap_metrics(period=LATEST, as_of="2026-05-31"):
    """Cuentas por pagar: abierto, vencido, por vencer (<=30d) y DPO."""
    asof = datetime.date.fromisoformat(as_of)
    open_total = overdue = upcoming_30 = 0.0
    n_overdue = 0
    for r in _AP:
        if r["status"] != "open":
            continue
        amt = _usd(float(r["amount_local"]), r["currency"], LATEST)
        open_total += amt
        days = (datetime.date.fromisoformat(r["due_date"]) - asof).days
        if days < 0:
            overdue += amt
            n_overdue += 1
        elif days <= 30:
            upcoming_30 += amt
    cogs = pnl_usd(period)["cogs"]
    return {"open_total": open_total, "overdue": overdue, "upcoming_30d": upcoming_30,
            "n_overdue": n_overdue, "dpo": (open_total / cogs * 30) if cogs else 0.0}


def tax_metrics(as_of="2026-05-31"):
    """Obligaciones impositivas pendientes: total, vencido, por vencer y por jurisdiccion."""
    asof = datetime.date.fromisoformat(as_of)
    pending_total = overdue = upcoming_30 = 0.0
    by_juris = {}
    for r in _TAX:
        if r["status"] != "pending":
            continue
        amt = _usd(float(r["amount_local"]), r["currency"], LATEST)
        pending_total += amt
        by_juris[r["jurisdiction"]] = by_juris.get(r["jurisdiction"], 0.0) + amt
        days = (datetime.date.fromisoformat(r["due_date"]) - asof).days
        if days < 0:
            overdue += amt
        elif days <= 30:
            upcoming_30 += amt
    return {"pending_total": pending_total, "overdue": overdue,
            "upcoming_30d": upcoming_30, "by_jurisdiction": by_juris}


# --------------------------------------------------------------------------
# Forecast directo de caja a 13 semanas (Treasury). Deterministico, en USD.
# --------------------------------------------------------------------------

AR_COLLECTION_RATE = 0.90   # 10% de prevision sobre cobranzas


def cash_forecast_13w(start="2026-06-01"):
    """Forecast directo de caja a 13 semanas (semanal), en USD.

    Modelo (asunciones explicitas y defendibles, para no doble-contar):
    - Caja inicial = caja consolidada al cierre.
    - Burn operativo recurrente: el burn mensual prorrateado por semana (x12/52),
      aplicado cada semana. Es el drenaje go-forward, ya neto de la operacion.
    - Capital de trabajo de saldos EXISTENTES al cierre (NO incluido en el burn):
      se cobran las facturas AR abiertas (al 90%) y se pagan AP y tax pendientes
      en la semana de su vencimiento; lo vencido cae en la semana 1 (catch-up).
    El burn es el flujo en curso; los saldos abiertos son stock que se liquida
    una sola vez -> no se duplica el revenue/costo.
    """
    start_d = datetime.date.fromisoformat(start)
    start_cash = cash_total_usd()
    monthly_burn = max(0.0, -pnl_usd(LATEST)["operating_income"])
    weekly_burn = monthly_burn * 12.0 / 52.0

    weeks = [{"inflow": 0.0, "outflow": 0.0} for _ in range(13)]

    def _bucket(due_iso):
        wi = (datetime.date.fromisoformat(due_iso) - start_d).days // 7
        if wi < 0:
            return 0          # vencido -> semana 1 (catch-up)
        return wi if wi <= 12 else None   # mas alla del horizonte: se ignora

    for r in _INV:            # AR: cobranzas (inflow), al 90%
        if r["status"] != "open":
            continue
        b = _bucket(r["due_date"])
        if b is not None:
            weeks[b]["inflow"] += _usd(float(r["amount_local"]), r["currency"], LATEST) * AR_COLLECTION_RATE
    for r in _AP:             # AP: pagos (outflow)
        if r["status"] != "open":
            continue
        b = _bucket(r["due_date"])
        if b is not None:
            weeks[b]["outflow"] += _usd(float(r["amount_local"]), r["currency"], LATEST)
    for r in _TAX:            # tax: pagos (outflow)
        if r["status"] != "pending":
            continue
        b = _bucket(r["due_date"])
        if b is not None:
            weeks[b]["outflow"] += _usd(float(r["amount_local"]), r["currency"], LATEST)

    cash = start_cash
    rows = []
    min_cash, min_week, week_negative = start_cash, 0, None
    for i in range(13):
        inflow = weeks[i]["inflow"]
        outflow = weeks[i]["outflow"] + weekly_burn
        net = inflow - outflow
        cash += net
        rows.append({"week": i + 1, "inflow": inflow, "outflow": outflow,
                     "net": net, "ending_cash": cash})
        if cash < min_cash:
            min_cash, min_week = cash, i + 1
        if week_negative is None and cash < 0:
            week_negative = i + 1

    return {"start": start, "starting_cash": start_cash, "weekly_burn": weekly_burn,
            "rows": rows, "ending_cash": cash, "min_cash": min_cash,
            "min_week": min_week, "week_cash_negative": week_negative}
