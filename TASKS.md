# Tasks

## Current Stage / Current Status

The Timesheet Analysis Tool is currently a deterministic web application with planned AI-assisted extraction, rule-based validation, human review, and Excel export.

Note: Future ML adoption should be considered after the initial build. The current project remains rule-based with planned AI-assisted extraction, but the system should be designed to preserve correction data and recurring usage patterns so it can become ML-ready later.

## Future Roadmap

### Future ML / Learning Layer Adoption

Status: Future roadmap item. Do not implement in the current stage.

The Timesheet Analysis Tool is currently not a custom ML model. The current system should remain a deterministic web application with planned AI-assisted extraction, rule-based validation, human review, and Excel export.

Future ML adoption should be considered after the initial build, especially because the tool is intended for recurring monthly use. Early design should make the system ML-ready by preserving extracted records, review corrections, validation outcomes, and recurring format patterns.

However, actual custom ML model training should only be implemented after enough labelled examples, monthly usage data, and user corrections have been collected to justify it.

Potential future ML / learning use cases:
- Improve file classification beyond filename and extension rules by detecting actual document layout and content.
- Improve extraction accuracy for repeated timesheet formats, worker names, site names, dates, clock-in times, clock-out times, break hours, overtime, and remarks.
- Detect anomalies such as missing clock-outs, duplicate entries, excessive hours, overlapping shifts, unusual overtime, and SOP mismatches.
- Learn from user corrections during the review stage to reduce repeated manual fixes.
- Build a correction-memory layer for recurring workers, site names, common OCR mistakes, and repeated formatting issues.
- Later consider a custom ML model or fine-tuned extraction model only if there are sufficient labelled examples and a clear accuracy or efficiency benefit.

Future implementation order:
1. Complete the initial deterministic build first.
2. Add real AI-assisted extraction only when ready.
3. Keep rule-based validation and human review mandatory.
4. After the initial build, start preserving user corrections, extracted records, validation flags, and recurring format patterns.
5. Use correction memory first before considering custom ML.
6. Evaluate whether custom ML is justified only after enough monthly data has accumulated.

Guardrails:
- Do not claim the project has a custom ML model unless one is actually trained on labelled project data.
- Do not build custom ML in the current stage.
- Do not replace deterministic validation rules with ML predictions.
- Do not remove human review from the workflow.
- Do not introduce model training dependencies until there is a dedicated ML implementation stage.
- Any future ML layer must be explainable, auditable, optional, and secondary to deterministic validation.

## Do Not Do Yet

- Do not build or train a custom ML model yet.
- Do not describe the current system as a custom ML model.
- Do not add ML training libraries or ML pipelines at this stage.
- Do not skip the human review layer even if AI extraction is added.
