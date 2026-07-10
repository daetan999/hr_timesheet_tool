import os
import base64
import json
import re
import time
import calendar
from datetime import date
from pathlib import Path
from uuid import uuid4

from services.file_processor import (
    get_preprocessing_manifest_by_upload,
    get_source_type_label,
    list_uploaded_files,
)
from services.session_store import SessionNotFoundError, load_session


IMAGE_PREVIEW_EXTENSIONS = {".jpg", ".jpeg", ".png", ".heic"}
PDF_EXTENSION = ".pdf"
SUPPORTED_EXTRACTION_MODES = {"mock", "real_openai"}
DEFAULT_EXTRACTION_MODE = "mock"
DEFAULT_OPENAI_MODEL = "gpt-5.5"
ALLOWED_REVIEW_REASONS = {
    "month_mismatch",
    "unclear_worker_name",
    "unknown_code",
    "unclear_time",
    "inferred_from_overlap",
    "overwritten_or_cancelled",
    "multiple_time_segments",
    "possible_split_shift",
    "blank_day",
    "handwritten_note_unclear",
    "date_mapping_unclear",
    "strange_hours",
    "irrelevant_file",
}
PLACEHOLDER_VALUES = {"hh:mm", "unknown", "n/a", "na", "-", "--", "tbd", "none", "null"}
EXTRACTION_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "detected_worker_name",
        "suggested_worker_match",
        "source_type",
        "card_number",
        "month_seen",
        "document_month",
        "document_year",
        "document_month_confidence",
        "month_mismatch",
        "document_issue",
        "document_issue_message",
        "entries",
    ],
    "properties": {
        "detected_worker_name": {"type": "string"},
        "suggested_worker_match": {"type": "string"},
        "source_type": {
            "type": "string",
            "enum": [
                "physical_time_card",
                "multi_worker_attendance_table",
                "pdf_or_excel_style",
                "unknown",
            ],
        },
        "card_number": {"type": "string"},
        "month_seen": {"type": "string"},
        "document_month": {"type": "string"},
        "document_year": {"type": "string"},
        "document_month_confidence": {
            "type": "string",
            "enum": ["high", "medium", "low", "unknown"],
        },
        "month_mismatch": {"type": "boolean"},
        "document_issue": {"type": "string"},
        "document_issue_message": {"type": "string"},
        "entries": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "day",
                    "worker",
                    "date",
                    "start_time",
                    "end_time",
                    "hours_worked",
                    "extracted_code",
                    "notes",
                    "requires_review",
                    "review_reason",
                ],
                "properties": {
                    "day": {"type": "string"},
                    "worker": {"type": "string"},
                    "date": {"type": "string"},
                    "start_time": {"type": "string"},
                    "end_time": {"type": "string"},
                    "hours_worked": {"type": "string"},
                    "extracted_code": {"type": "string"},
                    "notes": {"type": "string"},
                    "requires_review": {"type": "boolean"},
                    "review_reason": {"type": "string"},
                },
            },
        },
    },
}
SECOND_PASS_RECHECK_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "row_id",
        "suggested_start_time",
        "suggested_end_time",
        "suggested_hours_worked",
        "suggested_notes",
        "confidence",
        "recommendation",
        "reason",
        "needs_human_confirmation",
        "fields_to_update",
    ],
    "properties": {
        "row_id": {"type": "string"},
        "suggested_start_time": {"type": "string"},
        "suggested_end_time": {"type": "string"},
        "suggested_hours_worked": {"type": "string"},
        "suggested_notes": {"type": "string"},
        "confidence": {"type": "number"},
        "recommendation": {
            "type": "string",
            "enum": ["no_suggestion", "suggest_only", "auto_fill", "auto_confirm"],
        },
        "reason": {"type": "string"},
        "needs_human_confirmation": {"type": "boolean"},
        "fields_to_update": {
            "type": "object",
            "additionalProperties": False,
            "required": ["start_time", "end_time", "hours_worked", "notes"],
            "properties": {
                "start_time": {"type": "string"},
                "end_time": {"type": "string"},
                "hours_worked": {"type": "string"},
                "notes": {"type": "string"},
            },
        },
    },
}


def get_extraction_status() -> dict[str, str | bool]:
    requested_mode = os.getenv("AI_EXTRACTION_MODE", DEFAULT_EXTRACTION_MODE).strip().lower()
    api_key_present = bool(os.getenv("OPENAI_API_KEY", "").strip())
    model = get_openai_model()
    warning = ""

    if requested_mode not in SUPPORTED_EXTRACTION_MODES:
        warning = "Unknown extraction mode. Running in mock mode."
        requested_mode = DEFAULT_EXTRACTION_MODE

    active_mode = requested_mode
    if requested_mode == "real_openai":
        if not api_key_present:
            active_mode = DEFAULT_EXTRACTION_MODE
            warning = "OpenAI API key is missing. Running in mock mode."
        else:
            active_mode = "real_openai"
    elif not api_key_present:
        warning = "OpenAI not connected yet. Running in mock mode."

    return {
        "requested_mode": requested_mode,
        "active_mode": active_mode,
        "active_mode_label": "Mock" if active_mode == "mock" else "Real OpenAI",
        "api_key_present": api_key_present,
        "openai_enabled": active_mode == "real_openai",
        "model": model,
        "warning": warning,
    }


def get_openai_model() -> str:
    return os.getenv("OPENAI_MODEL", DEFAULT_OPENAI_MODEL).strip() or DEFAULT_OPENAI_MODEL


def build_live_extraction_options(session_id: str | None) -> list[dict[str, str]]:
    if not session_id:
        return []

    options = []
    for entry in get_preprocessing_manifest_by_upload(session_id).values():
        if entry.get("status") != "success":
            continue

        original_filename = str(entry.get("original_filename") or "")
        source_type = str(entry.get("source_type") or "unknown")
        source_type_label = str(
            entry.get("source_type_label")
            or get_source_type_label(source_type)
        )
        preprocessed_files = entry.get("preprocessed_files", [])
        if not isinstance(preprocessed_files, list):
            continue

        for preprocessed_file in preprocessed_files:
            if not isinstance(preprocessed_file, dict):
                continue

            path = str(preprocessed_file.get("path") or "")
            filename = str(preprocessed_file.get("filename") or Path(path).name)
            if not path or not filename:
                continue

            label = f"{original_filename} -> {filename}"
            options.append(
                {
                    "value": path,
                    "label": label,
                    "filename": filename,
                    "original_filename": original_filename,
                    "stored_filename": str(entry.get("stored_filename") or ""),
                    "source_path": str(entry.get("source_path") or ""),
                    "source_type": source_type,
                    "source_type_label": source_type_label,
                    "session_relative_path": str(
                        preprocessed_file.get("session_relative_path") or ""
                    ),
                    "page_number": str(preprocessed_file.get("page_number") or ""),
                }
            )

    return sorted(options, key=lambda item: item["label"])


def find_live_extraction_option(
    session_id: str,
    selected_preprocessed_path: str,
) -> dict[str, str] | None:
    return next(
        (
            option
            for option in build_live_extraction_options(session_id)
            if option["value"] == selected_preprocessed_path
        ),
        None,
    )


def build_live_extraction_prompt(
    *,
    session: dict[str, str | int],
    workers: list[dict[str, str]],
    sop_codes: list[dict[str, str]],
    selected_file: dict[str, str],
) -> str:
    worker_names = [str(worker.get("name", "")).strip() for worker in workers]
    worker_names = [name for name in worker_names if name]
    sop_code_text = ", ".join(
        f"{item.get('code', '')}={item.get('meaning', '')}"
        for item in sop_codes
        if item.get("code")
    )
    month = int(session["month"])
    year = int(session["year"])
    session_month_label = calendar.month_name[month]

    source_type = selected_file.get("source_type", "unknown")
    common_rules = f"""
You are extracting timesheet data for HR review.

Source of truth:
- Selected payroll month: {session_month_label} {year}
- Worker masterlist: {", ".join(worker_names) if worker_names else "No workers configured"}
- Known SOP codes: {sop_code_text if sop_code_text else "No SOP codes configured"}
- Original file: {selected_file["original_filename"]}
- Preprocessed file: {selected_file["filename"]}
- Pre-classified source type: {source_type}

Global rules:
- Return only data that is visible in the image.
- First detect whether the document visibly states a month and year, such as "APRIL 2026 ATTENDANCE".
- If the document visibly states a month/year that conflicts with the selected payroll month, set month_mismatch=true, document_issue="month_mismatch", and document_issue_message="Document appears to be [visible month year] but session is {session_month_label} {year}."
- If month_mismatch=true, return only one high-level review entry. Do not return daily rows.
- Use the selected payroll month/year only when the document month/year is missing, unclear, or matches the selected payroll month/year.
- Do not guess unclear handwriting, worker names, times, notes, or crossed-out values.
- If a field is unclear, leave the field blank when appropriate and set requires_review=true.
- Unknown SOP codes must be flagged for HR review.
- If the image is irrelevant or not a timesheet, return source_type="unknown" and create one entry with requires_review=true and review_reason="irrelevant_file".
- For hours_worked, use the format "9h 35m" when start and end times are clear. Leave blank if unclear.
- Use 24-hour HH:MM for start_time and end_time when clear.
- Never output placeholder values such as "HH:MM", "unknown", "N/A", "-", or "TBD". Use an empty string and requires_review=true instead.
- Use review_reason only from this set when possible: month_mismatch, unclear_worker_name, unknown_code, unclear_time, inferred_from_overlap, overwritten_or_cancelled, multiple_time_segments, possible_split_shift, blank_day, handwritten_note_unclear, date_mapping_unclear, strange_hours, irrelevant_file.
- Put the visible code or short note code in extracted_code when there is one. Put the full visible note text in notes.
""".strip()

    multi_worker_rules = """
Source-type instructions for multi_worker_attendance_table:
- Treat the table column headers as worker names.
- Each entry.worker must contain exactly one worker name from one column header.
- Never combine multiple worker names in one entry. Do not output values like "MICHELE; MINDY; THING; TINA".
- If multiple workers have entries on the same day, return separate entries, one per worker.
- Return one row per worker per date/note that is visible.
- Preserve actual visible note text exactly where practical, including OFF, OFF 加休, OL 拿假, LATE IN 迟到, EARLY OUT 早回, MC, and CC LEAVE 育儿假.
- If the note/code is not in the known SOP codes list, set requires_review=true and review_reason="unknown_code".
- Do not infer start/end times for attendance-table note cells unless times are explicitly visible.
""".strip()

    physical_card_rules = """
Source-type instructions for physical_time_card:
- Detect the worker name at the top of the card. Use one worker only.
- Detect visible month/year if available.
- Detect the card number if visible.
- If card_number is "1", rows likely map to days 1 through 15 of the selected/document month.
- If card_number is "2", rows likely map to days 16 through 31 of the selected/document month.
- If card number is missing, unclear, overwritten, or row-to-date mapping is not confident, leave uncertain dates blank or mark requires_review=true with review_reason="date_mapping_unclear".
- Extract start_time and end_time per visible day when clear.
- Preserve handwritten notes, corrections, OFF/leave codes, and remarks in notes.
- If time values are overwritten, cancelled, crossed out, or unclear, leave unclear fields blank and set requires_review=true with review_reason="overwritten_or_cancelled" or "unclear_time".
- Some physical cards have stamped times that overlap between adjacent day rows. Estimate confidence from visual row placement, stamp alignment, neighboring blank fields, and whether the adjacent day already has the complementary start/end time.
- If overlap inference confidence is >= 0.65, fill the inferred start_time or end_time, set requires_review=true, set review_reason="inferred_from_overlap", and explain the inference briefly in notes.
- Example: if a time appears between day 21 and day 22, and day 22 has an end time but no start time, you may infer the lower/visually aligned stamp belongs to day 22 when confidence is >= 0.65.
- Do not silently accept inferred overlapping stamps as clean rows.
- If overlap inference confidence is < 0.65, leave the field blank and set requires_review=true with review_reason="unclear_time".
- Do not invent missing clock-in or clock-out times.
""".strip()

    fallback_rules = """
Source-type instructions for unknown or unclear source:
- If this is not a timesheet or attendance document, return source_type="unknown" and one entry with requires_review=true and review_reason="irrelevant_file".
- If the document type is unclear but appears related to attendance, extract only clearly visible fields and flag uncertainty for HR review.
""".strip()

    if source_type == "multi_worker_attendance_table":
        source_rules = multi_worker_rules
    elif source_type == "physical_time_card":
        source_rules = physical_card_rules
    else:
        source_rules = fallback_rules

    return f"{common_rules}\n\n{source_rules}"


def _openai_call_with_retry(fn, *, max_attempts: int = 3):
    """Call fn() with exponential backoff on transient OpenAI errors.

    Retries on APIConnectionError, RateLimitError, and 5xx APIStatusError.
    Raises immediately on 4xx errors (auth, bad request, etc.).
    RateLimitError must be caught before APIStatusError because it is a subclass.
    """
    import openai as _openai

    delays = [1, 2, 4]
    last_exc: Exception | None = None
    for attempt in range(max_attempts):
        try:
            return fn()
        except _openai.RateLimitError as exc:
            last_exc = exc
        except _openai.APIConnectionError as exc:
            last_exc = exc
        except _openai.APIStatusError as exc:
            if exc.status_code >= 500:
                last_exc = exc
            else:
                raise  # 4xx — do not retry
        if attempt + 1 < max_attempts:
            time.sleep(delays[attempt])
    raise last_exc  # type: ignore[misc]


def image_path_to_data_url(path: Path) -> str:
    image_bytes = path.read_bytes()
    return f"data:image/jpeg;base64,{base64.b64encode(image_bytes).decode('ascii')}"


def call_live_openai_extraction(
    *,
    session: dict[str, str | int],
    workers: list[dict[str, str]],
    sop_codes: list[dict[str, str]],
    selected_file: dict[str, str],
) -> dict[str, object]:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise ValueError("OpenAI API key is missing. Add OPENAI_API_KEY to .env.")

    image_path = Path(selected_file["value"])
    if not image_path.exists():
        raise ValueError("Selected preprocessed file was not found.")

    try:
        from openai import OpenAI
    except ImportError as exc:
        raise ValueError("OpenAI package is not installed. Run pip install -r requirements.txt.") from exc

    client = OpenAI(api_key=api_key)

    def _do_extraction_call():
        return client.responses.create(
            model=get_openai_model(),
            input=[
                {
                    "role": "developer",
                    "content": build_live_extraction_prompt(
                        session=session,
                        workers=workers,
                        sop_codes=sop_codes,
                        selected_file=selected_file,
                    ),
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": "Extract this selected preprocessed timesheet image into the required JSON schema.",
                        },
                        {
                            "type": "input_image",
                            "image_url": image_path_to_data_url(image_path),
                            "detail": "high",
                        },
                    ],
                },
            ],
            text={
                "format": {
                    "type": "json_schema",
                    "name": "timesheet_extraction",
                    "strict": True,
                    "schema": EXTRACTION_SCHEMA,
                }
            },
        )

    response = _openai_call_with_retry(_do_extraction_call)

    output_text = response.output_text
    try:
        result = json.loads(output_text)
    except json.JSONDecodeError as exc:
        return {"error": True, "error_message": f"OpenAI returned invalid JSON: {exc}"}

    if not isinstance(result, dict):
        return {"error": True, "error_message": "OpenAI returned an invalid extraction structure."}

    return result


def normalize_second_pass_confidence(value: object) -> float:
    try:
        confidence = float(value)
    except (TypeError, ValueError):
        return 0.0
    if confidence > 1:
        confidence = confidence / 100
    return max(0.0, min(confidence, 1.0))


def _get_auto_confirm_threshold() -> float:
    """Return the auto_confirm confidence threshold.

    Priority:
    1. AUTO_CONFIRM_THRESHOLD env var (float, clamped to [0.76, 0.99])
    2. Auto-selected based on OPENAI_MODEL:
       - gpt-5.4-nano  → 0.97
       - gpt-5.4       → 0.93
       - gpt-5.5 / unknown premium / anything else → 0.90
    """
    model = os.getenv("OPENAI_MODEL", DEFAULT_OPENAI_MODEL).strip().lower()
    if model == "gpt-5.4-nano":
        auto_threshold = 0.97
    elif model == "gpt-5.4":
        auto_threshold = 0.93
    else:
        auto_threshold = 0.90

    raw = os.getenv("AUTO_CONFIRM_THRESHOLD")
    if raw is not None:
        try:
            threshold = float(raw)
        except (ValueError, TypeError):
            threshold = auto_threshold
    else:
        threshold = auto_threshold

    return max(0.76, min(threshold, 0.99))


def second_pass_recommendation_for_confidence(confidence: float) -> str:
    if confidence < 0.65:
        return "no_suggestion"
    if confidence < 0.75:
        return "suggest_only"
    if confidence < _get_auto_confirm_threshold():
        return "auto_fill"
    return "auto_confirm"


def build_second_pass_prompt(
    *,
    session: dict[str, str | int],
    row: dict[str, object],
    sop_codes: list[dict[str, str]],
    card_number: str,
) -> str:
    month = int(session["month"])
    year = int(session["year"])
    session_month_label = calendar.month_name[month]
    sop_code_text = ", ".join(
        f"{item.get('code', '')}={item.get('meaning', '')}"
        for item in sop_codes
        if item.get("code")
    )

    return f"""
You are a second-pass checker for one timesheet review row.

Use the full preprocessed image. Do not assume a crop is available.
Focus on the target worker/date/day described below, but inspect adjacent rows if stamped times overlap.
If uncertain, say so and do not invent values.
Return structured JSON only.

Session:
- Payroll month/year: {session_month_label} {year}
- Known SOP codes: {sop_code_text if sop_code_text else "No SOP codes configured"}

Target row:
- row_id: {row.get("row_id", "")}
- worker: {row.get("worker", "")}
- date: {row.get("date", "")}
- source_type: {row.get("source_type", "")}
- card_number: {card_number}
- current start_time: {row.get("start_time", "")}
- current end_time: {row.get("end_time", "")}
- current hours_worked: {row.get("hours_worked", "")}
- notes: {row.get("notes", "")}
- review_reason: {row.get("review_reason", "")}

Rules:
- Inspect the full image and focus on the target worker/date/day.
- For physical time cards, check neighboring rows when stamps overlap between days.
- Do not use crop assumptions.
- Do not guess unreadable handwriting.
- Use 24-hour H:MM or HH:MM times only when visible or strongly supported.
- For confidence below 0.65, return no_suggestion and leave fields_to_update blank.
- For confidence 0.65 to 0.74, return suggest_only.
- For confidence 0.75 to 0.89, return auto_fill.
- For confidence 0.90 and above, return auto_confirm only if the evidence is very clear.
- Explain the visual evidence in reason.
- If no field should change, keep fields_to_update values as empty strings.
""".strip()


def call_second_pass_openai_recheck(
    *,
    session: dict[str, str | int],
    row: dict[str, object],
    sop_codes: list[dict[str, str]],
    image_path: Path,
    card_number: str = "",
) -> dict[str, object]:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise ValueError("OpenAI API key is missing. Add OPENAI_API_KEY to .env.")
    if not image_path.exists():
        raise ValueError("Preprocessed image was not found.")

    try:
        from openai import OpenAI
    except ImportError as exc:
        raise ValueError("OpenAI package is not installed. Run pip install -r requirements.txt.") from exc

    client = OpenAI(api_key=api_key)
    _row_id = str(row.get("row_id") or "")

    def _do_second_pass_call():
        return client.responses.create(
            model=get_openai_model(),
            input=[
                {
                    "role": "developer",
                    "content": build_second_pass_prompt(
                        session=session,
                        row=row,
                        sop_codes=sop_codes,
                        card_number=card_number,
                    ),
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": "Recheck only this one review row using the full preprocessed image.",
                        },
                        {
                            "type": "input_image",
                            "image_url": image_path_to_data_url(image_path),
                            "detail": "high",
                        },
                    ],
                },
            ],
            text={
                "format": {
                    "type": "json_schema",
                    "name": "timesheet_second_pass_recheck",
                    "strict": True,
                    "schema": SECOND_PASS_RECHECK_SCHEMA,
                }
            },
        )

    response = _openai_call_with_retry(_do_second_pass_call)

    try:
        result = json.loads(response.output_text)
    except json.JSONDecodeError as exc:
        return {"error": True, "error_message": f"OpenAI returned invalid JSON: {exc}", "row_id": _row_id}

    if not isinstance(result, dict):
        return {"error": True, "error_message": "OpenAI returned an invalid second-pass structure.", "row_id": _row_id}

    confidence = normalize_second_pass_confidence(result.get("confidence"))
    enforced_recommendation = second_pass_recommendation_for_confidence(confidence)
    fields_to_update = result.get("fields_to_update")
    if not isinstance(fields_to_update, dict):
        return {"error": True, "error_message": "OpenAI returned invalid fields_to_update.", "row_id": _row_id}

    normalized_fields = {
        "start_time": clean_extracted_value(fields_to_update.get("start_time")),
        "end_time": clean_extracted_value(fields_to_update.get("end_time")),
        "hours_worked": clean_extracted_value(fields_to_update.get("hours_worked")),
        "notes": clean_extracted_value(fields_to_update.get("notes")),
    }
    if enforced_recommendation == "no_suggestion":
        normalized_fields = {"start_time": "", "end_time": "", "hours_worked": "", "notes": ""}
    elif not any(normalized_fields.values()):
        enforced_recommendation = "no_suggestion"

    return {
        "row_id": str(result.get("row_id") or row.get("row_id") or ""),
        "suggested_start_time": clean_extracted_value(result.get("suggested_start_time")),
        "suggested_end_time": clean_extracted_value(result.get("suggested_end_time")),
        "suggested_hours_worked": clean_extracted_value(result.get("suggested_hours_worked")),
        "suggested_notes": clean_extracted_value(result.get("suggested_notes")),
        "confidence": confidence,
        "recommendation": enforced_recommendation,
        "model_recommendation": str(result.get("recommendation") or ""),
        "reason": str(result.get("reason") or "").strip(),
        "needs_human_confirmation": enforced_recommendation != "auto_confirm",
        "fields_to_update": normalized_fields,
    }


def parse_month_year(value: str) -> tuple[int | None, int | None]:
    normalized = value.strip()
    if not normalized:
        return None, None

    month_lookup = {name.lower(): index for index, name in enumerate(calendar.month_name) if name}
    month_lookup.update(
        {name.lower(): index for index, name in enumerate(calendar.month_abbr) if name}
    )
    lower_value = normalized.lower()
    month = None
    year = None

    for month_name, month_number in month_lookup.items():
        if re.search(rf"\b{re.escape(month_name)}\b", lower_value):
            month = month_number
            break

    year_match = re.search(r"\b(20\d{2})\b", normalized)
    if year_match:
        year = int(year_match.group(1))

    numeric_match = re.search(r"\b(20\d{2})[-/](0?[1-9]|1[0-2])\b", normalized)
    if numeric_match:
        year = int(numeric_match.group(1))
        month = int(numeric_match.group(2))

    return month, year


def document_month_matches_session(
    extraction: dict[str, object],
    session: dict[str, str | int],
) -> bool:
    document_month = str(extraction.get("document_month") or extraction.get("month_seen") or "")
    document_year = str(extraction.get("document_year") or "")
    month, year = parse_month_year(f"{document_month} {document_year}")
    if month is None or year is None:
        return True

    return month == int(session["month"]) and year == int(session["year"])


def build_month_mismatch_row(
    extraction: dict[str, object],
    selected_file: dict[str, str],
    session: dict[str, str | int],
) -> dict[str, str | bool]:
    session_month_label = calendar.month_name[int(session["month"])]
    visible_month = str(extraction.get("document_month") or extraction.get("month_seen") or "").strip()
    visible_year = str(extraction.get("document_year") or "").strip()
    visible_label = " ".join(part for part in [visible_month, visible_year] if part)
    message = str(extraction.get("document_issue_message") or "").strip()
    if not message:
        if visible_label:
            message = (
                f"Document appears to be {visible_label} but session is "
                f"{session_month_label} {session['year']}."
            )
        else:
            message = (
                f"Document month/year conflicts with session {session_month_label} "
                f"{session['year']}."
            )

    return {
        "row_id": f"live-{uuid4().hex}",
        "extraction_mode": "real_openai",
        "worker": "",
        "date": "",
        "start_time": "",
        "end_time": "",
        "hours_worked": "",
        "notes": message,
        "requires_attention": True,
        "review_reason": "month_mismatch",
        "source_original_filename": selected_file["original_filename"],
        "source_stored_filename": selected_file["stored_filename"],
        "source_path": selected_file["source_path"],
        "source_kind": "image",
        "source_can_preview": True,
        "source_type": str(extraction.get("source_type") or selected_file["source_type"] or "unknown"),
        "source_type_label": get_source_type_label(
            str(extraction.get("source_type") or selected_file["source_type"] or "unknown")
        ),
        "preprocessing_status": "success",
        "preprocessing_error": "",
        "preprocessed_filename": selected_file["filename"],
        "preprocessed_path": selected_file["value"],
        "preprocessed_session_path": selected_file["session_relative_path"],
        "preprocessed_file_count": "1",
    }


def worker_value_is_combined(worker: str) -> bool:
    if not worker.strip():
        return False
    separators = [";", "/", "\\", "&", " and ", "、", ","]
    return any(separator in worker for separator in separators)


def note_matches_known_sop(note: str, known_sop_codes: set[str]) -> bool:
    normalized_note = note.strip().casefold()
    if not normalized_note:
        return True
    return normalized_note in known_sop_codes


def clean_extracted_value(value: object) -> str:
    text = str(value or "").strip()
    if text.casefold() in PLACEHOLDER_VALUES:
        return ""
    return text


def normalize_review_reason(reason: str) -> str:
    normalized = reason.strip().casefold().replace("-", "_").replace(" ", "_")
    aliases = {
        "cancelled_or_overwritten": "overwritten_or_cancelled",
        "overwritten": "overwritten_or_cancelled",
        "cancelled": "overwritten_or_cancelled",
        "unclear": "unclear_time",
        "unknown_sop": "unknown_code",
    }
    normalized = aliases.get(normalized, normalized)
    if normalized in ALLOWED_REVIEW_REASONS:
        return normalized
    return normalized if not normalized else "handwritten_note_unclear"


def day_matches_card_number(day: str, card_number: str) -> bool:
    try:
        day_number = int(day)
    except ValueError:
        return True

    if card_number == "1":
        return 1 <= day_number <= 15
    if card_number == "2":
        return 16 <= day_number <= 31
    return True


def date_day_matches_entry_day(date_value: str, day: str) -> bool:
    if not date_value or not day:
        return True
    try:
        day_number = int(day)
    except ValueError:
        return True
    match = re.search(r"-(\d{2})$", date_value)
    if not match:
        return True
    return int(match.group(1)) == day_number


def extracted_code_is_known(code: str, known_sop_codes: set[str]) -> bool:
    normalized_code = code.strip().casefold()
    if not normalized_code:
        return True
    return normalized_code in known_sop_codes


def live_extraction_result_to_review_rows(
    extraction: dict[str, object],
    selected_file: dict[str, str],
    session: dict[str, str | int],
    sop_codes: list[dict[str, str]],
) -> list[dict[str, str | bool]]:
    if bool(extraction.get("month_mismatch")) or not document_month_matches_session(
        extraction,
        session,
    ):
        return [build_month_mismatch_row(extraction, selected_file, session)]

    entries = extraction.get("entries", [])
    if not isinstance(entries, list):
        raise ValueError("OpenAI extraction did not include a valid entries list.")

    source_type = str(extraction.get("source_type") or selected_file["source_type"] or "unknown")
    detected_worker_name = clean_extracted_value(extraction.get("detected_worker_name"))
    suggested_worker_match = clean_extracted_value(extraction.get("suggested_worker_match"))
    known_sop_codes = {
        str(item.get("code") or "").strip().casefold()
        for item in sop_codes
        if str(item.get("code") or "").strip()
    }
    if not entries:
        entries = [
            {
                "day": "",
                "date": "",
                "start_time": "",
                "end_time": "",
                "hours_worked": "",
                "notes": "",
                "requires_review": True,
                "review_reason": "blank_day: no entries extracted.",
            }
        ]

    rows = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue

        review_reason = normalize_review_reason(str(entry.get("review_reason") or ""))
        entry_worker = clean_extracted_value(entry.get("worker"))
        worker_name = entry_worker or suggested_worker_match or detected_worker_name
        card_number = str(extraction.get("card_number") or "")
        month_seen = str(extraction.get("month_seen") or "")
        context_notes = []
        if card_number:
            context_notes.append(f"card {card_number}")
        if month_seen:
            context_notes.append(f"month seen {month_seen}")
        if source_type == "unknown" and "irrelevant_file" not in review_reason:
            review_reason = "irrelevant_file"
        if worker_value_is_combined(worker_name):
            review_reason = "unclear_worker_name"
            worker_name = ""

        day = clean_extracted_value(entry.get("day"))
        date_value = clean_extracted_value(entry.get("date"))
        start_time = clean_extracted_value(entry.get("start_time"))
        end_time = clean_extracted_value(entry.get("end_time"))
        hours_worked = clean_extracted_value(entry.get("hours_worked"))
        extracted_code = clean_extracted_value(entry.get("extracted_code"))
        notes = clean_extracted_value(entry.get("notes"))
        if (
            source_type == "physical_time_card"
            and card_number
            and not day_matches_card_number(day, card_number)
        ):
            review_reason = "date_mapping_unclear"
            date_value = ""
        if (
            source_type == "physical_time_card"
            and not date_day_matches_entry_day(date_value, day)
        ):
            review_reason = "date_mapping_unclear"
            date_value = ""
        if (str(entry.get("start_time") or "").strip() and not start_time) or (
            str(entry.get("end_time") or "").strip() and not end_time
        ):
            review_reason = "unclear_time"

        if (
            source_type in {"multi_worker_attendance_table", "physical_time_card"}
            and extracted_code
            and review_reason not in {"month_mismatch", "unclear_worker_name"}
            and not extracted_code_is_known(extracted_code, known_sop_codes)
        ):
            review_reason = "unknown_code"
        elif (
            source_type == "multi_worker_attendance_table"
            and notes.strip()
            and review_reason not in {"month_mismatch", "unclear_worker_name"}
            and not note_matches_known_sop(notes, known_sop_codes)
        ):
            review_reason = "unknown_code"

        requires_attention = bool(entry.get("requires_review")) or bool(review_reason)
        if context_notes:
            notes = f"{notes} ({', '.join(context_notes)})" if notes else f"({', '.join(context_notes)})"

        rows.append(
            {
                "row_id": f"live-{uuid4().hex}",
                "extraction_mode": "real_openai",
                "worker": worker_name,
                "date": date_value,
                "start_time": start_time,
                "end_time": end_time,
                "hours_worked": hours_worked,
                "notes": notes or extracted_code,
                "requires_attention": requires_attention,
                "review_reason": review_reason,
                "review_status": "needs_review" if requires_attention else "clean",
                "source_original_filename": selected_file["original_filename"],
                "source_stored_filename": selected_file["stored_filename"],
                "source_path": selected_file["source_path"],
                "source_kind": "image",
                "source_can_preview": True,
                "source_type": source_type,
                "source_type_label": get_source_type_label(source_type),
                "preprocessing_status": "success",
                "preprocessing_error": "",
                "preprocessed_filename": selected_file["filename"],
                "preprocessed_path": selected_file["value"],
                "preprocessed_session_path": selected_file["session_relative_path"],
                "preprocessed_file_count": "1",
            }
        )

    return rows


def run_live_extraction_test(
    *,
    session: dict[str, str | int],
    workers: list[dict[str, str]],
    sop_codes: list[dict[str, str]],
    selected_file: dict[str, str],
) -> list[dict[str, str | bool]]:
    extraction = call_live_openai_extraction(
        session=session,
        workers=workers,
        sop_codes=sop_codes,
        selected_file=selected_file,
    )
    # Propagate error sentinel so app.py's per-file try/except marks the file failed
    # rather than passing a malformed dict to live_extraction_result_to_review_rows.
    if extraction.get("error"):
        raise ValueError(str(extraction.get("error_message") or "OpenAI extraction failed."))
    return live_extraction_result_to_review_rows(extraction, selected_file, session, sop_codes)


def _source_metadata(uploaded_file: dict[str, str] | None) -> dict[str, str | bool]:
    if not uploaded_file:
        return {
            "source_original_filename": "",
            "source_stored_filename": "",
            "source_path": "",
            "source_kind": "none",
            "source_can_preview": False,
            "source_type": "unknown",
            "source_type_label": get_source_type_label("unknown"),
        }

    extension = Path(uploaded_file["stored_filename"]).suffix.lower()
    source_kind = "file"
    can_preview = False
    if extension in IMAGE_PREVIEW_EXTENSIONS:
        source_kind = "image"
        can_preview = True
    elif extension == PDF_EXTENSION:
        source_kind = "pdf"

    return {
        "source_original_filename": uploaded_file["original_filename"],
        "source_stored_filename": uploaded_file["stored_filename"],
        "source_path": uploaded_file["path"],
        "source_kind": source_kind,
        "source_can_preview": can_preview,
        "source_type": uploaded_file.get("source_type", "unknown"),
        "source_type_label": uploaded_file.get(
            "source_type_label",
            get_source_type_label(uploaded_file.get("source_type", "unknown")),
        ),
    }


def _build_mock_row(
    *,
    row_id: str,
    worker: str,
    work_date: str,
    start_time: str,
    end_time: str,
    hours_worked: str,
    notes: str,
    requires_attention: bool,
    review_reason: str,
    source_file: dict[str, str] | None,
    extraction_mode: str = "mock",
) -> dict[str, str | bool]:
    return {
        "row_id": row_id,
        "extraction_mode": extraction_mode,
        "worker": worker,
        "date": work_date,
        "start_time": start_time,
        "end_time": end_time,
        "hours_worked": hours_worked,
        "notes": notes,
        "requires_attention": requires_attention,
        "review_reason": review_reason,
        **_source_metadata(source_file),
    }


def generate_mock_extraction_rows(
    workers: list[dict[str, str]] | None = None,
    session_id: str | None = None,
) -> list[dict[str, str | bool]]:
    uploaded_files = list_uploaded_files(session_id)
    _today = date.today()
    year, month = _today.year, _today.month
    if session_id:
        try:
            _session = load_session(session_id)
            year = int(_session["year"])
            month = int(_session["month"])
        except Exception:
            pass
    worker_names = [
        str(worker.get("name", "")).strip()
        for worker in workers or []
        if str(worker.get("name", "")).strip()
    ]
    if not worker_names:
        worker_names = ["Kim Tan", "Serene Lim", "John Lee"]

    physical_sources = [
        uploaded_file
        for uploaded_file in uploaded_files
        if uploaded_file.get("source_type") == "physical_time_card"
    ]
    table_sources = [
        uploaded_file
        for uploaded_file in uploaded_files
        if uploaded_file.get("source_type") == "multi_worker_attendance_table"
    ]
    pdf_sources = [
        uploaded_file
        for uploaded_file in uploaded_files
        if uploaded_file.get("source_type") == "pdf_or_excel_style"
    ]

    first_source = physical_sources[0] if physical_sources else None
    if first_source is None and uploaded_files:
        first_source = uploaded_files[0]

    table_source = table_sources[0] if table_sources else None
    if table_source is None:
        table_source = uploaded_files[1] if len(uploaded_files) > 1 else first_source

    pdf_source = pdf_sources[0] if pdf_sources else None
    if pdf_source is None:
        pdf_source = uploaded_files[2] if len(uploaded_files) > 2 else first_source

    rows = [
        _build_mock_row(
            row_id="mock-001",
            worker=worker_names[0],
            work_date=f"{year}-{month:02d}-01",
            start_time="08:30",
            end_time="18:05",
            hours_worked="9h 35m",
            notes="Physical card stamp",
            requires_attention=False,
            review_reason="",
            source_file=first_source,
        ),
        _build_mock_row(
            row_id="mock-002",
            worker=worker_names[min(1, len(worker_names) - 1)],
            work_date=f"{year}-{month:02d}-02",
            start_time="09:00",
            end_time="18:00",
            hours_worked="9h 00m",
            notes="From attendance table",
            requires_attention=False,
            review_reason="",
            source_file=table_source,
        ),
        _build_mock_row(
            row_id="mock-003",
            worker=worker_names[min(2, len(worker_names) - 1)],
            work_date=f"{year}-{month:02d}-03",
            start_time="09:10",
            end_time="18:00",
            hours_worked="8h 50m",
            notes="Possible overwritten stamp",
            requires_attention=True,
            review_reason="unclear_time: start time appears overwritten.",
            source_file=first_source,
        ),
        _build_mock_row(
            row_id="mock-004",
            worker=worker_names[min(1, len(worker_names) - 1)],
            work_date=f"{year}-{month:02d}-04",
            start_time="",
            end_time="",
            hours_worked="0h 00m",
            notes="OFF in table",
            requires_attention=True,
            review_reason="blank_day: confirm this should be marked OFF.",
            source_file=table_source,
        ),
        _build_mock_row(
            row_id="mock-005",
            worker=worker_names[0],
            work_date=f"{year}-{month:02d}-05",
            start_time="08:45",
            end_time="17:45",
            hours_worked="9h 00m",
            notes="PDF-style printed row",
            requires_attention=False,
            review_reason="",
            source_file=pdf_source,
        ),
    ]

    for index, uploaded_file in enumerate(uploaded_files[3:], start=6):
        is_table = uploaded_file.get("source_type") == "multi_worker_attendance_table"
        rows.append(
            _build_mock_row(
                row_id=f"mock-{index:03d}",
                worker=worker_names[(index - 1) % len(worker_names)],
                work_date=f"{year}-{month:02d}-{index:02d}",
                start_time="08:45" if not is_table else "09:00",
                end_time="17:45" if not is_table else "18:00",
                hours_worked="9h 00m",
                notes="MC" if index % 2 == 0 else "Table row" if is_table else "",
                requires_attention=index % 2 == 0,
                review_reason="unknown_code: confirm MC note." if index % 2 == 0 else "",
                source_file=uploaded_file,
            )
        )

    return rows
