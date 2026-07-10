# Timesheet Analysis Tool

An AI-assisted timesheet review tool for HR/payroll teams. Workers submit physical time cards (photos, scans, PDFs, or small Excel sheets). The tool uses OpenAI vision to extract timesheet data, flags uncertain entries for HR review, and exports a payroll-ready Excel workbook.

---

## Table of Contents

1. [What This Is](#what-this-is)
2. [Current Status](#current-status)
3. [Architecture](#architecture)
4. [Quick Start — Local](#quick-start--local)
5. [Environment Variables](#environment-variables)
6. [Full Workflow](#full-workflow)
7. [AI Logic and Business Rules](#ai-logic-and-business-rules)
8. [Configuration](#configuration)
9. [Session Data](#session-data)
10. [Excel Export](#excel-export)
11. [Railway Deployment](#railway-deployment)
12. [Pending Implementation](#pending-implementation)
13. [Known Issues and Limitations](#known-issues-and-limitations)
14. [Key Decisions and Why](#key-decisions-and-why)
15. [File Structure](#file-structure)
16. [Further Reading](#further-reading)
17. [Handover Notes](#handover-notes)

---

## What This Is

**Target users:** HR and payroll staff who process monthly worker timesheets.

**The problem it solves:** Workers submit physical time cards — stamped or handwritten monthly cards, photos, PDFs, or small Excel sheets. HR currently checks these manually and transfers data into Excel. This tool uses AI to extract and structure the data, surface exceptions, and let HR confirm or correct uncertain entries before generating the final payroll Excel file.

**What it is NOT:** This is an internal single-company tool, not a multi-tenant SaaS product. There is no login, no billing, and no cloud database. All state lives in local files on disk (or on a Railway Volume in production). The original handover pack in `docs/` contains a full SaaS rebuild assessment if that direction is ever revisited.

---

## Current Status

> **For any new developer picking this up: read this section first. It tells you exactly what is finished, what is partially done, and what is still planned. Do not assume something is built just because it is mentioned.**

### Done and smoke-tested

- **P0-A — Extraction never overwrites reviewed data.** Re-running extraction on a session that already has reviewed rows merges new rows by `row_id` instead of wiping the file. Fixed in `app.py` (`_merge_rows`, `run_live_extraction_batch_worker`, `session_run_live_extraction_test`).
- **P0-B — OpenAI retry and error sentinel.** Both extraction and second-pass calls retry 3 times with exponential backoff on transient errors. Bad API responses return an error sentinel dict instead of crashing the batch. Fixed in `services/ai_extractor.py`.
- **P0-C — Second-pass sentinel guard.** `run_second_pass_for_row` in `app.py` raises `ValueError` on an error sentinel so the batch marks the row failed rather than silently treating it as `no_suggestion`. Fixed in `app.py` (~line 591).
- **P0-D — `review_status` set at write time.** Extracted rows always land with `review_status` set. Existing null rows are backfilled on first page load. Fixed in `services/ai_extractor.py` and `app.py`.
- **P2 — Review workflow trust.** Debug banner removed from `templates/review.html`. OpenAI status text accurately reflects mock/configured/not-configured. Export triggers a 303 redirect warning when unresolved rows exist; `?force=1` bypasses it.
- **P3 — Operability.** README updated. `.gitignore` covers all runtime data. Repo clutter untracked.
- **P4 — Light UI polish.** Sidebar nav, step wizard, review table layout, assistant panel, button sizing. CSS in `static/style.css`.
- **SOP code config cleaned.** Three baseline codes seeded: `OFF`, `EARLY OUT 早回`, `LATE IN 迟到`. HR adds their own codes during use.

### Validated on real data (P1 testing)

- **Second-pass mechanism runs cleanly** on real OpenAI data: 3/3 rows processed, no crash, no data loss.
- **All audit fields written correctly:** `ai_second_pass_checked`, `ai_confidence`, `ai_recommendation`, `ai_reason`, `ai_batch_status`, `ai_batch_run_id`, `ai_checked_at`.
- **`suggest_only` tier verified** (0.70 confidence → values suggested but not written, HR confirmation required).
- **Enforcement downgrade verified:** a row returned `confidence 0.96, model_recommendation=auto_confirm` but was correctly held to `no_suggestion` because `fields_to_update` was empty.

### NOT yet verified on real data

- **`auto_fill` (75–89%) and `auto_confirm` (90%+) write paths.** These are the tiers that write payroll values without HR seeing them first. The enforcement logic is correct in code, but no real row has gone through these paths end-to-end. A new developer must exercise these tiers on a test row with a clear-stamp image before trusting them with production payroll data.

### Decided but not yet built

See [Pending Implementation](#pending-implementation) for the full list with context.

---

## Architecture

This is a **single-service** FastAPI app with server-side Jinja2 templates. There is no separate frontend framework.

```
HR Browser  ──HTTP──▶  FastAPI app (app.py)
                            │
                            ├── Jinja2 templates  (templates/)
                            ├── Static CSS/JS     (static/)
                            ├── services/
                            │   ├── ai_extractor.py     OpenAI extraction + second-pass
                            │   ├── file_processor.py   Upload, dedup, preprocessing
                            │   ├── session_store.py    Session folders, reviewed_rows.json
                            │   ├── config_store.py     Workers, SOP codes (JSON files)
                            │   └── excel_exporter.py   Excel workbook generation
                            │
                            ├── config/                 Workers, SOP codes, crop templates
                            ├── sessions/               Per-month payroll session data
                            ├── uploads/                Original uploaded files
                            └── OpenAI API  ────────────▶  gpt-5.4 (vision)
```

**Key architectural constraint:** All batch job state (AI extraction batches, second-pass batches) lives in process-level Python dicts (`AI_BATCH_RUNS`, `LIVE_EXTRACTION_BATCH_RUNS` in `app.py`). This means:

- **Single instance only.** If the app ever runs as 2+ instances, batch status 404s and writes clobber each other. Always deploy with `instances = 1`.
- **Batch progress is lost on restart.** Already-processed rows are safe on disk (atomic writes), but the UI progress overlay disappears. HR must re-run second-pass for remaining rows after a restart.

---

## Quick Start — Local

### Prerequisites

- Python 3.10+
- An OpenAI API key with access to `gpt-5.4` (or `gpt-5.5`)

### Setup

```bash
git clone https://github.com/daetan999/timesheet_tool.git
cd timesheet_tool
pip install -r requirements.txt
cp .env.example .env
# Edit .env — add your OPENAI_API_KEY
```

### Run in mock mode (no API key needed, no cost)

```bash
AI_EXTRACTION_MODE=mock uvicorn app:app --reload
```

Open `http://127.0.0.1:8000`. All AI calls return hardcoded fixture data — useful for development and UI testing.

### Run in real mode

```bash
uvicorn app:app --reload
```

Requires `OPENAI_API_KEY` and `AI_EXTRACTION_MODE=real_openai` in `.env`.

---

## Environment Variables

All variables live in `.env` (never committed). See `.env.example`.

| Variable | Required | Default | Description |
|---|---|---|---|
| `OPENAI_API_KEY` | Yes (real mode) | — | Your OpenAI API key |
| `AI_EXTRACTION_MODE` | No | `mock` | `mock` or `real_openai` |
| `OPENAI_MODEL` | No | `gpt-5.5` | Model to use. Recommended: `gpt-5.4` |
| `AUTO_CONFIRM_THRESHOLD` | No | `0.90` | Confidence threshold for auto-confirm. **NOT YET IMPLEMENTED** — currently hardcoded at 0.90 in `services/ai_extractor.py`. |
| `DATA_DIR` | Railway: Yes | `.` | Root path for sessions/, config/, uploads/. Set to `/data` on Railway. **NOT YET IMPLEMENTED** — blocking item for Railway. |

### Intended model-to-threshold mapping (pending build)

| Model | Recommended threshold |
|---|---|
| `gpt-5.5` | `0.90` |
| `gpt-5.4` | `0.93` |
| `gpt-5.4-nano` | `0.97` |

---

## Full Workflow

```
1.  Select month/year        → Creates a payroll session
2.  Confirm workers          → Set active worker list for this month
3.  Confirm SOP codes        → Set known abbreviation meanings
4.  Upload timesheets        → JPG, PNG, HEIC, PDF accepted. XLSX pending (Option B).
5.  Preprocess files         → Converts all inputs to JPEG for AI
6.  Run AI extraction        → OpenAI reads each image, returns structured rows
7.  Review extracted rows    → HR sees Needs Review / Reviewed / All tabs
8.  Run AI second-pass       → AI rechecks uncertain rows, applies confidence tiers
9.  Manual review            → HR works through remaining exceptions in guided modal
10. Add unknown SOP codes    → HR adds meanings for unrecognised codes
11. Export Excel             → Generates payroll-ready workbook (warns if unresolved rows)
12. Check final report       → Summary + per-worker sheets
```

---

## AI Logic and Business Rules

### Initial extraction (`services/ai_extractor.py` → `call_live_openai_extraction`)

- Source-type-specific prompts: `physical_time_card`, `multi_worker_attendance_table`, `pdf_or_excel_style`, `unknown`.
- **Physical time cards:** card number "1" = days 1–15, "2" = days 16–31. Stamped-time overlap inference only at ≥0.65 confidence.
- **Two-layer month-mismatch guard:** model flag + independent `document_month_matches_session()` parser. If triggered, returns one summary row instead of daily rows.
- **Unknown SOP code detection:** post-extraction, any code not in the known SOP set flags the row as `unknown_code`.
- **Conservative rules:** placeholders ("HH:MM", "unknown", "N/A") are stripped, never guessed.

### AI second-pass (`call_second_pass_openai_recheck`)

Rechecks a single row using the full preprocessed image (no crop). Returns a confidence score and recommendation. **Confidence tiers are enforced in code, not just by the model** (`second_pass_recommendation_for_confidence` in `ai_extractor.py`):

| Confidence | Recommendation | Effect |
|---|---|---|
| < 65% | `no_suggestion` | No change, row stays for HR |
| 65–74% | `suggest_only` | Values shown to HR, not written |
| 75–89% | `auto_fill` | Values written, HR must still confirm |
| ≥ threshold | `auto_confirm` | Values written, row marked reviewed with full audit trail |

**Important:** if `fields_to_update` are all empty strings, the recommendation is downgraded to `no_suggestion` regardless of confidence. This was observed in P1 testing: a 0.96-confidence OFF-day row was correctly held back because there were no time fields to fill.

**The `auto_fill` and `auto_confirm` write paths have not been exercised on real data.** The enforcement logic is correct in code but must be validated before trusting with payroll.

### Audit fields (preserved on every row)

```
ai_second_pass_checked    bool
ai_confidence             float (0.0–1.0)
ai_reason                 string (AI's explanation of its decision)
ai_recommendation         string (enforced tier)
ai_suggested_fields       dict (what AI suggested)
ai_original_fields        dict (values before any AI change)
ai_checked_at             ISO timestamp
ai_batch_run_id           string
ai_batch_status           string
```

Auto-confirmed rows remain visible in the Reviewed tab. HR can always reopen a reviewed row.

### Real-world accuracy note

GPT-5.4/5.5 can misread faint or ambiguous stamps. In P1 testing, a faint red-circled stamp was read as `09:19` by extraction and `09:10` by second-pass, when the correct value was `12:18` (confirmed by manual image check). These cases correctly return low confidence and stay for HR review — the system behaves correctly, but AI is not infallible on degraded image quality. The planned mitigation is multi-sample retry (Pending item 6).

---

## Configuration

All config lives in `config/` (committed, persisted on Railway Volume).

### `config/workers.json`

Active workers. HR manages this through the app UI (Step 2). Starts empty — HR adds workers on first use. Format:

```json
[
  {"name": "Worker Name", "worker_type": "Full-time"},
  {"name": "Another Worker", "worker_type": "Part-time"}
]
```

### `config/sop_codes.json`

Known SOP/leave codes. HR manages this (Step 3 + unknown-code workflow). Currently seeded with:

```json
[
  {"code": "OFF", "meaning": "Off day"},
  {"code": "EARLY OUT 早回", "meaning": "Leave early"},
  {"code": "LATE IN 迟到", "meaning": "Enter shift late"}
]
```

**Known UI bug (fix pending):** The add-unknown-code form pre-fills the Code field with the AI's full extracted note text. HR must type a short code only (e.g. `OFF`, not `OFF (month seen APRIL 2026)`). A character-limit validation fix is planned before the HR trial.

### `config/crop_templates.json`

Crop calibration for physical time card layouts. Crop is currently **disabled** — full image preview is used instead. Inaccurate crop is worse than no crop.

---

## Session Data

Each payroll month is a session stored under `sessions/YYYY-MM/`:

```
sessions/
  2026-04/
    session.json                    Month metadata
    uploads/                        Original uploaded files
    preprocessed/                   AI-ready JPEG images
      preprocessing_manifest.json
    review/
      reviewed_rows.json            All rows + HR edits + AI audit fields
    exports/                        Generated Excel files
```

Sessions are not committed (gitignored). On Railway, sessions live on the persistent Volume.

### Persistence behaviour

- **Row saves are atomic** (tmp file + rename). Closing the browser mid-review loses only the current unsaved row.
- **Batch progress lives in memory.** Server restart mid-batch = progress UI gone, but processed rows are safe on disk.
- **On Railway:** all session data persists across restarts via the Volume. Without the Volume, data wipes on every restart.

---

## Excel Export

Generated by `services/excel_exporter.py`. One workbook per session:

- **Summary sheet:** all workers, total hours, SOP code counts, attention flags
- **Per-worker sheets:** one row per calendar day, Start / End / Hours / Notes columns
- Yellow highlighting = leave codes; orange = requires attention
- Filename: `Timesheet Report - <Month> <Year>.xlsx`

Export warns (303 redirect) if any `requires_attention` rows remain. Add `?force=1` to bypass.

---

## Railway Deployment

### Overview

One Railway service runs the entire app. HR accesses it by URL — no installation on their end.

```
HR Browser  ──HTTPS──▶  Railway service (FastAPI + Jinja)
                              ├── Railway Volume at /data
                              │     /data/sessions/
                              │     /data/config/
                              │     /data/uploads/
                              └── OpenAI API
```

### Step-by-step setup

**1. Connect GitHub to Railway**

- Railway dashboard → New Project → Deploy from GitHub repo
- Select `daetan999/timesheet_tool`, branch `main`

**2. Add environment variables** (Railway dashboard → Variables)

```
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-5.4
AI_EXTRACTION_MODE=real_openai
DATA_DIR=/data
```

**3. Add a Volume** (Railway dashboard → Volumes)

- Mount path: `/data`
- Without this, all HR data is wiped on every deploy or restart. Not optional.

**4. Set start command** (Railway → Settings → Deploy)

```
uvicorn app:app --host 0.0.0.0 --port $PORT
```

**5. Seed initial config**

After first deploy, open Railway shell and run:

```bash
mkdir -p /data/config /data/sessions /data/uploads
cp config/sop_codes.json /data/config/sop_codes.json
echo "[]" > /data/config/workers.json
```

**6. Set instances = 1**

In Railway settings, ensure the app runs as a single instance. Multiple instances break batch state and cause write collisions.

**7. Deploy**

Railway auto-deploys on every push to `main`. HR bookmarks the public URL.

### Cost estimate (~45 workers)

| Item | Cost/month |
|---|---|
| Railway service | ~$5–10 |
| Railway Volume | ~$0.25/GB (under 1 GB) |
| OpenAI GPT-5.4 | ~$5–7 |
| **Total** | **~$14/month** |

### Blocking item before Railway works

`DATA_DIR` is not yet implemented. Without it, the app ignores the Volume and writes to the container filesystem (ephemeral). **Implement Pending item 1 before deploying to Railway.**

---

## Pending Implementation

In priority order. Items 1–3 should be done before HR trial.

### 1. `DATA_DIR` environment variable — BLOCKS RAILWAY

Update `services/session_store.py` and `services/config_store.py` to resolve all paths relative to `DATA_DIR` env var (defaulting to `.` for local). Currently uses `Path("sessions")`, `Path("config")` etc. — these don't resolve under the Railway Volume.

### 2. Auto-confirm threshold env-var

Replace hardcoded `0.90` in `second_pass_recommendation_for_confidence` (`services/ai_extractor.py`) with `AUTO_CONFIRM_THRESHOLD` env var. Ideally auto-select based on `OPENAI_MODEL`: 0.90 for gpt-5.5, 0.93 for gpt-5.4, 0.97 for gpt-5.4-nano.

### 3. Add-code form tightening — BEFORE HR TRIAL

In `templates/review.html`, add a character limit (~20 chars), hint text ("Short code only, e.g. AL, MC, OFF"), and client-side validation on the Code field of the add-unknown-code form. Without this, HR will re-pollute the SOP config.

### 4. Excel `.xlsx` input support (Option B)

Accept `.xlsx` and `.xls` uploads. Use `openpyxl` to read cell values, then pass structured text to a text-mode LLM call to map arbitrary layouts to the standard schema. Not a pure parser — arbitrary Excel layouts need an AI pass. Files: `services/file_processor.py`, `services/ai_extractor.py`.

### 5. Correction-memory layer

- **Part 1 (now):** Create `config/correction_memory.json` (starts as `[]`).
- **Part 2 (now):** In `session_save_review_row_as_reviewed`, compare HR's saved values against `ai_original_fields`. Record corrections: worker, source_type, review_reason, ai_value, hr_value, note. Fix gap: rows never through second-pass lack `ai_original_fields` — snapshot pre-edit values before overwriting.
- **Part 3 (post-trial):** Inject relevant corrections into extraction and second-pass prompts. Gate until list is non-empty and trial is stable. Helps with recurring structural quirks (e.g. "Xiaomin's IN1 stamp is often faint"), not one-off misreads.

### 6. Multi-sample retry for low-confidence reads (future)

When second-pass returns inconsistent values across multiple calls, run extraction 2–3× and compare. Diverging results → flag as genuinely uncertain, show all versions to HR. This is the actual fix for faint-stamp misreads — correction memory is not.

---

## Known Issues and Limitations

- **`auto_fill` / `auto_confirm` write paths not validated on real data.** Fix before trusting with payroll.
- **`DATA_DIR` not implemented.** Railway deployment requires this.
- **Add-code form** accepts long strings as codes. Fix before HR trial.
- **Batch progress lost on restart.** Completed rows are safe; HR re-runs second-pass for remaining rows.
- **Single instance only.** No horizontal scaling. Set `instances = 1` on Railway.
- **No authentication.** Anyone with the URL can access. Add Railway IP allowlisting or HTTP basic auth middleware if needed.
- **XLSX not supported yet.** Workers submitting `.xlsx` get a silent rejection. Tell them to export to PDF until Option B is built.
- **Crop disabled.** Full image + lightbox used instead.

---

## Key Decisions and Why

| Decision | Rationale |
|---|---|
| Internal tool, not SaaS | One company's HR team. Full SaaS rebuild assessed in handover docs — deliberately not the current direction. |
| GPT-5.4 | Cost difference vs 5.5 is ~$5/month — negligible. 5.4 is a capable vision model. Nano risks accuracy on faint/handwritten stamps. |
| Auto-confirm at 93% for 5.4 (pending) | 90% fired too easily in tests. Model-dependent: 90% for 5.5, 93% for 5.4, 97% for nano. |
| No custom AI agent framework | The extraction → second-pass → HR review loop is already the right pattern. Adding orchestration adds cost and complexity with no benefit at 45 workers/month. |
| Correction-memory over fine-tuning | Fine-tuning needs hundreds of labeled examples. RAG-style prompt enrichment from corrections achieves most of the benefit with minimal infrastructure. |
| Railway single-service | FastAPI + Jinja = no separate frontend. One service, one Volume. Simple, cheap, right-sized. |
| Ephemeral batch state | Acceptable for single-user internal tool. Redis/DB for job state is SaaS territory. |
| Crop disabled | Inaccurate crop (wrong row shown) is worse than full card. Disabled until calibration is proven reliable. |

---

## File Structure

```
timesheet_tool/
├── app.py                          All FastAPI routes, batch workers, row save/reopen, export
├── requirements.txt
├── .env.example
├── .gitignore
├── PROJECT_BRIEF.md                Original product spec
├── BUILD_PLAN.md                   Stage-by-stage build plan (includes AI second-pass + ML notes)
├── AI_EXTRACTION_SPEC.md           Physical time card layout and extraction rules
│
├── services/
│   ├── ai_extractor.py             OpenAI calls, extraction + second-pass, confidence tiers
│   ├── file_processor.py           Upload, SHA-256 dedup, preprocessing (PIL + PyMuPDF)
│   ├── session_store.py            Session folders, reviewed_rows.json load/save
│   ├── config_store.py             Workers, SOP codes, crop templates
│   └── excel_exporter.py           Excel workbook generation (openpyxl)
│
├── templates/
│   ├── base.html                   Sidebar nav, step wizard, page shell
│   ├── review.html                 Main review page (largest file — most UI logic here)
│   ├── index.html                  Home / month selection
│   ├── started.html                Session confirmation
│   ├── upload.html                 File upload
│   ├── workers.html                Worker management
│   ├── sop_codes.html              SOP code management
│   └── crop_calibration.html       Crop debug (disabled feature)
│
├── static/
│   └── style.css                   All styles
│
├── config/                         Committed — persisted on Railway Volume
│   ├── workers.json                Active workers (starts empty)
│   ├── sop_codes.json              Known SOP codes (3 seeded)
│   └── crop_templates.json         Crop calibration (disabled)
│
├── docs/
│   ├── superpowers/specs/
│   │   └── 2026-06-29-timesheet-hardening-design.md
│   └── swarm/
│       └── mission-brief.md
│
└── sessions/                       GITIGNORED — runtime only
    └── YYYY-MM/
        ├── session.json
        ├── uploads/
        ├── preprocessed/
        │   └── preprocessing_manifest.json
        ├── review/
        │   └── reviewed_rows.json
        └── exports/
```

---

## Further Reading

- `docs/superpowers/specs/2026-06-29-timesheet-hardening-design.md` — full hardening design spec with Codex adversarial review findings and acceptance criteria
- `docs/swarm/mission-brief.md` — the agent implementation brief with exact file/line references for every P0–P4 change
- `PROJECT_BRIEF.md` — original product spec from when the tool was first built
- `BUILD_PLAN.md` — stage-by-stage plan including AI second-pass and ML sequencing notes
- `AI_EXTRACTION_SPEC.md` — physical time card layout, extraction priorities, conservative rules

---

## Handover Notes

If you are picking this up fresh:

1. Read this README fully.
2. Read `docs/superpowers/specs/2026-06-29-timesheet-hardening-design.md`.
3. Run locally in mock mode (`AI_EXTRACTION_MODE=mock uvicorn app:app --reload`) to see the full workflow.
4. Check `services/ai_extractor.py` → `second_pass_recommendation_for_confidence` — threshold is hardcoded at `0.90`. Implement env-var (Pending item 2).
5. Implement `DATA_DIR` (Pending item 1) — this blocks Railway from persisting data.
6. Fix the add-code form (Pending item 3) before any HR trial.
7. Validate `auto_fill` / `auto_confirm` write paths on a real row with a clearly-readable time card image.
8. Deploy to Railway following the steps above.

**Biggest risks:**
1. Unvalidated write tiers (auto_fill/auto_confirm) — could silently write wrong payroll values
2. Missing `DATA_DIR` implementation — Railway loses all data on restart without it
3. Add-code form — HR will re-pollute SOP config on day one if not fixed
