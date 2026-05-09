# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What Jura is

Jura is a **state jurisdiction & regulatory authority agent** for small commercial insurance underwriting. It runs on **port 8003**, sits in front of Aria (W2-B, port 8001), and decides whether each submission is admitted-eligible, must be routed to surplus lines (E&S), needs a compliance disclosure, or is hard-blocked by statute.

Jurisdiction rules are **deterministic YAML lookups** (`config/*.yaml`). The LLM is only used for plain-language regulatory rationale — never for routing decisions.

## Commands

All commands assume the venv is active: `source .venv/bin/activate`.

```bash
# Run server (auto-reload during dev)
uvicorn jura.server:app --port 8003 --reload

# Run server in browser-HITL mode (used by demo)
HITL_MODE=browser uvicorn jura.server:app --port 8003 --reload

# Tests
pytest tests/                        # full suite
pytest tests/test_checker.py::test_fl_moratorium_raises -v   # single test

# Exec demo — seeds 5 sample submissions, prints Rich summary
python run_demo.py                   # auto-starts server if not running
python run_demo.py --demo            # also opens browser at http://localhost:8003/
python run_demo.py --no-reset        # skip clearing DB + audit logs

# DB / audit smoke check
python verify_db.py
```

Provider switching: edit `config/llm_config.yaml` → `provider: openai | anthropic`. Keys read from `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` (loaded from `.env` by `load_dotenv()` in the lifespan).

Override Aria endpoint: `ARIA_ENDPOINT=http://host:port/score`. Override SLA window: `COMPLIANCE_SLA_HOURS=24`.

## Architecture

### Routing pipeline

`POST /jurisdiction` → `jura.router.JurisdictionRouter.route()` is the single entry point. It:

1. Inserts the submission into SQLite (`data/jura.db`) and marks it `jura_checking`.
2. Calls `jura.checker.run_jurisdiction_check(event)` (pure, deterministic).
3. Branches on the result into one of five handlers, each of which sets a terminal status, writes a notice file, and returns an outcome dict:

| Outcome | Trigger | Status | Side effect |
|---|---|---|---|
| `blocked` | `JurisdictionBlock` raised, or `has_block` flag | `jurisdiction_blocked` | hold notice file |
| `disclose_pending` | any `disclose`-level DOI flag | `admitted_disclose_pending` | disclosure docs + HITL card |
| `es_pending` | `es_eligible` and no admitted path | `surplus_pending` | E&S notice with mock declinations |
| `multi_state_conflict` | `MultiStateConflict` raised | `multi_state_conflict` | conflict HITL card |
| `forwarded_to_aria` | clean admitted path | `forwarded_to_aria` | `POST` to `ARIA_ENDPOINT` (falls back to `data/aria_pending/*.json` if Aria is down) |

If you add a new outcome, update both `VALID_STATUSES` in `jura/db.py` and the `_nav_counts` / templates that render queue chips.

### Deterministic checker (`jura/checker.py`)

- All YAML configs are loaded **once at import time** (module-level globals).
- `evaluate_doi_rules()` evaluates each rule's `trigger_condition` via `eval()` with a **restricted ctx** — no `__builtins__`, only event fields, derived flags, state-code constants, and ZIP-set proxies (`CA_FAIR_PLAN_ZIPS`, `FL_MORATORIUM_ZIPS`). Adding a new variable to a trigger means adding it to the `ctx` dict; otherwise `eval` raises and the rule silently treats it as not-triggered.
- Two YAML rule classes:
  - **Hard geo-blocks** (FL moratorium, CA FAIR Plan) raise `JurisdictionBlock` *before* DOI evaluation.
  - **DOI rules** (`config/doi_rules.yaml`, keyed by state) produce `DOIFlag`s with level `block` / `disclose` / `warn` / `clear`.
- For multi-state submissions the mailing-state rules are also evaluated and merged; `detect_multi_state_conflict()` groups flags by topic (`_TOPIC_KEYWORDS`) and reports topics where the levels differ across states.
- `market` is derived in this priority order: any `block` → `restricted`; conflicts → `multi_state_conflict`; admitted state → `admitted`; else → `surplus_lines`.

### Persistence layer

- **SQLite** (`data/jura.db`) — single `submissions` table, managed by `jura/db.py`. `update_status` validates against `VALID_STATUSES`. `_SEED` in this file mirrors `_SAMPLES` in `run_demo.py`; keep them in sync when changing demo fixtures.
- **JSONL audit logs** (`data/jurisdiction_log.jsonl`, `data/compliance_decisions.jsonl`) — `JurisdictionAuditLogger` (`jura/audit.py`) writes one entry per jurisdiction check with a SHA-256 `log_hash` over the canonical JSON of the entry. `verify_integrity()` re-hashes each line; tamper-evident, not tamper-proof.
- **Generated artifacts** under `data/`: `hold_notices/`, `disclosures/`, `es_notices/`, `aria_pending/`. The lifespan handler creates these directories on startup.

### HITL modes

`HITL_MODE` env var (default `terminal`) selects how disclose/block/conflict review is surfaced:

- `terminal` — `jura.router` calls into `hitl.card` to render Rich panels and prompt the reviewer in-process via `asyncio.to_thread`. Approval forwards to Aria; rejection leaves the submission pending.
- `browser` — no terminal blocking; reviewers handle queue at `/compliance` (router under `compliance/review.py`, mounted on the FastAPI app).

### UI (templates/)

Two parallel template trees:
- **Exec demo** (`base.html` + `queue.html`, `blocks.html`, `audit_log.html`, `insights.html`) — mounted by `jura/views.py`.
- **Compliance portal** (`compliance_base.html` + `compliance_queue.html`, `disclosure_review.html`, `compliance_blocks.html`, `compliance_es.html`, `compliance_conflicts.html`, `compliance_audit.html`) — mounted under `/compliance` by `compliance/review.py`.

Nav chip counts come from `_nav_counts(db)` / `_counts(db)` — when a status is added, update both helpers.

## Conventions worth knowing

- The ZIP-set membership operators in YAML triggers (`premises_zip in CA_FAIR_PLAN_ZIPS`) work because `_FairPlanZipProxy` / `_MoratoriumZipProxy` implement `__contains__`. CA uses **3-digit prefix** matching; FL uses full 5-digit ZIP membership.
- Rule **topics** for conflict detection are matched by keyword in `rule_name`/`rule_id` (see `_TOPIC_KEYWORDS`). New rule families that should participate in conflict detection need a topic keyword added.
- `run_jurisdiction_check` is pure and synchronous — keep it that way; all I/O (DB, HTTP to Aria, file writes, HITL prompts) belongs in the router/handlers.
- `pytest.ini_options` sets `pythonpath = ["."]` so tests import `jura.*` directly without an editable install.
