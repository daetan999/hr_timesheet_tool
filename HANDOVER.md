# PORTFOLIO HANDOVER — Full Specification for the Continuation Session

**Purpose of this branch:** temporary staging + handover. It carries two fully-built, sanitization-swept repos (`technical-resume/`, `hospitality-mlops-platform/`) that could not be pushed to their own repositories from the originating session (its GitHub token was scoped to `hr_timesheet_tool` only), plus this complete specification for finishing the portfolio. **Delete this branch once migration is complete.**

---

## 1. Mission

Build an elite, enterprise-grade **technical blueprint portfolio** for Technical Sales evaluations, owned by GitHub user `daetan999`. Voice and quality bar: *Elite Principal Solutions Engineer & Senior DevOps Specialist*. Every artifact must look like the work of someone who designs production systems for a living: architecture-first, quantified business impact, immaculate diagrams, zero confidential data.

## 2. Portfolio state at handover

| Piece | Status | Where |
|---|---|---|
| `hr_timesheet_tool` | ✅ Published, public-ready. Single-commit history (`feat: initial enterprise architectural skeleton release`), SVG diagrams, screenshots | github.com/daetan999/hr_timesheet_tool (main) |
| MERIDIAN MLOps platform blueprint | ✅ Built + swept, **not yet in its own repo** | `hospitality-mlops-platform/` on this branch |
| Technical-resume hub | ✅ Built + swept, **not yet pushed** | `technical-resume/` on this branch → push into existing repo `daetan999/technical_resume` |
| FHNP sanitized duplicate | ❌ Not started — needs FHNP repo access | to be built |
| ADK agent sanitized duplicate | ❌ Not started — needs adk_agent_mmm_pnl access | to be built |
| Semis-Analysis-Web | ❓ Unassessed | include only if it has real substance |

## 3. Immediate migration tasks (before any new work)

1. Push `technical-resume/*` (contents, not the folder) into `daetan999/technical_resume`, branch `main`.
2. Push `hospitality-mlops-platform/*` into `daetan999/hospitality-mlops-platform` (user must pre-create it empty; keep this exact name — the hub README links to it).
3. Commit style for both: **single commit**, author `daetan999 <daetan999@gmail.com>`, message `feat: initial enterprise architectural blueprint release`. **No AI/assistant references or co-author trailers in any commit, ever.**
4. After both are live and the user confirms: delete this `portfolio-staging` branch from `hr_timesheet_tool`. Also remind the user the stale branch `claude/hr-timesheet-enterprise-readme-aj9hgl` on `hr_timesheet_tool` still needs manual deletion.

## 4. New work — FHNP sanitized duplicate

- **Source:** `daetan999/FHNP`. Its diagrams (UML workflow diagrams, GCP infrastructure diagram) live in the **`Design_files`** directory — use them as ground truth, but **rebuild** them in the portfolio design system (Section 7) rather than copying exported images that may embed confidential labels.
- **Hard rule: the string "FHNP" (and whatever it expands to) must never appear** in the public repo, its README, diagrams, commits, or the hub. Refer to it by a neutral sanitized identity, e.g. "Enterprise GCP Data Platform" (final name at the agent's discretion, cleared with the user).
- **Strip:** GCP project names & project IDs, data lake / BigQuery dataset & table names, bucket names, service-account emails, internal endpoints/hostnames, API keys/tokens, client or personnel names, anything identifying the employer/client. Replace with `<placeholder>` conventions or fictional-but-plausible names, exactly as done in `hospitality-mlops-platform/feature_store/feature_definitions.py`.
- **Preserve:** architecture, data model shapes, workflow logic, SLOs, engineering trade-offs. Sanitize, don't lobotomize.
- **Deliverable repo** (user pre-creates empty, private): suggested name `gcp-data-platform-blueprint`. Structure mirrors `hospitality-mlops-platform/`: showpiece README (badges → exec summary → verbatim disclaimer (Section 6) → SVG diagrams w/ Mermaid sources in `<details>` → stack table w/ justifications → roadmap), `docs/` deep-dives, `docs/assets/` SVGs, illustrative config/code skeletons, MIT LICENSE.

## 5. New work — ADK agent sanitized duplicate

- **Source:** `daetan999/adk_agent_mmm_pnl` — an LLM agent system on Google's Agent Development Kit for marketing-mix-modeling P&L analytics.
- **It has no diagrams. Create them** from the code: (a) agent architecture/topology diagram — agents, tools, model calls, data flows; (b) request-lifecycle sequence diagram; (c) GCP deployment view if the code evidences one. Same design system.
- Same strip list as FHNP (GCP identifiers, dataset/table names, endpoints, prompts containing client data). The concepts "MMM" and "P&L analytics" are generic and fine to keep.
- **Deliverable repo** (user pre-creates empty, private): suggested name `adk-fpa-agent-blueprint`.

## 6. Non-negotiable content standards

- Include this blockquote verbatim (adjust only the bracketed domain phrase) in every blueprint README:
  > **Architectural Blueprint Notice:** This repository serves strictly as a sanitized, open-source structural blueprint demonstrating [system design, data architecture, and workflow automation]. All proprietary enterprise API integrations, sensitive webhooks, internal routing logic, and production access tokens have been completely omitted or mocked for security and compliance.
- Quantify impact wherever the source material supports it; frame numbers as "aggregated, portfolio-level modeled outcomes."
- Illustrative code must be honest: `NotImplementedError("Blueprint stub — proprietary transformation omitted")` for redacted internals; real, runnable shapes for configs.
- Before ANY repo goes public: produce a **confidentiality inventory** (every sensitive string found in the source → what replaced it) and get the user's explicit sign-off. Repos stay private until then.
- Run a final sweep before every push: `grep -rniE "fhnp|rubik|<real project ids>|claude|chatgpt|anthropic|gmail|password|secret|token|api[_-]?key"` — the only acceptable hits are the disclaimer's own wording and the LICENSE copyright line.

## 7. Design system (keep the portfolio visually coherent)

- Diagrams are **hand-generated SVG** (Python generator producing strict-XML-valid output — validate with `xml.etree.ElementTree.fromstring`; GitHub's SVG parser rejects invalid XML with a broken-image icon). Reference generators exist in the originating session's style; copy conventions from the SVGs on this branch.
- Palette: canvas `#f2f5ea`, edges `#d8dfcd`, card `#ffffff`, navy `#1b2733`, ink `#16232e`, body `#33413a`, muted `#5c6b60`, faint `#8a958b`, green `#2e5d43` (+bg `#eef2e4`), amber `#8a4a12` (+bg `#fbf7ec`), red `#a33a2a` (+bg `#fdf1ef`).
- Fonts: `IBM Plex Sans, -apple-system, Segoe UI, Helvetica, Arial, sans-serif`; mono: `IBM Plex Mono, ui-monospace, Menlo, monospace` (no quotes inside `font-family` attributes — quoting breaks GitHub's XML parsing).
- Card grammar: rounded 14px cards, 6px accent bar (left or top), title/subtitle/body lines, mono chips in tinted pills; labeled arrows; dashed amber for feedback loops; `letter-spacing:4` mono uppercase corner titles.
- Every SVG diagram gets its Mermaid diagram-as-code equivalent in a `<details>` block beneath it.
- If GitHub serves a stale/broken cached image after a fix, cache-bust the README reference (`?v=2`).

## 8. Hub updates after FHNP + ADK ship

In `technical_resume/README.md`: replace the two "*(blueprint in preparation)*" rows and the "In-Flight Blueprints" section with real links + one-line impact statements; extend the competency matrix if new evidence warrants. Assess `Semis-Analysis-Web`: if it has real substance, add an entry (sanitized if needed); if it's empty/stale, silently omit it.

## 9. Constraints learned the hard way (save yourself the retries)

- The GitHub App token **cannot create repositories** (`403 Resource not accessible by integration`) — the user must pre-create every new repo in the GitHub UI, and grant the Claude GitHub App access to it, BEFORE the session needs it.
- Mid-session `add_repo` may be broken on some sessions ("MCP tool call requires approval" loop) — select ALL needed repos at session creation.
- PyPI and apt installs may be blocked by network policy; a global Node Playwright + Chromium at `/opt/pw-browsers` is available for rendering/screenshot verification of SVGs.
- Git identity in the container defaults to an AI name — always commit with `-c user.name=daetan999 -c user.email=daetan999@gmail.com`.
