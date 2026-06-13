# AI Finance Training

Hands-on projects building automation and AI tools for finance work, moving
from simple API calls up to a reliable multi-agent finance operating model.
Each piece is small, self-contained, and written to be read and run by
someone else.

## Projects (in order of depth)

### `finance-mcp/` — Finance MCP connector (server + client)
A Model Context Protocol server exposing the finance system of a fictional
post-seed SaaS (6 legal entities, 6 currencies) as tools: consolidated P&L,
balance sheet, AR aging, and cash position, with multi-currency
consolidation at period-close FX. Includes a Python MCP client that drives
it over the real protocol. See [`finance-mcp/README.md`](finance-mcp/README.md).

**Concepts:** MCP server/client, FastMCP, stdio transport, tool schemas,
multi-entity consolidation, input validation, read-only safety surface.

### `orchestration/` — Multi-agent orchestration + reliability
An orchestrator coordinating specialized sub-agents (close review, cash
forecast, reporting), plus the **AI Finance Operating Model v2**: deterministic
checks between stages, an audit trail, severity-based escalation, and a
human-in-the-loop approval gate. See [`orchestration/README.md`](orchestration/README.md).

**Concepts:** prompt chaining, routing, sub-agents, state passing, audit
trail, escalation rules, human-in-the-loop. Numbers are computed by code;
the model only reasons and writes.

### `agent_fx.py` — AI agent with tool use
A first agent: Claude decides when to call a `get_rate` tool, the code runs
it against a real API, and Claude writes the final answer.

**Concepts:** tool use / function calling, the decide-execute-return loop,
secrets via `.env`.

### `fx_rates.py` — Real-time foreign exchange rates
Pulls official ECB rates (Frankfurter API), prints an aligned multi-currency
table, converts amounts, and handles failures instead of crashing. No API key.

**Concepts:** REST API calls, JSON parsing, functions, error handling.

### `api_fx.py` — First API call
The starting point for working with APIs: hits a public FX endpoint, reads
the JSON response, and prints the rates. The minimal version that `fx_rates.py`
builds on.

**Concepts:** what a REST API is, GET requests, reading JSON, status codes.

### `hello_finance.py` — First script
A minimal margin calculation. The starting point.

## `diagrams/`
Architecture diagrams, one per milestone (tool use, MCP, the SDK's role, and
the operating model). See [`diagrams/README.md`](diagrams/README.md).

## Requirements

- Python 3
- `pip install requests anthropic python-dotenv mcp`
- An Anthropic API key in a local `.env` as `ANTHROPIC_API_KEY` (never committed)

## Design principle

In finance the number has to be right. Across every project, numbers are
computed deterministically by code; the model routes, reasons, and writes
prose, but never invents a figure. Controls and a human sign off at the
critical points.

## About

Training repo documenting my move from 17 years in senior finance into
AI-enabled finance engineering. Built step by step, project by project.
