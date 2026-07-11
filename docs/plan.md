# UI Redesign Plan — Visual Identity Pass

**Status:** Design plan only. No code has been written against this document yet.
**Scope:** Visual identity (palette, type, layout, one signature element) plus a short list of related UX gaps found while planning. This is a *design brief*, not a line-by-line implementation plan — see "How to implement this" at the end for the required next step before anyone writes CSS.
**Relationship to prior work:** This repo already went through one UI pass (`docs/superpowers/plans/2026-07-01-ui-simplification.md`, merged 2026-07-04/05) that removed clutter (sidebar, dead "Ask Assistant", a 3-card explainer block) using an **additive-only CSS strategy** — new rules appended, nothing in the legacy stylesheet edited or deleted, because that stylesheet has 2-14 duplicate copies of many selectors. That pass deliberately deferred a full cleanup of ~1,561 lines of now-dead CSS. **This redesign is a different kind of change** — a real visual identity, not a clutter trim — and will likely require actually rewriting `static/style.css` against verified screenshots as ground truth, which is exactly the deferred cleanup work. Whoever implements this should treat the CSS rewrite and the dead-CSS cleanup as the same job, not two.

---

## The design brief this plan follows

The following is the frontend-design guidance given for this pass, pasted exactly as provided, unedited:

---
name: frontend-design
description: Guidance for distinctive, intentional visual design when building new UI or reshaping an existing one. Helps with aesthetic direction, typography, and making choices that don't read as templated defaults.
license: Complete terms in LICENSE.txt
---

# Frontend Design

Approach this as the design lead at a small studio known for giving every client a visual identity that could not be mistaken for anyone else's. This client has already rejected proposals that felt templated, and is paying for a distinctive point of view: make deliberate, opinionated choices about palette, typography, and layout that are specific to this brief, and take one real aesthetic risk you can justify.

## Ground it in the subject

If the brief does not pin down what the product or subject is, pin it yourself before designing: name one concrete subject, its audience, and the page's single job, and state your choice. If there's any information in your memory about the human's preferences, context about what they're building, or designs you've made before – use that as a hint. The subject's own world, its materials, instruments, artifacts, and vernacular, is where distinctive choices come from. Build with the brief's real content and subject matter throughout.

## Design principles

For web designs, the hero is a thesis. Open with the most characteristic thing in the subject's world, in whatever form makes sense for it: a headline, an image, an animation, a live demo, an interactive moment. Be deliberate with your choice: a big number with a small label, supporting stats, and a gradient accent is the template answer, only use if that's truly the best option.

Typography carries the personality of the page. Pair the display and body faces deliberately, not the same families you would reach for on any other project, and set a clear type scale with intentional weights, widths, and spacing. Make the type treatment itself a memorable part of the design, not a neutral delivery vehicle for the content.

Structure is information. Structural devices, numbering, eyebrows, dividers, labels, should encode something true about the content, not decorate it. Many generic designs use numbered markers (01 / 02 / 03), but that's only appropriate if the content actually is a sequence - like a real process or a typed timeline where order carries information the reader needs. Question if choices like numbered markers actually make sense before incorporating them.

Leverage motion deliberately. Think about where and if animation can serve the subject: a page-load sequence, a scroll-triggered reveal, hover micro-interactions, ambient atmosphere. An orchestrated moment usually lands harder than scattered effects; choose what the direction calls for. However, sometimes less is more, and extra animation contributes to the feeling that the design is AI-generated.

Match complexity to the vision. Maximalist directions need elaborate execution; minimal directions need precision in spacing, type, and detail. Elegance is executing the chosen vision well.

Consider written content carefully. Often a design brief may not contain real content, and it's up to you to come up with copy. Copy can make a design feel as templated as the design itself. See the below section on writing for more guidance.

## Process: brainstorm, explore, plan, critique, build, critique again

For calibration: AI-generated design right now clusters around three looks: (1) a warm cream background (near #F4F1EA) with a high-contrast serif display and a terracotta accent; (2) a near-black background with a single bright acid-green or vermilion accent; (3) a broadsheet-style layout with hairline rules, zero border-radius, and dense newspaper-like columns. All three are legitimate for some briefs, but they are defaults rather than choices, and they appear regardless of subject. Where the brief pins down a visual direction, follow it exactly — the brief's own words always win, including when it asks for one of these looks. Where it leaves an axis free, don't spend that freedom on one of these defaults. Just like a human designer who's hired, there's often a careful balance between doing what you're good at and taking each project as a chance to experiment and learn.

Work in two passes. First, brainstorm a short design plan based on the human's design brief: create a compact token system with color, type, layout, and signature. Color: describe the palette as 4–6 named hex values. Type: the typefaces for 2+ roles (a characterful display face that's used with restraint, a complementary body face, and a utility face for captions or data if needed). Layout: a layout concept, using one-sentence prose descriptions and ASCII wireframes to ideate and compare. Signature: the single unique element this page will be remembered by that embodies the brief in an appropriate way.

Then review that plan against the brief before building: if any part of it reads like the generic default you would produce for any similar page (work through a similar prompt to see if you arrive somewhere similar) rather than a choice made for this specific brief — revise that part, say what you changed and why. Only after you've confirmed the relative uniqueness of your design plan should you start to write the code, following the revised plan exactly and deriving every color and type decision from it.

When writing the code, be careful of structuring your CSS selector specificities. It's easy to generate CSS classes that cancel each other out (especially with a type-based selector like .section and a element-based selector like .cta). This can happen often with paddings/margins between sections.

Try to do a lot of this planning and iteration in your thinking, and only show ideas to the user when you have higher confidence it'll delight them.

## Restraint and self-critique

Spend your boldness in one place. Let the signature element be the one memorable thing, keep everything around it quiet and disciplined, and cut any decoration that does not serve the brief. Not taking a risk can be a risk itself! Build to a quality floor without announcing it: responsive down to mobile, visible keyboard focus, reduced motion respected. Critique your own work as you build, taking screenshots if your environment supports it – a picture is worth 1000 tokens. Consider Chanel's advice: before leaving the house, take a look in the mirror and remove one accessory. Human creators have memory and always try to do something new, so if you have a space to quickly jot down notes about what you've tried, it can help you in future passes.

## More on writing in design

Words appear in a design for one reason: to make it easier to understand, and therefore easier to use. They are design material, not decoration. Bring the same intentionality to copy that you would bring to spacing and color. Before writing anything, ask what the design needs to say, and how it can best be said to help the person navigate the experience.

Write from the end user's side of the screen. Name things by what people control and recognize, never by how the system is built. A person manages notifications, not webhook config. Describe what something does in plain terms rather than selling it. Being specific is always better than being clever.

Use active voice as default. A control should say exactly what happens when it's used: "Save changes," not "Submit." An action keeps the same name through the whole flow, so the button that says "Publish" produces a toast that says "Published." The vocabulary of an interface is the signposting for someone navigating the product. Cohesion and consistency are how people learn their way around.

Treat failure and emptiness as moments for direction, not mood. Explain what went wrong and how to fix it, in the interface's voice rather than a person's. Errors don't apologize, and they are never vague about what happened. An empty screen is an invitation to act.

Keep the register conversational and tuned: plain verbs, sentence case, no filler, with tone matched to the brand and the audience. Let each element do exactly one job. A label labels, an example demonstrates, and nothing quietly does double duty.

---

## Step 1: Ground it in the subject

**Product:** Timesheet Analysis Tool — an internal HR utility, not a public product. It exists to turn a pile of physical time cards (photos, phone snapshots, PDF scans, occasional ad-hoc Excel sheets from supervisors) into one clean, correct Excel export per month.

**Audience:** A small internal HR team. Not developers, not power users — people who use this tool in short monthly bursts (upload → review → export), then don't touch it again for weeks. They are not learning a product, they are getting a job done between other HR duties.

**The page's single job, per page:**
- **Home** — resume this month's work, or start next month's, in one glance
- **Workers** — the master list of who gets paid; add/edit/remove a name
- **SOP Codes** — the master glossary of shorthand HR already uses on paper (OFF, EARLY OUT, LATE IN) so the AI extractor and the humans agree on what an abbreviation means
- **Upload** — get the raw time card files into the system
- **Review** — the real work: confirm or correct what the AI read off each time card, one row at a time
- **Export** — produce the Excel file that leaves this tool and enters payroll

**The subject's own world:** this tool's entire reason to exist is old-fashioned paper time cards and the HR ritual of reconciling them — punch clocks, stamped approvals, ruled ledger columns, a supervisor's handwriting next to a printed grid. That vernacular — not generic SaaS dashboard chrome — is where this identity should come from.

## Step 2: Design plan (first pass)

### Color — "Ledger" palette

| Name | Hex | Use |
|---|---|---|
| Ledger Paper | `#EDF3E7` | Page background — pale green-tinted, not cream |
| Bar Stripe | `#DCEAD3` | Alternating row/zone tint (the "green bar" of old dot-matrix payroll printouts) |
| Ink Navy | `#1E2C3A` | Primary text, headings |
| Graphite | `#51606A` | Secondary text, captions, labels |
| Stamp Red | `#B8402B` | The one urgent/attention accent — "needs review," destructive actions |
| Approved Green | `#2E6B3E` | Confirmed/reviewed state — deliberately not the same green as the paper tint |

Six named colors, one urgent accent, one "good" accent, everything else is ink-on-paper.

### Type — three roles

- **Display (headings):** a **slab serif** (e.g. Roboto Slab / Zilla Slab) — low-contrast, mechanical, typewriter-adjacent letterforms. Reads like a stamped ledger-book title, not a delicate editorial serif.
- **Body (labels, copy, buttons):** a humanist sans (e.g. IBM Plex Sans) — legible at a glance, no personality contest with the headings. IBM Plex is also a deliberate nod: IBM mainframes are literally where computerized payroll and time-and-attendance systems came from.
- **Utility/data (times, dates, SOP codes, row counts):** a monospace (e.g. IBM Plex Mono) with tabular figures — every column of numbers lines up vertically, which is what actually helps HR scan 15+ rows of start/end times quickly. This also echoes dot-matrix payroll printout output.

### Layout concept

Keep the validated **sectioned-zone structure** from the 2026-07 simplification pass (a light-tint status zone, a plain content zone, a clearly separated actions zone) — that structure tested well and isn't the problem. Re-skin it in the Ledger palette and add ledger-style hairline row dividers instead of the current card-shadow table.

```
┌─────────────────────────────────────────────────────────┐
│ Timesheet Analysis Tool                            Home │  <- ink navy on paper, no logo mark needed
├─────────────────────────────────────────────────────────┤
│ ① Month  ─  ② Workers  ─  ③ SOP Codes  ─  ④ Upload  ─   │  <- slab serif numerals, mono step labels
│    ⑤ Review  ─  ⑥ Export                                 │
├─────────────────────────────────────────────────────────┤
│ ▌TEST MODE — NO AI CHARGES▐   ·   3 ROWS NEED REVIEW     │  <- "stamped" status pill, see Signature below
│                                                           │
│  [ To Review (3) ] [ Reviewed (0) ] [ All (15) ]         │  <- bar-stripe tint zone
│                                                           │
│  [Run AI Second-Pass]  [Start Review]  [Export Excel]    │
├───────┬──────────┬───────────┬──────────────┬───────────┤
│STATUS │ WORKER   │ DATE      │ ISSUE TYPE   │  ACTION   │  <- mono column headers, hairline rules
│───────┼──────────┼───────────┼──────────────┼───────────│     between every row (ledger rule lines)
│ ▌□    │ Xiaomin  │ 01 Apr 26 │ Unknown code │ [Review]  │
│ ▌□    │ Xiaomin  │ 02 Apr 26 │ Unclear time │ [Review]  │
└───────┴──────────┴───────────┴──────────────┴───────────┘
```

### Signature — the one real risk

**Rubber-stamp status indicators.** Every status pill and badge ("NEEDS REVIEW," "REVIEWED," "TEST MODE," "OFF," a worker's "In Progress" tag) renders as if it were physically stamped onto the page: uppercase, letter-spaced monospace text inside a thin stamp-outline border, sitting at a slight −1.5° to 1.5° rotation, with a faint ink-bleed shadow (soft, low-opacity, offset 1px) instead of a normal drop shadow. This is the single place the design takes a visible risk — everywhere else (spacing, buttons, forms) stays quiet and disciplined, per the brief's "spend your boldness in one place."

This is not decoration: a stamp is literally what happens to a real, physical timesheet when HR signs off on it. The signature element **is** the subject.

## Step 3: Self-critique against the brief's own calibration warning

The brief calls out three AI-design defaults by name and says to avoid spending creative freedom on them where the brief leaves the axis open. Checking this plan against each:

1. **"Warm cream background (~#F4F1EA) + high-contrast serif display + terracotta accent."** This was the first direction I drafted, and it is uncomfortably close to this exact trap — cream paper, serif headings, a warm red-orange accent. **Revised:** the background moved from cream to a **green**-tinted "ledger paper" (`#EDF3E7`, not `#F4F1EA` — a different hue family, not just a different shade of the same one), and the heading face moved from a high-contrast serif (thin/thick modulation, like Playfair) to a **slab serif** (uniform stroke weight, mechanical) — a different genus of letterform entirely. The accent color is used in exactly one place (stamp pills for urgency/status), not as a general link/CTA color the way the flagged default uses terracotta everywhere. The justification for green + slab-serif + IBM Plex isn't "it looks nice" — it's "dot-matrix payroll printouts used green-bar paper, and IBM literally built the first computerized payroll/timekeeping systems," which is a reason this brief specifically supports and a different one wouldn't.
2. **"Near-black background, one bright accent."** Not used — an HR tool used in short work sessions by non-technical staff should not ask anyone to read a dark-mode dashboard by default. Rejected for audience fit, not just to dodge the pattern.
3. **"Broadsheet hairline rules, zero border-radius, dense newspaper columns."** Partially present (hairline row rules) because ledger books *are* ruled — but the layout is the already-validated sectioned-zone system, not dense multi-column news typography, and corners stay softly rounded (stamps and ledger cards, not newsprint). Kept the one element that's genuinely on-subject, left the rest of the pattern out.

## Step 4: Accessibility and quality floor (non-negotiable, not a "nice to have")

- Verify Ink Navy (`#1E2C3A`) on Ledger Paper (`#EDF3E7`) and Graphite (`#51606A`) on the same background both meet WCAG AA contrast (4.5:1 body text) before finalizing — check with a real contrast tool during implementation, don't eyeball it.
- Visible keyboard focus states on every interactive element (buttons, tabs, table row actions) — the current stylesheet's focus handling should be audited, not assumed adequate.
- Respect `prefers-reduced-motion` for the stamp rotation/ink-bleed effect if it's animated on state change (e.g. a row transitioning from "needs review" to "reviewed") — the stamp can appear instantly for users who've asked for reduced motion, no spring/settle animation forced on them.
- Responsive down to a single-column mobile layout — HR staff may well pull this up on a phone to sanity-check a row.
- Tabular figures (`font-variant-numeric: tabular-nums` or the monospace utility face) specifically for anything in a table column of numbers/times — this is a real usability requirement for this subject, not a style flourish.

## Step 5: Copy pass (per the brief's writing guidance)

A few concrete spots where current copy doesn't yet follow the brief's writing rules — worth fixing in the same pass as the visual redesign, since both touch the same templates:

- **Empty states are currently generic** ("No workers saved yet.", "No rows in this view.") — per "an empty screen is an invitation to act," these should tell HR what to do next, e.g. "No workers yet — add the first name above to get started." rather than just stating absence.
- **Action naming consistency** — audit that a button's label matches the toast/message that follows it (e.g. if a button says "Save changes," the confirmation shouldn't say "Submitted successfully"). Do this check page-by-page during implementation.
- **Error copy** — should explain what went wrong and how to fix it in the interface's voice, not apologize or go vague. Example already done correctly: the SOP code length validation ("SOP code must be 20 characters or less. Use a short code like AL, MC, or OFF.") — use this message as the house style template for every other validation error in the app.

## Related gaps found while planning (separate from the visual pass — flagging so nothing gets lost)

These came up in conversation while scoping this redesign. They are **not** pure CSS/copy changes — they need real backend work — so they should be scoped and built as their own small feature, not folded silently into the visual redesign PR:

1. **No way to delete a monthly session.** There is currently no delete route at all (`app.py` / `services/session_store.py` — confirmed no delete endpoint exists). Needed: a `POST /sessions/{session_id}/delete` (or archive) route, a confirmation step (this is destructive, irreplaceable HR data), and a decision on hard-delete-the-files vs. soft-delete/archive-and-hide. Recommendation: soft-delete first (hide from the Home lists, keep files on disk) given the data is irreplaceable — a hard delete can be a later fast-follow once trust is established.
2. **No visibility into the Workers / SOP Codes master lists from Home.** HR currently can only see these lists mid-session, buried inside the step wizard for one particular month. Good news: session-independent routes already exist (`GET /workers`, `GET /sop-codes` in `app.py`) — this is purely a missing link from Home, not new backend work. Add two links/buttons on Home: "View & edit workers" → `/workers`, "View & edit SOP codes" → `/sop-codes`.
3. **Starting a month that's already in progress does not duplicate it** — confirmed via `services/session_store.py: ensure_session()`, which keys sessions by `YYYY-MM` and returns the existing session if one already exists for that month. No action needed here; documented so nobody "fixes" a non-bug.

Item 2 is trivial and could genuinely ride along in the same visual-redesign PR (it's two links). Item 1 needs its own brainstorm → spec → plan cycle before any code is written, because of the destructive-data decision it requires.

## How to implement this

This document is a **design brief and token system**, not a step-by-step build plan. Per this repo's established workflow (see `docs/superpowers/plans/2026-07-01-ui-simplification.md` for the pattern), the next steps before writing any CSS are:

1. Run this plan through the **brainstorming** process against the actual current templates and screenshots — validate the token system and wireframes against real content (the real `sessions/2026-04` fixture data), not the abstract sketch above.
2. Produce a proper **design spec** (`docs/superpowers/specs/YYYY-MM-DD-ui-redesign-design.md`) once the direction above is confirmed or adjusted by the project owner.
3. Produce an **implementation plan** (`docs/superpowers/plans/YYYY-MM-DD-ui-redesign.md`) with exact file/line targets, given this is a full visual identity change and will likely require rewriting rather than appending to `static/style.css` — unlike the additive-only June pass, this one should re-author the stylesheet cleanly against verified screenshots, folding in the already-flagged dead-CSS cleanup (~1,561 lines) as part of the same effort rather than a separate one.
4. Execute via the same subagent-driven-development flow used for the June pass (fresh implementer per task, task review, final whole-branch review) — this is a larger, higher-risk change than a clutter trim, so the same quality gates apply, not fewer.
