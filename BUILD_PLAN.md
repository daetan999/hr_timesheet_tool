build plan

# Build Plan

## Stage 1A - App foundation

Build:
- FastAPI app
- Home page
- Month/year selection
- Navigation
- Static CSS
- Basic README

No AI yet.

## Stage 1B - Local config

Build:
- Worker masterlist page
- SOP code setup page
- Save data to local JSON files

## Stage 1C - Upload flow

Build:
- Upload page
- Accept JPG, JPEG, PNG, HEIC, PDF
- Save uploads locally
- Show uploaded file list

No AI yet.

## Stage 1D - Mock extraction and review

Build:
- Mock extracted timesheet data
- Review page
- Allow HR to edit extracted rows
- Allow HR to confirm unclear items

## Stage 1E - Excel export

Build:
- One worksheet per worker
- Date, Start Time, End Time, Hours Worked, Notes
- Total hours at bottom
- Notes summary at bottom
- Summary worksheet
- Basic formatting/highlighting

## Stage 1F - Real AI extraction

Build:
- OpenAI API integration
- Convert supported files to AI-readable input
- Extract JSON
- Validate JSON
- Feed results into review page

## Stage 1G - Review Chatbot Assistant

Build:
- Add a chatbot inside the Review Extraction page after guided review mode is stable.
- Help HR inspect and control the review queue through natural language.
- Use current reviewed_rows.json and SOP data as context.
- Support commands such as:
  - "Show Michelle's unresolved rows"
  - "Show all unclear time issues"
  - "Show all unknown SOP codes"
  - "Summarize remaining review items"
  - "Find rows where end time is missing"
  - "Show rows for 21 April"
- Require explicit confirmation before changing payroll/timesheet data.
- Show a confirmation summary before any data-changing action, for example:
  "I found 8 matching rows. Confirm applying this change?"
- Keep the chatbot secondary to the structured review queue.

Do not build yet:
- Do not replace guided review.
- Do not directly change payroll/timesheet data without confirmation.

## Stage 1G.2 - AI Second-Pass Review Suggestions

Goal:
- Use AI as a second checker for rows that require attention.

Rules:
1. AI second-pass should inspect unresolved review rows and suggest corrections.
   - Use the full preprocessed image as the visual source.
   - Do not use crop previews for AI second-pass unless a template-specific crop has been proven reliable across multiple days/cards.
2. Confidence thresholds:
   - below 65%: no auto-fill, keep manual review
   - 65% to 74%: show suggestion only
   - 75% to 89%: auto-fill suggested value, but keep row requiring HR confirmation
   - 90% and above: auto-fill and auto-confirm, but only with audit logging

3. For 90%+ auto-confirm:
   - set review_status = reviewed
   - set requires_attention = false
   - set hr_decision = ai_auto_confirmed
   - save ai_confidence
   - save ai_reason
   - save ai_suggested_fields
   - save original extracted fields before changes
   - allow Reopen for Review

4. Auto-confirmed rows must still appear in Reviewed tab.
5. Reviewed tab must clearly label them as:
   AI auto-confirmed
6. Do not silently hide auto-confirmed rows from audit/history.
7. Excel export can use the confirmed values, but reviewed_rows.json must retain the audit details.

Do not build yet:
- Do not build AI second-pass review yet.
- Do not call OpenAI for this stage until explicitly approved.
- Do not silently change payroll/timesheet data without audit logging.

## ML Sequencing and Future Learning Layer

Important sequencing:
- Before any ML/fine-tuning/pattern-learning stage begins, the rule-based workflow must be stable and usable.

Required before ML:
1. Complete and stabilize the current rule-based + GPT extraction workflow.
2. Guided review modal must be clean, usable, and reliable.
3. Review checklist/table must be stable.
4. SOP code handling must work reliably.
5. Hours Worked auto-calculation must work reliably.
6. AI second-pass review suggestions must be controlled with audit logging.
7. Physical time card crop/visual reference must be properly usable.

Crop/visual reference requirement:
- The current crop feature was disabled because inaccurate crop is worse than no crop.
- Current production behavior should use full image preview plus the in-app lightbox with zoom/pan.
- Keep crop disabled for HR review and AI second-pass until it is verified reliable.
- Keep crop as a future optional enhancement, not as a required dependency for the current review workflow.
- Before future ML adoption, build a reliable crop/visual reference system only if it can be proven accurate.
- Cropping should correctly show the relevant row/date for physical time cards.
- If precise cropping is not reliable, use a larger zoomable image viewer instead.
- Any crop used for HR review must not mislead the user to the wrong date/row.
- Crop calibration may need to be template-specific, e.g. ER-M physical card layout.
- Only enable crop after template-specific calibration is proven accurate across multiple days/cards.
- Cropping must remain a visual aid only and must not overwrite original/preprocessed images.
- Cropping must not affect HR review, AI second-pass, extraction values, or exports until verified.

Future ML adoption:
- Future ML adoption should be considered after the initial rule-based + GPT workflow is stable.
- ML should use HR-confirmed corrections as training/evaluation data.
- Store correction history clearly:
  - original AI extraction
  - AI confidence
  - AI suggestion
  - HR final correction
  - HR decision
  - source type
  - issue type
  - correction note
- ML should not automatically change payroll/timesheet data without controlled rules and audit logging.
- ML/fine-tuning should improve confidence and pattern recognition over time, especially for repeated handwriting/crop/layout issues.

Do not build yet:
- Do not build ML.
- Do not build fine-tuning or pattern-learning yet.
- Do not use ML to replace deterministic validation or HR review.

## Stage 1H - Handover readiness

Build:
- README for non-technical user
- .env.example
- Mac/Windows setup instructions
- Troubleshooting section
