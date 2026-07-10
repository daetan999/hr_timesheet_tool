import asyncio
import os
import re
from io import BytesIO
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from uuid import uuid4

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.concurrency import run_in_threadpool
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv() -> bool:
        return False


from services.config_store import (
    load_crop_templates,
    load_sop_codes,
    load_workers,
    normalize_sop_code_display,
    normalize_sop_code_value,
    save_sop_codes,
    save_workers,
)
from services.ai_extractor import (
    build_live_extraction_options,
    call_second_pass_openai_recheck,
    find_live_extraction_option,
    generate_mock_extraction_rows,
    get_extraction_status,
    run_live_extraction_test,
)
from services.excel_exporter import export_reviewed_rows_to_excel
from services.file_processor import (
    delete_uploaded_file,
    get_preprocessing_manifest_by_upload,
    get_source_type_label,
    get_upload_directory,
    list_uploaded_files,
    load_preprocessing_manifest,
    preprocess_uploaded_files,
    save_uploaded_files,
)
from services.session_store import (
    SessionNotFoundError,
    delete_session,
    ensure_session,
    get_session_exports_directory,
    get_session_upload_directory,
    get_sessions_directory,
    list_sessions,
    load_reviewed_rows,
    load_session,
    save_reviewed_rows,
)


load_dotenv()

_DATA_ROOT = Path(os.getenv("DATA_DIR", "."))

app = FastAPI(title="Timesheet Analysis Tool")

app.mount("/static", StaticFiles(directory="static"), name="static")

_upload_dir = get_upload_directory()
_upload_dir.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(_upload_dir)), name="uploads")

templates = Jinja2Templates(directory="templates")
# Regenerated on every process start (i.e. every deploy) so browsers/edge
# caches always fetch the current style.css instead of a stale copy served
# under an unchanged "?v=" query string.
templates.env.globals["asset_version"] = uuid4().hex[:8]


@app.exception_handler(SessionNotFoundError)
async def session_not_found_handler(request: Request, exc: SessionNotFoundError) -> Response:
    return Response(status_code=404)


@app.get("/sessions/{session_id}/files/preprocessed/{filename}")
async def session_serve_preprocessed_file(session_id: str, filename: str) -> FileResponse:
    safe_name = Path(filename).name
    resolved = resolve_session_preprocessed_image(session_id, f"{session_id}/preprocessed/{safe_name}")
    if resolved is None:
        raise HTTPException(status_code=404)
    return FileResponse(resolved)


@app.get("/sessions/{session_id}/files/uploads/{filename}")
async def session_serve_upload_file(session_id: str, filename: str) -> FileResponse:
    safe_name = Path(filename).name
    uploads_dir = get_session_upload_directory(session_id).resolve()
    file_path = (uploads_dir / safe_name).resolve()
    try:
        file_path.relative_to(uploads_dir)
    except ValueError:
        raise HTTPException(status_code=404)
    if not file_path.is_file():
        raise HTTPException(status_code=404)
    return FileResponse(file_path)


MONTHS = [
    {"value": 1, "label": "January"},
    {"value": 2, "label": "February"},
    {"value": 3, "label": "March"},
    {"value": 4, "label": "April"},
    {"value": 5, "label": "May"},
    {"value": 6, "label": "June"},
    {"value": 7, "label": "July"},
    {"value": 8, "label": "August"},
    {"value": 9, "label": "September"},
    {"value": 10, "label": "October"},
    {"value": 11, "label": "November"},
    {"value": 12, "label": "December"},
]

WORKER_TYPES = ["Full-time", "Part-time"]
WORKFLOW_STEPS = [
    {"number": 1, "label": "Month & Year", "endpoint": "session_started"},
    {"number": 2, "label": "Workers", "endpoint": "session_workers"},
    {"number": 3, "label": "SOP Codes", "endpoint": "session_sop_codes"},
    {"number": 4, "label": "Upload", "endpoint": "session_upload"},
    {"number": 5, "label": "Review", "endpoint": "session_review"},
    {"number": 6, "label": "Export", "endpoint": "session_export_excel"},
]

REVIEW_STATUSES = {"needs_review", "reviewed", "clean"}
REVIEW_VIEW_FILTERS = {"needs_review", "reviewed", "all"}
AI_AUDIT_FIELDS = {
    "ai_second_pass_checked",
    "ai_confidence",
    "ai_reason",
    "ai_recommendation",
    "ai_suggested_fields",
    "ai_original_fields",
    "ai_checked_at",
    "ai_batch_run_id",
    "ai_batch_status",
}
AI_BATCH_RUNS: dict[str, dict[str, object]] = {}
LIVE_EXTRACTION_BATCH_RUNS: dict[str, dict[str, object]] = {}


def _prune_batch_runs(runs: dict[str, dict[str, object]], max_runs: int = 30) -> None:
    if len(runs) <= max_runs:
        return
    terminal_keys = [
        key for key, state in runs.items()
        if state.get("status") in {"completed", "cancelled", "failed"}
    ]
    for key in terminal_keys[:len(runs) - max_runs]:
        del runs[key]


def normalize_unique_value(value: str) -> str:
    return " ".join(value.split()).casefold()


def build_year_options() -> list[int]:
    current_year = date.today().year
    return list(range(current_year - 2, current_year + 3))


def month_label_for(month: int) -> str:
    return next(item["label"] for item in MONTHS if item["value"] == month)


def build_preprocessing_failures(session_id: str | None) -> list[dict[str, object]]:
    return [
        item
        for item in load_preprocessing_manifest(session_id)
        if item.get("status") == "failed"
    ]


def build_preprocessed_metadata(
    row: dict[str, object],
    preprocessing_by_upload: dict[str, dict[str, object]],
) -> dict[str, object]:
    source_stored_filename = str(row.get("source_stored_filename") or "")
    manifest_entry = preprocessing_by_upload.get(source_stored_filename, {})
    preprocessed_files = manifest_entry.get("preprocessed_files", [])
    first_preprocessed_file = None
    if isinstance(preprocessed_files, list) and preprocessed_files:
        first_preprocessed_file = preprocessed_files[0]

    preprocessed_filename = ""
    preprocessed_path = ""
    preprocessed_session_path = ""
    if isinstance(first_preprocessed_file, dict):
        preprocessed_filename = str(first_preprocessed_file.get("filename") or "")
        preprocessed_path = str(first_preprocessed_file.get("path") or "")
        preprocessed_session_path = str(first_preprocessed_file.get("session_relative_path") or "")

    return {
        "preprocessing_status": str(manifest_entry.get("status") or "not_available"),
        "preprocessing_error": str(manifest_entry.get("error") or ""),
        "preprocessed_filename": preprocessed_filename,
        "preprocessed_path": preprocessed_path,
        "preprocessed_session_path": preprocessed_session_path,
        "preprocessed_file_count": len(preprocessed_files) if isinstance(preprocessed_files, list) else 0,
    }


def prepare_review_rows(
    rows: list[dict[str, str | bool]],
    session_id: str | None = None,
) -> list[dict[str, object]]:
    preprocessing_by_upload = get_preprocessing_manifest_by_upload(session_id)
    prepared_rows = []
    for row in rows:
        source_type = str(row.get("source_type") or "unknown")
        prepared_row = {
            **row,
            "extraction_mode": str(row.get("extraction_mode") or "mock"),
            "review_status": determine_review_status(row),
            "source_type": source_type,
            "source_type_label": str(
                row.get("source_type_label")
                or get_source_type_label(source_type)
            ),
            **build_preprocessed_metadata(row, preprocessing_by_upload),
        }
        prepared_row["unknown_sop_code"] = extract_unknown_sop_code_from_row(prepared_row)
        prepared_rows.append(prepared_row)
    return prepared_rows


def determine_review_status(row: dict[str, object]) -> str:
    explicit_status = str(row.get("review_status") or "").strip()
    if row_needs_review(row):
        return "needs_review"
    if explicit_status == "reviewed":
        return "reviewed"
    if explicit_status in REVIEW_STATUSES:
        return explicit_status
    return "clean"


def row_needs_review(row: dict[str, object]) -> bool:
    return bool(row.get("requires_attention")) or bool(str(row.get("review_reason") or "").strip())


def build_review_queue_counts(rows: list[dict[str, object]]) -> dict[str, int]:
    return {
        "needs_review": sum(1 for row in rows if row["review_status"] == "needs_review"),
        "reviewed": sum(1 for row in rows if row["review_status"] == "reviewed"),
        "all": len(rows),
    }


def filter_review_rows(rows: list[dict[str, object]], view_filter: str) -> list[dict[str, object]]:
    if view_filter == "reviewed":
        return [row for row in rows if row["review_status"] == "reviewed"]
    if view_filter == "all":
        return rows
    return [
        row for row in rows
        if row["review_status"] == "needs_review"
        or row_needs_review(row)
    ]


def parse_day_number(value: str) -> int | None:
    iso_match = re.search(r"\b\d{4}[-/](\d{1,2})[-/](\d{1,2})\b", value)
    if iso_match:
        day = int(iso_match.group(2))
        return day if 1 <= day <= 31 else None

    match = re.search(r"(?<!\d)([1-9]|[12][0-9]|3[01])(?!\d)", value)
    if not match:
        return None
    return int(match.group(1))


def normalize_card_number(value: str, day: int) -> str:
    card_number_match = re.search(r"\b([12])\b", value)
    if card_number_match:
        return card_number_match.group(1)
    return "1" if day <= 15 else "2"


def row_card_number(row: dict[str, object]) -> str:
    notes = str(row.get("notes") or "")
    match = re.search(r"\bcard\s*([12])\b", notes, flags=re.IGNORECASE)
    if match:
        return match.group(1)
    return ""


def find_enabled_crop_template(
    *,
    source_type: str,
    card_number: str,
) -> tuple[dict[str, object] | None, str]:
    matching_disabled_template = None
    for template in load_crop_templates().values():
        template_source_type = str(template.get("source_type") or "")
        template_card_number = str(template.get("card_number") or "")
        if template_source_type != source_type or template_card_number != card_number:
            continue
        if bool(template.get("enabled")):
            return template, ""
        matching_disabled_template = template

    if matching_disabled_template:
        template_name = str(matching_disabled_template.get("template_name") or "matching crop template")
        return None, f"{template_name} exists but is disabled."
    return None, "No matching crop template is configured."


def calculate_crop_geometry(
    *,
    width: int,
    height: int,
    day: int,
    template: dict[str, object],
) -> dict[str, object]:
    card_left_ratio = float(template["card_left_ratio"])
    card_right_ratio = float(template["card_right_ratio"])
    card_top_ratio = float(template["card_top_ratio"])
    card_bottom_ratio = float(template["card_bottom_ratio"])
    table_top_ratio = float(template["table_top_ratio_within_card"])
    table_bottom_ratio = float(template["table_bottom_ratio_within_card"])
    first_day = int(template["first_day"])
    last_day = int(template["last_day"])
    row_count = last_day - first_day + 1
    warnings = []

    if row_count <= 0 or not first_day <= day <= last_day:
        raise ValueError("Day does not fit crop template.")
    if not 0 <= card_left_ratio < card_right_ratio <= 1:
        raise ValueError("Card horizontal ratios are invalid.")
    if not 0 <= card_top_ratio < card_bottom_ratio <= 1:
        raise ValueError("Card vertical ratios are invalid.")
    if not 0 <= table_top_ratio < table_bottom_ratio <= 1:
        raise ValueError("Table-within-card ratios are invalid.")

    card_left = int(width * card_left_ratio)
    card_right = int(width * card_right_ratio)
    card_top = int(height * card_top_ratio)
    card_bottom = int(height * card_bottom_ratio)
    card_width = max(card_right - card_left, 1)
    card_height = max(card_bottom - card_top, 1)

    table_top = card_top + int(card_height * table_top_ratio)
    table_bottom = card_top + int(card_height * table_bottom_ratio)
    table_height = max(table_bottom - table_top, 1)

    day_index = day - first_day
    row_height = table_height / row_count
    target_top = table_top + (day_index * row_height)
    target_bottom = target_top + row_height

    raw_crop_top = int(target_top - row_height)
    raw_crop_bottom = int(target_bottom + row_height)
    crop_top = max(card_top, raw_crop_top)
    crop_bottom = min(card_bottom, raw_crop_bottom)
    crop_left = max(0, int(card_left - (card_width * 0.02)))
    crop_right = min(width, int(card_right + (card_width * 0.02)))

    fallback_top = max(table_top, int(target_top - (row_height * 2.5)))
    fallback_bottom = min(table_bottom, int(target_bottom + (row_height * 2.5)))

    crop_box = {"left": crop_left, "top": crop_top, "right": crop_right, "bottom": crop_bottom}
    fallback_box = {"left": crop_left, "top": fallback_top, "right": crop_right, "bottom": fallback_bottom}
    card_bounds = {"left": card_left, "top": card_top, "right": card_right, "bottom": card_bottom}
    table_bounds = {"left": card_left, "top": table_top, "right": card_right, "bottom": table_bottom}
    target_row_bounds = {
        "top": int(target_top),
        "bottom": int(target_bottom),
    }

    if raw_crop_top < card_top or raw_crop_bottom > card_bottom:
        warnings.append("Crop likely invalid. Check card/table calibration.")
    table_overlap = max(0, min(crop_bottom, table_bottom) - max(crop_top, table_top))
    crop_height = max(crop_bottom - crop_top, 1)
    if crop_bottom <= table_top or crop_top >= table_bottom or table_overlap / crop_height < 0.4:
        warnings.append("Crop likely invalid. Check card/table calibration.")
    if crop_bottom <= crop_top or crop_right <= crop_left:
        warnings.append("Crop likely invalid. Check card/table calibration.")

    return {
        "image_size": {"width": width, "height": height},
        "card_bounds": card_bounds,
        "table_bounds": table_bounds,
        "target_row_index": day_index,
        "target_row_index_display": day_index + 1,
        "target_row_bounds": target_row_bounds,
        "row_height": row_height,
        "crop_box": crop_box,
        "fallback_box": fallback_box,
        "warnings": sorted(set(warnings)),
    }


def crop_box_to_tuple(crop_box: dict[str, int]) -> tuple[int, int, int, int]:
    return (
        int(crop_box["left"]),
        int(crop_box["top"]),
        int(crop_box["right"]),
        int(crop_box["bottom"]),
    )


def build_physical_card_crop(
    image_path: Path,
    day: int,
    template: dict[str, object],
    *,
    crop_kind: str = "row",
) -> BytesIO:
    from PIL import Image

    with Image.open(image_path) as image:
        image = image.convert("RGB")
        width, height = image.size
        geometry = calculate_crop_geometry(width=width, height=height, day=day, template=template)
        crop_box = geometry["fallback_box"] if crop_kind == "fallback" else geometry["crop_box"]

        cropped = image.crop(crop_box_to_tuple(crop_box))
        output = BytesIO()
        cropped.save(output, format="JPEG", quality=92)
        output.seek(0)
        return output


def get_crop_diagnostics(image_path: Path, day: int, template: dict[str, object]) -> dict[str, object]:
    from PIL import Image

    with Image.open(image_path) as image:
        width, height = image.size
    return calculate_crop_geometry(width=width, height=height, day=day, template=template)


def list_session_preprocessed_images(session_id: str) -> list[dict[str, str]]:
    preprocessed_dir = get_sessions_directory() / session_id / "preprocessed"
    if not preprocessed_dir.exists():
        return []

    images = []
    for path in sorted(preprocessed_dir.iterdir()):
        if not path.is_file() or path.suffix.lower() not in {".jpg", ".jpeg", ".png"}:
            continue
        images.append(
            {
                "filename": path.name,
                "session_relative_path": f"{session_id}/preprocessed/{path.name}",
            }
        )
    return images


def resolve_session_preprocessed_image(session_id: str, image_path: str) -> Path | None:
    sessions_root = get_sessions_directory().resolve()
    session_preprocessed_dir = (sessions_root / session_id / "preprocessed").resolve()
    requested_path = (sessions_root / image_path).resolve()

    try:
        requested_path.relative_to(session_preprocessed_dir)
    except ValueError:
        return None

    if not requested_path.is_file():
        return None
    return requested_path


def row_is_unresolved_for_ai(row: dict[str, object]) -> bool:
    return str(row.get("review_status") or "") == "needs_review" or row_needs_review(row)


def second_pass_skip_reason(row: dict[str, object], session_id: str) -> str:
    review_reason = str(row.get("review_reason") or "")
    worker = str(row.get("worker") or "").strip()
    date_value = str(row.get("date") or "").strip()
    image_path = str(row.get("preprocessed_session_path") or "")

    if not row_is_unresolved_for_ai(row):
        return "Row is not unresolved."
    if review_reason_contains(review_reason, "month_mismatch"):
        return "Skipped month mismatch row for manual HR review."
    if review_reason_contains(review_reason, "irrelevant_file"):
        return "Skipped irrelevant file row for manual HR review."
    if review_reason_contains(review_reason, "date_mapping_unclear") and not worker and not date_value:
        return "Skipped document-level date mapping issue for manual HR review."
    if not image_path:
        return "No preprocessed image is available."
    if resolve_session_preprocessed_image(session_id, image_path) is None:
        return "Preprocessed image is missing or invalid."
    return ""


def second_pass_original_fields(row: dict[str, object]) -> dict[str, str]:
    return {
        "worker": str(row.get("worker") or ""),
        "date": str(row.get("date") or ""),
        "start_time": str(row.get("start_time") or ""),
        "end_time": str(row.get("end_time") or ""),
        "hours_worked": str(row.get("hours_worked") or ""),
        "notes": str(row.get("notes") or ""),
        "review_reason": str(row.get("review_reason") or ""),
    }


def second_pass_batch_status_for_recommendation(recommendation: str) -> str:
    return {
        "auto_confirm": "auto_confirmed",
        "auto_fill": "auto_filled",
        "suggest_only": "suggestion_only",
        "no_suggestion": "no_suggestion",
    }.get(recommendation, "no_suggestion")


def apply_second_pass_result_to_row(
    row: dict[str, object],
    result: dict[str, object],
    *,
    batch_run_id: str = "",
    persist_auto_fill: bool = False,
) -> dict[str, object]:
    recommendation = str(result.get("recommendation") or "no_suggestion")
    fields_to_update = result.get("fields_to_update")
    if not isinstance(fields_to_update, dict):
        fields_to_update = {}

    audit_fields = {
        "ai_second_pass_checked": True,
        "ai_confidence": result.get("confidence", 0.0),
        "ai_reason": str(result.get("reason") or ""),
        "ai_recommendation": recommendation,
        "ai_suggested_fields": {
            "start_time": str(fields_to_update.get("start_time") or ""),
            "end_time": str(fields_to_update.get("end_time") or ""),
            "hours_worked": str(fields_to_update.get("hours_worked") or ""),
            "notes": str(fields_to_update.get("notes") or ""),
        },
        "ai_original_fields": row.get("ai_original_fields") or second_pass_original_fields(row),
        "ai_checked_at": datetime.now(timezone.utc).isoformat(),
        "ai_batch_run_id": batch_run_id,
        "ai_batch_status": second_pass_batch_status_for_recommendation(recommendation),
    }
    row.update(audit_fields)

    auto_confirmed = recommendation == "auto_confirm"
    should_apply_fields = auto_confirmed or (recommendation == "auto_fill" and persist_auto_fill)
    if should_apply_fields:
        for field_name in ["start_time", "end_time", "hours_worked", "notes"]:
            suggested_value = str(fields_to_update.get(field_name) or "").strip()
            if suggested_value:
                row[field_name] = suggested_value
    if auto_confirmed:
        row["requires_attention"] = False
        row["review_reason"] = ""
        row["review_status"] = "reviewed"
        row["hr_decision"] = "ai_auto_confirmed"

    return {
        "audit": audit_fields,
        "auto_confirmed": auto_confirmed,
        "updated_fields": {
            "start_time": str(row.get("start_time") or ""),
            "end_time": str(row.get("end_time") or ""),
            "hours_worked": str(row.get("hours_worked") or ""),
            "notes": str(row.get("notes") or ""),
            "hr_decision": str(row.get("hr_decision") or ""),
        },
    }


def run_second_pass_for_row(
    *,
    session_id: str,
    session: dict[str, str | int],
    row: dict[str, object],
    sop_codes: list[dict[str, str]],
    batch_run_id: str = "",
    persist_auto_fill: bool = False,
) -> dict[str, object]:
    preprocessed_session_path = str(row.get("preprocessed_session_path") or "")
    requested_path = resolve_session_preprocessed_image(session_id, preprocessed_session_path)
    if requested_path is None:
        raise ValueError("Preprocessed image was not found for this row.")

    result = call_second_pass_openai_recheck(
        session=session,
        row=row,
        sop_codes=sop_codes,
        image_path=requested_path,
        card_number=row_card_number(row),
    )
    if result.get("error"):
        raise ValueError(result.get("error_message") or "AI second-pass failed.")
    applied = apply_second_pass_result_to_row(
        row,
        result,
        batch_run_id=batch_run_id,
        persist_auto_fill=persist_auto_fill,
    )
    return {
        "result": result,
        **applied,
    }


def build_ai_batch_summary(rows: list[dict[str, object]], session_id: str) -> dict[str, int]:
    summary = {
        "considered": 0,
        "total_eligible": 0,
        "processed": 0,
        "auto_confirmed": 0,
        "auto_filled": 0,
        "suggestions_only": 0,
        "no_suggestion": 0,
        "skipped": 0,
        "failed": 0,
        "cancelled": 0,
    }
    for row in rows:
        if not row_is_unresolved_for_ai(row):
            continue
        summary["considered"] += 1
        if second_pass_skip_reason(row, session_id):
            summary["skipped"] += 1
        else:
            summary["total_eligible"] += 1
    return summary


def batch_state_payload(batch_run_id: str) -> dict[str, object]:
    state = AI_BATCH_RUNS.get(batch_run_id)
    if not state:
        return {
            "success": False,
            "message": "AI second-pass batch was not found.",
        }
    return {
        "success": True,
        "batch_run_id": batch_run_id,
        "session_id": state.get("session_id", ""),
        "status": state.get("status", "unknown"),
        "message": state.get("message", ""),
        "summary": state.get("summary", {}),
        "rows": state.get("rows", []),
    }


def live_extraction_batch_state_payload(batch_run_id: str) -> dict[str, object]:
    state = LIVE_EXTRACTION_BATCH_RUNS.get(batch_run_id)
    if not state:
        return {
            "success": False,
            "message": "Extraction batch was not found.",
        }
    return {
        "success": True,
        "batch_run_id": batch_run_id,
        "session_id": state.get("session_id", ""),
        "status": state.get("status", "unknown"),
        "message": state.get("message", ""),
        "summary": state.get("summary", {}),
        "results": state.get("results", []),
    }


def _merge_rows(
    existing: list[dict[str, object]],
    new_rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    """Merge new_rows into existing by row_id.

    - Rows in new_rows whose row_id does not exist in existing are appended.
    - Rows in new_rows whose row_id already exists replace the existing row.
    - Rows in existing with no matching row_id in new_rows are kept unchanged.
    - Rows with no row_id (empty string) are handled safely: they are indexed
      by their position and never collapsed into a single entry.
    """
    merged: dict[str, dict[str, object]] = {}
    positional: list[dict[str, object]] = []

    for row in existing:
        rid = str(row.get("row_id") or "")
        if rid:
            merged[rid] = row
        else:
            positional.append(row)

    for row in new_rows:
        rid = str(row.get("row_id") or "")
        if rid:
            merged[rid] = row
        else:
            positional.append(row)

    return list(merged.values()) + positional


async def run_live_extraction_batch_worker(session_id: str, batch_run_id: str) -> None:
    state = LIVE_EXTRACTION_BATCH_RUNS[batch_run_id]
    session = load_session(session_id)
    workers = load_workers()
    sop_codes = load_sop_codes()
    options = build_live_extraction_options(session_id)
    summary = state["summary"]
    results = state["results"]
    review_rows: list[dict[str, object]] = load_reviewed_rows(session_id)

    state["status"] = "running"
    state["message"] = "Extraction is running."
    try:
        for selected_file in options:
            if state.get("cancel_requested"):
                summary["cancelled"] = 1
                state["status"] = "cancelled"
                state["message"] = "Extraction was cancelled. Already extracted rows were saved."
                break

            filename = str(selected_file.get("filename") or "Selected file")
            preprocessed_path = Path(str(selected_file.get("value") or ""))
            if not preprocessed_path.exists():
                summary["processed"] += 1
                summary["skipped"] += 1
                results.append(
                    {
                        "filename": filename,
                        "status": "skipped",
                        "message": "Preprocessed file is missing.",
                    }
                )
                if review_rows:
                    save_reviewed_rows(session_id, review_rows)
                continue

            try:
                rows = await run_in_threadpool(
                    run_live_extraction_test,
                    session=session,
                    workers=workers,
                    sop_codes=sop_codes,
                    selected_file=selected_file,
                )
            except Exception as exc:
                summary["processed"] += 1
                summary["failed"] += 1
                results.append(
                    {
                        "filename": filename,
                        "status": "failed",
                        "message": str(exc) or "OpenAI live extraction failed.",
                    }
                )
                if review_rows:
                    save_reviewed_rows(session_id, review_rows)
                continue

            summary["processed"] += 1
            summary["succeeded"] += 1
            review_rows = _merge_rows(review_rows, rows)
            results.append(
                {
                    "filename": filename,
                    "status": "success",
                    "message": f"{len(rows)} review row{'s' if len(rows) != 1 else ''} extracted.",
                }
            )
            save_reviewed_rows(session_id, review_rows)

        if state.get("status") == "cancelling":
            summary["cancelled"] = 1
            state["status"] = "cancelled"
            state["message"] = "Extraction was cancelled. Already extracted rows were saved."
        elif state.get("status") not in {"cancelled", "failed"}:
            state["status"] = "completed"
            state["message"] = "Extraction batch complete."
    except Exception as exc:
        state["status"] = "failed"
        state["message"] = str(exc) or "Extraction batch failed."


async def run_ai_second_pass_batch_worker(session_id: str, batch_run_id: str) -> None:
    state = AI_BATCH_RUNS[batch_run_id]
    session = load_session(session_id)
    rows = load_reviewed_rows(session_id)
    sop_codes = load_sop_codes()
    summary = state["summary"]
    row_results = state["rows"]

    state["status"] = "running"
    state["message"] = "AI second-pass is running."
    try:
        for row in rows:
            if state.get("cancel_requested"):
                summary["cancelled"] = 1
                state["status"] = "cancelled"
                state["message"] = "AI second-pass was cancelled. Already processed rows were saved."
                break
            if not row_is_unresolved_for_ai(row):
                continue

            row_id = str(row.get("row_id") or "")
            skip_reason = second_pass_skip_reason(row, session_id)
            if skip_reason:
                row["ai_batch_run_id"] = batch_run_id
                row["ai_batch_status"] = "skipped"
                row_results.append(
                    {
                        "row_id": row_id,
                        "status": "skipped",
                        "message": skip_reason,
                    }
                )
                save_reviewed_rows(session_id, rows)
                continue

            try:
                processed = await run_in_threadpool(
                    run_second_pass_for_row,
                    session_id=session_id,
                    session=session,
                    row=row,
                    sop_codes=sop_codes,
                    batch_run_id=batch_run_id,
                    persist_auto_fill=True,
                )
            except Exception as exc:
                row["ai_batch_run_id"] = batch_run_id
                row["ai_batch_status"] = "failed"
                row["ai_checked_at"] = datetime.now(timezone.utc).isoformat()
                row["ai_reason"] = str(exc) or "AI second-pass failed."
                summary["failed"] += 1
                row_results.append(
                    {
                        "row_id": row_id,
                        "status": "failed",
                        "message": str(exc) or "AI second-pass failed.",
                    }
                )
                save_reviewed_rows(session_id, rows)
                continue

            result = processed["result"]
            recommendation = str(result.get("recommendation") or "no_suggestion")
            summary["processed"] += 1
            if recommendation == "auto_confirm":
                summary["auto_confirmed"] += 1
            elif recommendation == "auto_fill":
                summary["auto_filled"] += 1
            elif recommendation == "suggest_only":
                summary["suggestions_only"] += 1
            else:
                summary["no_suggestion"] += 1

            row_results.append(
                {
                    "row_id": row_id,
                    "status": "processed",
                    "recommendation": recommendation,
                    "result": result,
                    "audit": processed["audit"],
                    "auto_confirmed": processed["auto_confirmed"],
                    "review_status": str(row.get("review_status") or ""),
                    "requires_attention": bool(row.get("requires_attention")),
                    "review_reason": str(row.get("review_reason") or ""),
                    "updated_fields": processed["updated_fields"],
                }
            )
            save_reviewed_rows(session_id, rows)

        if state.get("status") == "cancelling":
            summary["cancelled"] = 1
            state["status"] = "cancelled"
            state["message"] = "AI second-pass was cancelled. Already processed rows were saved."
        elif state.get("status") not in {"cancelled", "failed"}:
            state["status"] = "completed"
            state["message"] = "AI second-pass batch complete."
    except Exception as exc:
        state["status"] = "failed"
        state["message"] = str(exc) or "AI second-pass batch failed."


def extract_unknown_sop_code_from_row(row: dict[str, object]) -> str:
    if not review_reason_has_unknown_code(str(row.get("review_reason") or "")):
        return ""

    notes = str(row.get("notes") or "").strip()
    if not notes:
        return ""

    return extract_sop_base_code(notes)


def extract_sop_base_code(value: str) -> str:
    code = normalize_sop_code_display(value)
    code = re.sub(r"^\s*(summary|detail)\s*:\s*", "", code, flags=re.IGNORECASE)
    code = re.sub(r"\([^)]*month\s+seen[^)]*\)", "", code, flags=re.IGNORECASE)

    code = normalize_sop_code_display(code.split(";", 1)[0])
    code = normalize_sop_code_display(code.split("(", 1)[0])
    code = re.sub(r"\bmonth\s+seen\b.*$", "", code, flags=re.IGNORECASE)
    code = normalize_sop_code_display(code)
    if not code or code.casefold().startswith("month seen "):
        return ""

    return code


def build_unknown_sop_codes(rows: list[dict[str, object]]) -> list[dict[str, str]]:
    sop_codes = load_sop_codes()
    unknown_codes_by_key = {}
    for row in rows:
        code = extract_unknown_sop_code_from_row(row)
        if not code:
            continue
        key = normalize_sop_code_value(code)
        if not key or sop_base_code_exists(code, sop_codes):
            continue
        unknown_codes_by_key.setdefault(key, code)

    return [
        {"code": code, "key": key}
        for key, code in sorted(unknown_codes_by_key.items(), key=lambda item: item[1].casefold())
    ]


def apply_sop_code_to_matching_review_rows(
    rows: list[dict[str, object]],
    code: str,
) -> list[dict[str, object]]:
    normalized_code = normalize_sop_code_value(code)
    updated_rows = []
    for row in rows:
        updated_row = dict(row)
        row_code = extract_unknown_sop_code_from_row(updated_row)
        if normalize_sop_code_value(row_code) == normalized_code:
            remaining_reason = remove_unknown_code_review_reason(str(updated_row.get("review_reason") or ""))
            updated_row["review_reason"] = remaining_reason
            updated_row["requires_attention"] = bool(remaining_reason)
        updated_rows.append(updated_row)
    return updated_rows


def review_reason_has_unknown_code(review_reason: str) -> bool:
    return "unknown_code" in split_review_reasons(review_reason)


def remove_unknown_code_review_reason(review_reason: str) -> str:
    remaining_reasons = [
        reason for reason in split_review_reasons(review_reason)
        if reason != "unknown_code"
    ]
    return ", ".join(remaining_reasons)


def split_review_reasons(review_reason: str) -> list[str]:
    return [
        reason.strip()
        for reason in re.split(r"[,;]+", review_reason)
        if reason.strip()
    ]


def review_reason_contains(review_reason: str, target_reason: str) -> bool:
    normalized_target = target_reason.strip().casefold()
    for reason in split_review_reasons(review_reason):
        normalized_reason = reason.casefold().strip()
        if normalized_reason == normalized_target or normalized_reason.startswith(f"{normalized_target}:"):
            return True
    return False


def sop_base_code_exists(code: str, sop_codes: list[dict[str, str]]) -> bool:
    normalized_code = normalize_sop_code_value(extract_sop_base_code(code))
    if not normalized_code:
        return False

    return normalized_code in {
        normalize_sop_code_value(extract_sop_base_code(item["code"]))
        for item in sop_codes if item.get("code")
    }


def session_context(session_id: str | None, current_step: int | None) -> dict[str, object]:
    if not session_id:
        return {"session": None, "session_id": None, "workflow_steps": [], "current_step": None}

    session = load_session(session_id)
    return {
        "session": {
            **session,
            "month_label": month_label_for(int(session["month"])),
        },
        "session_id": session_id,
        "workflow_steps": WORKFLOW_STEPS,
        "current_step": current_step,
    }


def render_workers_page(
    request: Request,
    *,
    workers: list[dict[str, str]] | None = None,
    message: str | None = None,
    error: str | None = None,
    session_id: str | None = None,
) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "workers.html",
        {
            "workers": workers if workers is not None else load_workers(),
            "worker_types": WORKER_TYPES,
            "message": message,
            "error": error,
            **session_context(session_id, 2 if session_id else None),
        },
    )


def render_sop_codes_page(
    request: Request,
    *,
    sop_codes: list[dict[str, str]] | None = None,
    message: str | None = None,
    error: str | None = None,
    session_id: str | None = None,
) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "sop_codes.html",
        {
            "sop_codes": sop_codes if sop_codes is not None else load_sop_codes(),
            "message": message,
            "error": error,
            **session_context(session_id, 3 if session_id else None),
        },
    )


def render_upload_page(
    request: Request,
    *,
    message: str | None = None,
    error: str | None = None,
    invalid_files: list[dict[str, str]] | None = None,
    session_id: str | None = None,
) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "upload.html",
        {
            "uploaded_files": list_uploaded_files(session_id),
            "message": message,
            "error": error,
            "invalid_files": invalid_files or [],
            **session_context(session_id, 4 if session_id else None),
        },
    )


def render_review_page(
    request: Request,
    *,
    rows: list[dict[str, str | bool]] | None = None,
    message: str | None = None,
    error: str | None = None,
    export_path: str | None = None,
    session_id: str | None = None,
) -> HTMLResponse:
    requested_view = request.query_params.get("view", "needs_review")
    active_review_view = requested_view if requested_view in REVIEW_VIEW_FILTERS else "needs_review"
    export_warning = request.query_params.get("export_warning")
    uploaded_files = list_uploaded_files(session_id)
    preprocessing_failures = build_preprocessing_failures(session_id)
    live_extraction_options = build_live_extraction_options(session_id)
    reviewed_rows = load_reviewed_rows(session_id) if session_id else []
    if session_id and reviewed_rows:
        backfilled = False
        for row in reviewed_rows:
            if not row.get("review_status"):
                row["review_status"] = determine_review_status(row)
                backfilled = True
        if backfilled:
            save_reviewed_rows(session_id, reviewed_rows)
    extraction_status = get_extraction_status()
    review_rows = rows if rows is not None else reviewed_rows or generate_mock_extraction_rows(
        load_workers(),
        session_id,
    )
    prepared_rows = prepare_review_rows(review_rows, session_id)
    review_counts = build_review_queue_counts(prepared_rows)
    ai_batch_initial_summary = build_ai_batch_summary(prepared_rows, session_id) if session_id else {}
    ai_second_pass_has_run = any(
        row.get("ai_second_pass_checked") or row.get("ai_batch_status")
        for row in prepared_rows
    )
    return templates.TemplateResponse(
        request,
        "review.html",
        {
            "rows": prepared_rows,
            "unknown_sop_codes": build_unknown_sop_codes(prepared_rows),
            "review_counts": review_counts,
            "active_review_view": active_review_view,
            "ai_batch_initial_summary": ai_batch_initial_summary,
            "ai_second_pass_has_run": ai_second_pass_has_run,
            "uploaded_files": uploaded_files,
            "has_uploads": bool(uploaded_files),
            "has_reviewed_rows": bool(reviewed_rows),
            "preprocessing_failures": preprocessing_failures,
            "live_extraction_options": live_extraction_options,
            "extraction_status": extraction_status,
            "message": message,
            "error": error,
            "export_path": export_path,
            "export_warning": export_warning,
            **session_context(session_id, 5 if session_id else None),
        },
    )


@app.get("/", response_class=HTMLResponse)
async def home(request: Request) -> HTMLResponse:
    today = date.today()
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "months": MONTHS,
            "years": build_year_options(),
            "selected_month": today.month,
            "selected_year": today.year,
            "recent_sessions": list_sessions(),
            "month_labels": {month["value"]: month["label"] for month in MONTHS},
        },
    )


@app.post("/start", response_class=HTMLResponse)
async def start_processing(
    request: Request,
    month: int = Form(...),
    year: int = Form(...),
) -> HTMLResponse:
    session = ensure_session(year, month)
    return RedirectResponse(
        url=f"/sessions/{session['session_id']}/started",
        status_code=303,
    )


@app.post("/sessions/{session_id}/delete")
async def session_delete(session_id: str) -> RedirectResponse:
    delete_session(session_id)
    return RedirectResponse(url="/", status_code=303)


@app.get("/sessions/{session_id}/started", response_class=HTMLResponse)
async def session_started(request: Request, session_id: str) -> HTMLResponse:
    session = load_session(session_id)
    return templates.TemplateResponse(
        request,
        "started.html",
        {
            **session_context(session_id, 1),
            "month": session["month"],
            "month_label": month_label_for(int(session["month"])),
            "year": session["year"],
        },
    )


@app.get("/sessions/{session_id}/workers", response_class=HTMLResponse)
async def session_workers(request: Request, session_id: str) -> HTMLResponse:
    load_session(session_id)
    return render_workers_page(request, session_id=session_id)


@app.post("/sessions/{session_id}/workers/add", response_class=HTMLResponse)
async def session_add_worker(
    request: Request,
    session_id: str,
    name: str = Form(""),
    worker_type: str = Form(...),
) -> HTMLResponse:
    return await add_worker(request, name=name, worker_type=worker_type, session_id=session_id)


@app.post("/sessions/{session_id}/workers/save", response_class=HTMLResponse)
async def session_update_workers(request: Request, session_id: str) -> HTMLResponse:
    return await update_workers(request, session_id=session_id)


@app.get("/sessions/{session_id}/sop-codes", response_class=HTMLResponse)
async def session_sop_codes(request: Request, session_id: str) -> HTMLResponse:
    load_session(session_id)
    return render_sop_codes_page(request, session_id=session_id)


@app.post("/sessions/{session_id}/sop-codes/add", response_class=HTMLResponse)
async def session_add_sop_code(
    request: Request,
    session_id: str,
    code: str = Form(""),
    meaning: str = Form(""),
) -> HTMLResponse:
    return await add_sop_code(request, code=code, meaning=meaning, session_id=session_id)


@app.post("/sessions/{session_id}/sop-codes/save", response_class=HTMLResponse)
async def session_update_sop_codes(request: Request, session_id: str) -> HTMLResponse:
    return await update_sop_codes(request, session_id=session_id)


@app.get("/sessions/{session_id}/upload", response_class=HTMLResponse)
async def session_upload(request: Request, session_id: str) -> HTMLResponse:
    load_session(session_id)
    return render_upload_page(request, session_id=session_id)


@app.post("/sessions/{session_id}/upload", response_class=HTMLResponse)
async def session_upload_files(
    request: Request,
    session_id: str,
    files: list[UploadFile] = File(default=[]),
) -> HTMLResponse:
    return await upload_files(request, files=files, session_id=session_id)


@app.post("/sessions/{session_id}/upload/delete", response_class=HTMLResponse)
async def session_delete_uploaded_file(
    request: Request,
    session_id: str,
    stored_filename: str = Form(...),
) -> HTMLResponse:
    load_session(session_id)
    delete_result = delete_uploaded_file(session_id, stored_filename)
    if not delete_result["upload_deleted"]:
        return render_upload_page(
            request,
            error="Uploaded file was not found.",
            session_id=session_id,
        )

    deleted_preprocessed_count = len(delete_result["deleted_preprocessed_files"])
    message = "Uploaded file deleted."
    if deleted_preprocessed_count:
        message = (
            f"Uploaded file deleted. Removed {deleted_preprocessed_count} "
            f"related preprocessed file{'s' if deleted_preprocessed_count != 1 else ''}."
        )

    return render_upload_page(request, message=message, session_id=session_id)


@app.get("/sessions/{session_id}/review", response_class=HTMLResponse)
async def session_review(request: Request, session_id: str) -> HTMLResponse:
    load_session(session_id)
    return render_review_page(request, session_id=session_id)


@app.get("/sessions/{session_id}/review/crop-calibration", response_class=HTMLResponse)
async def session_crop_calibration(request: Request, session_id: str) -> HTMLResponse:
    load_session(session_id)
    images = list_session_preprocessed_images(session_id)
    templates_by_key = load_crop_templates()
    template_items = [
        {"key": key, **template}
        for key, template in sorted(templates_by_key.items())
        if isinstance(template, dict)
    ]
    selected_image = request.query_params.get("image_path") or (
        images[0]["session_relative_path"] if images else ""
    )
    selected_template_key = request.query_params.get("template_key") or (
        "physical_time_card_er_m_card_2"
        if "physical_time_card_er_m_card_2" in templates_by_key
        else (template_items[0]["key"] if template_items else "")
    )
    selected_day = request.query_params.get("day") or "21"
    selected_template = templates_by_key.get(selected_template_key, {})
    crop_url = ""
    fallback_crop_url = ""
    diagnostics = {}
    diagnostics_error = ""
    if selected_image and selected_template_key and selected_day:
        base_crop_url = str(request.url_for("session_crop_calibration_image", session_id=session_id))
        crop_url = base_crop_url + "?" + urlencode(
            {
                "image_path": selected_image,
                "template_key": selected_template_key,
                "day": selected_day,
                "crop_kind": "row",
            }
        )
        fallback_crop_url = base_crop_url + "?" + urlencode(
            {
                "image_path": selected_image,
                "template_key": selected_template_key,
                "day": selected_day,
                "crop_kind": "fallback",
            }
        )
        requested_path = resolve_session_preprocessed_image(session_id, selected_image)
        try:
            if requested_path is None:
                raise ValueError("Invalid calibration image path.")
            diagnostics = get_crop_diagnostics(requested_path, int(selected_day), selected_template)
        except Exception as exc:
            diagnostics_error = str(exc) or "Could not calculate crop diagnostics."

    return templates.TemplateResponse(
        request,
        "crop_calibration.html",
        {
            "images": images,
            "templates": template_items,
            "selected_image": selected_image,
            "selected_template_key": selected_template_key,
            "selected_template": selected_template,
            "selected_day": selected_day,
            "test_days": [18, 21, 22, 27, 31],
            "crop_url": crop_url,
            "fallback_crop_url": fallback_crop_url,
            "diagnostics": diagnostics,
            "diagnostics_error": diagnostics_error,
            **session_context(session_id, 5),
        },
    )


@app.get("/sessions/{session_id}/review/crop-calibration/image")
async def session_crop_calibration_image(
    session_id: str,
    image_path: str = "",
    template_key: str = "",
    day: int = 21,
    crop_kind: str = "row",
) -> Response:
    load_session(session_id)
    requested_path = resolve_session_preprocessed_image(session_id, image_path)
    if requested_path is None:
        return JSONResponse({"success": False, "message": "Invalid calibration image path."}, status_code=400)

    template = load_crop_templates().get(template_key)
    if not isinstance(template, dict):
        return JSONResponse({"success": False, "message": "Crop template was not found."}, status_code=404)

    try:
        crop = build_physical_card_crop(
            requested_path,
            day,
            template,
            crop_kind="fallback" if crop_kind == "fallback" else "row",
        )
    except Exception:
        return JSONResponse({"success": False, "message": "Could not generate calibration crop."}, status_code=400)

    return Response(content=crop.getvalue(), media_type="image/jpeg")


@app.post("/sessions/{session_id}/review", response_class=HTMLResponse)
async def session_save_review_rows(request: Request, session_id: str) -> HTMLResponse:
    return await save_review_rows(request, session_id=session_id)


@app.post("/sessions/{session_id}/review/sop-code/add", response_class=HTMLResponse)
async def session_add_unknown_sop_code(
    request: Request,
    session_id: str,
    code: str = Form(""),
    meaning: str = Form(""),
    apply_to_matching_rows: str | None = Form(None),
) -> HTMLResponse:
    load_session(session_id)
    reviewed_rows = load_reviewed_rows(session_id)
    sop_codes = load_sop_codes()
    sop_code = extract_sop_base_code(code)
    sop_meaning = meaning.strip()

    if not sop_code or not sop_meaning:
        return render_review_page(
            request,
            error="SOP code and meaning cannot be blank.",
            session_id=session_id,
        )

    if sop_base_code_exists(sop_code, sop_codes):
        return render_review_page(
            request,
            error=f"SOP code already exists: {sop_code}",
            session_id=session_id,
        )

    sop_codes.append({"code": sop_code, "meaning": sop_meaning})
    save_sop_codes(sop_codes)

    message = f"SOP preset added: {sop_code}."
    if apply_to_matching_rows:
        reviewed_rows = apply_sop_code_to_matching_review_rows(reviewed_rows, sop_code)
        save_reviewed_rows(session_id, reviewed_rows)
        message = f"SOP preset added: {sop_code}. Matching review rows were updated."

    return render_review_page(
        request,
        rows=reviewed_rows,
        message=message,
        session_id=session_id,
    )


@app.post("/sessions/{session_id}/review/sop-code/add-json")
async def session_add_unknown_sop_code_json(
    session_id: str,
    code: str = Form(""),
    meaning: str = Form(""),
    apply_to_matching_rows: bool = Form(False),
) -> JSONResponse:
    load_session(session_id)
    reviewed_rows = load_reviewed_rows(session_id)
    sop_codes = load_sop_codes()
    sop_code = extract_sop_base_code(code)
    sop_meaning = meaning.strip()

    if not sop_code or not sop_meaning:
        return JSONResponse(
            {
                "success": False,
                "message": "SOP code and meaning cannot be blank.",
            },
            status_code=400,
        )

    if len(sop_code) > 20:
        return JSONResponse(
            {
                "success": False,
                "message": "SOP code must be 20 characters or less. Use a short code like AL, MC, or OFF.",
            },
            status_code=400,
        )

    if sop_base_code_exists(sop_code, sop_codes):
        return JSONResponse(
            {
                "success": False,
                "message": "SOP code already exists.",
                "code": sop_code,
                "normalized_code": normalize_sop_code_value(sop_code),
            },
            status_code=409,
        )

    sop_codes.append({"code": sop_code, "meaning": sop_meaning})
    save_sop_codes(sop_codes)

    matching_row_ids = []
    if apply_to_matching_rows:
        normalized_code = normalize_sop_code_value(sop_code)
        for row in reviewed_rows:
            row_code = extract_unknown_sop_code_from_row(row)
            if normalize_sop_code_value(row_code) == normalized_code:
                matching_row_ids.append(str(row.get("row_id") or ""))
        reviewed_rows = apply_sop_code_to_matching_review_rows(reviewed_rows, sop_code)
        save_reviewed_rows(session_id, reviewed_rows)

    return JSONResponse(
        {
            "success": True,
            "message": "SOP code added.",
            "code": sop_code,
            "normalized_code": normalize_sop_code_value(sop_code),
            "apply_to_matching_rows": apply_to_matching_rows,
            "matching_row_ids": matching_row_ids,
        }
    )


@app.post("/sessions/{session_id}/review/row/save-reviewed-json")
async def session_save_review_row_as_reviewed(
    session_id: str,
    row_id: str = Form(""),
    worker: str = Form(""),
    date_value: str = Form("", alias="date"),
    start_time: str = Form(""),
    end_time: str = Form(""),
    hours_worked: str = Form(""),
    notes: str = Form(""),
    hr_decision: str = Form(""),
    hr_correction_note: str = Form(""),
) -> JSONResponse:
    load_session(session_id)
    # P0-C: load_reviewed_rows() always reads fresh from disk — no module-level cache.
    # save_reviewed_rows() writes via atomic tmp-replace, so concurrent batch writes
    # cannot corrupt the file mid-write. For single-user local use this is sufficient.
    rows = load_reviewed_rows(session_id)
    for row in rows:
        if str(row.get("row_id") or "") != row_id:
            continue

        row.update(
            {
                "worker": worker.strip(),
                "date": date_value.strip(),
                "start_time": start_time.strip(),
                "end_time": end_time.strip(),
                "hours_worked": hours_worked.strip(),
                "notes": notes,
                "requires_attention": False,
                "review_reason": "",
                "review_status": "reviewed",
                "hr_decision": hr_decision.strip(),
                "hr_correction_note": hr_correction_note.strip(),
            }
        )
        save_reviewed_rows(session_id, rows)
        return JSONResponse(
            {
                "success": True,
                "message": "Row saved and marked reviewed.",
                "row_id": row_id,
                "review_status": "reviewed",
            }
        )

    return JSONResponse(
        {"success": False, "message": "Review row not found."},
        status_code=404,
    )


@app.post("/sessions/{session_id}/review/row/reopen-json")
async def session_reopen_review_row(
    session_id: str,
    row_id: str = Form(""),
) -> JSONResponse:
    load_session(session_id)
    rows = load_reviewed_rows(session_id)
    for row in rows:
        if str(row.get("row_id") or "") != row_id:
            continue

        row["requires_attention"] = True
        row["review_reason"] = "manually_reopened"
        row["review_status"] = "needs_review"
        row["hr_decision"] = ""
        save_reviewed_rows(session_id, rows)
        return JSONResponse(
            {
                "success": True,
                "message": "Row reopened for review.",
                "row_id": row_id,
                "review_status": "needs_review",
            }
        )

    return JSONResponse(
        {"success": False, "message": "Review row not found."},
        status_code=404,
    )


@app.post("/sessions/{session_id}/review/ai-recheck-row")
async def session_ai_recheck_review_row(
    session_id: str,
    row_id: str = Form(""),
) -> JSONResponse:
    session = load_session(session_id)
    extraction_status = get_extraction_status()
    if not extraction_status["openai_enabled"]:
        return JSONResponse(
            {"success": False, "message": "OpenAI is not configured for real extraction mode."},
            status_code=400,
        )

    rows = load_reviewed_rows(session_id)
    target_row = None
    for row in rows:
        if str(row.get("row_id") or "") == row_id:
            target_row = row
            break

    if target_row is None:
        return JSONResponse({"success": False, "message": "Review row not found."}, status_code=404)
    if not row_is_unresolved_for_ai(target_row):
        return JSONResponse(
            {"success": False, "message": "Only rows requiring review can be rechecked."},
            status_code=400,
        )

    preprocessed_session_path = str(target_row.get("preprocessed_session_path") or "")
    if not preprocessed_session_path:
        return JSONResponse(
            {"success": False, "message": "No preprocessed image is available for this row."},
            status_code=400,
        )
    if resolve_session_preprocessed_image(session_id, preprocessed_session_path) is None:
        return JSONResponse(
            {"success": False, "message": "Preprocessed image was not found for this row."},
            status_code=400,
        )

    sop_codes = load_sop_codes()
    try:
        processed = await run_in_threadpool(
            run_second_pass_for_row,
            session_id=session_id,
            session=session,
            row=target_row,
            sop_codes=sop_codes,
            persist_auto_fill=False,
        )
    except Exception as exc:
        return JSONResponse(
            {"success": False, "message": str(exc) or "AI recheck failed."},
            status_code=400,
        )

    save_reviewed_rows(session_id, rows)
    return JSONResponse(
        {
            "success": True,
            "message": "AI second-pass recheck complete.",
            "row_id": row_id,
            "result": processed["result"],
            "audit": processed["audit"],
            "auto_confirmed": processed["auto_confirmed"],
            "review_status": str(target_row.get("review_status") or ""),
            "requires_attention": bool(target_row.get("requires_attention")),
            "review_reason": str(target_row.get("review_reason") or ""),
            "updated_fields": processed["updated_fields"],
        }
    )


@app.post("/sessions/{session_id}/review/ai-recheck-batch/start")
async def session_start_ai_recheck_review_batch(session_id: str) -> JSONResponse:
    load_session(session_id)
    extraction_status = get_extraction_status()
    if not extraction_status["openai_enabled"]:
        return JSONResponse(
            {"success": False, "message": "OpenAI is not configured for real extraction mode."},
            status_code=400,
        )

    rows = load_reviewed_rows(session_id)
    batch_run_id = f"ai-batch-{uuid4().hex}"
    summary = build_ai_batch_summary(rows, session_id)
    if summary["total_eligible"] == 0:
        return JSONResponse(
            {
                "success": False,
                "message": "No eligible rows need AI second-pass.",
                "summary": summary,
            },
            status_code=400,
        )

    _prune_batch_runs(AI_BATCH_RUNS)
    AI_BATCH_RUNS[batch_run_id] = {
        "session_id": session_id,
        "status": "queued",
        "message": "AI second-pass batch queued.",
        "cancel_requested": False,
        "summary": summary,
        "rows": [],
    }
    asyncio.create_task(run_ai_second_pass_batch_worker(session_id, batch_run_id))
    return JSONResponse(
        {
            "success": True,
            "message": "AI second-pass batch started.",
            "batch_run_id": batch_run_id,
            "status": "queued",
            "summary": summary,
        }
    )


@app.get("/sessions/{session_id}/review/ai-recheck-batch/{batch_run_id}/status")
async def session_ai_recheck_review_batch_status(session_id: str, batch_run_id: str) -> JSONResponse:
    load_session(session_id)
    payload = batch_state_payload(batch_run_id)
    if not payload["success"] or payload.get("session_id") != session_id:
        return JSONResponse(
            {"success": False, "message": "AI second-pass batch was not found."},
            status_code=404,
        )
    return JSONResponse(payload)


@app.post("/sessions/{session_id}/review/ai-recheck-batch/{batch_run_id}/cancel")
async def session_cancel_ai_recheck_review_batch(session_id: str, batch_run_id: str) -> JSONResponse:
    load_session(session_id)
    state = AI_BATCH_RUNS.get(batch_run_id)
    if not state or state.get("session_id") != session_id:
        return JSONResponse(
            {"success": False, "message": "AI second-pass batch was not found."},
            status_code=404,
        )
    if state.get("status") in {"completed", "cancelled", "failed"}:
        return JSONResponse(batch_state_payload(batch_run_id))
    state["cancel_requested"] = True
    state["status"] = "cancelling"
    state["message"] = "Stopping after current row..."
    return JSONResponse(
        {
            "success": True,
            "message": "Stopping after current row...",
            "batch_run_id": batch_run_id,
            "status": state["status"],
            "summary": state["summary"],
        }
    )


@app.get("/sessions/{session_id}/review/physical-card-crop")
async def session_physical_card_crop(
    session_id: str,
    image_path: str = "",
    date_value: str = "",
    card_number: str = "",
    source_type: str = "",
) -> Response:
    load_session(session_id)
    if source_type != "physical_time_card":
        return JSONResponse(
            {"success": False, "message": "Crop preview not calibrated. Showing full image."},
            status_code=400,
        )

    day = parse_day_number(date_value)
    if day is None:
        return JSONResponse(
            {"success": False, "message": "Crop preview not calibrated. Showing full image."},
            status_code=400,
        )

    safe_card_number = normalize_card_number(card_number, day)
    if safe_card_number == "1" and not 1 <= day <= 15:
        return JSONResponse(
            {"success": False, "message": "Crop preview not calibrated. Showing full image."},
            status_code=400,
        )
    if safe_card_number == "2" and not 16 <= day <= 31:
        return JSONResponse(
            {"success": False, "message": "Crop preview not calibrated. Showing full image."},
            status_code=400,
        )

    sessions_root = get_sessions_directory().resolve()
    session_preprocessed_dir = (sessions_root / session_id / "preprocessed").resolve()
    requested_path = (sessions_root / image_path).resolve()

    try:
        requested_path.relative_to(session_preprocessed_dir)
    except ValueError:
        return JSONResponse(
            {"success": False, "message": "Crop preview not calibrated. Showing full image."},
            status_code=400,
        )

    if not requested_path.is_file():
        return JSONResponse(
            {"success": False, "message": "Crop preview not calibrated. Showing full image."},
            status_code=404,
        )

    template, template_message = find_enabled_crop_template(
        source_type=source_type,
        card_number=safe_card_number,
    )
    if not template:
        return JSONResponse(
            {
                "success": False,
                "message": "Crop preview not calibrated. Showing full image.",
                "details": template_message,
            },
            status_code=400,
        )

    try:
        crop = build_physical_card_crop(requested_path, day, template)
    except Exception:
        return JSONResponse(
            {"success": False, "message": "Crop preview not calibrated. Showing full image."},
            status_code=400,
        )

    return Response(content=crop.getvalue(), media_type="image/jpeg")


@app.post("/sessions/{session_id}/review/live-extraction-test", response_class=HTMLResponse)
async def session_run_live_extraction_test(
    request: Request,
    session_id: str,
    selected_preprocessed_file: str = Form(""),
) -> HTMLResponse:
    session = load_session(session_id)
    extraction_status = get_extraction_status()
    if extraction_status["requested_mode"] != "real_openai":
        return render_review_page(
            request,
            error="Live extraction is disabled. Set AI_EXTRACTION_MODE=real_openai to run a live test.",
            session_id=session_id,
        )
    if not extraction_status["api_key_present"]:
        return render_review_page(
            request,
            error="OpenAI API key is missing. Add OPENAI_API_KEY to .env before running live extraction.",
            session_id=session_id,
        )

    live_extraction_options = build_live_extraction_options(session_id)
    if not live_extraction_options:
        return render_review_page(
            request,
            error="No preprocessed files are available. Upload and preprocess a file first.",
            session_id=session_id,
        )

    if not selected_preprocessed_file:
        return render_review_page(
            request,
            error="Select one preprocessed file before running live extraction.",
            session_id=session_id,
        )

    selected_file = find_live_extraction_option(session_id, selected_preprocessed_file)
    if not selected_file:
        return render_review_page(
            request,
            error="Selected preprocessed file was not found.",
            session_id=session_id,
        )

    try:
        live_rows = await run_in_threadpool(
            run_live_extraction_test,
            session=session,
            workers=load_workers(),
            sop_codes=load_sop_codes(),
            selected_file=selected_file,
        )
    except Exception as exc:
        return render_review_page(
            request,
            error=f"OpenAI live extraction failed: {exc}",
            session_id=session_id,
        )

    merged_rows = _merge_rows(load_reviewed_rows(session_id), live_rows)
    save_reviewed_rows(session_id, merged_rows)
    return render_review_page(
        request,
        rows=merged_rows,
        message="Live extraction test completed for one selected preprocessed file. Review and apply changes before export.",
        session_id=session_id,
    )


@app.post("/sessions/{session_id}/review/live-extraction-batch/start")
async def session_start_live_extraction_batch(session_id: str) -> JSONResponse:
    session = load_session(session_id)
    extraction_status = get_extraction_status()
    if extraction_status["requested_mode"] != "real_openai":
        return JSONResponse(
            {
                "success": False,
                "message": "Live extraction is disabled. Set AI_EXTRACTION_MODE=real_openai to run batch extraction.",
            },
            status_code=400,
        )
    if not extraction_status["api_key_present"]:
        return JSONResponse(
            {
                "success": False,
                "message": "OpenAI API key is missing. Add OPENAI_API_KEY to .env before running batch extraction.",
            },
            status_code=400,
        )

    live_extraction_options = build_live_extraction_options(session_id)
    if not live_extraction_options:
        return JSONResponse(
            {
                "success": False,
                "message": "No eligible preprocessed files are available for batch extraction.",
            },
            status_code=400,
        )

    batch_run_id = f"extraction-batch-{uuid4().hex}"
    _prune_batch_runs(LIVE_EXTRACTION_BATCH_RUNS)
    LIVE_EXTRACTION_BATCH_RUNS[batch_run_id] = {
        "session_id": session["session_id"],
        "status": "queued",
        "message": "Extraction batch queued.",
        "cancel_requested": False,
        "summary": {
            "total_files": len(live_extraction_options),
            "processed": 0,
            "succeeded": 0,
            "failed": 0,
            "skipped": 0,
            "cancelled": 0,
        },
        "results": [],
    }
    asyncio.create_task(run_live_extraction_batch_worker(session_id, batch_run_id))
    return JSONResponse(
        {
            "success": True,
            "message": "Extraction batch started.",
            "batch_run_id": batch_run_id,
            "status": "queued",
            "summary": LIVE_EXTRACTION_BATCH_RUNS[batch_run_id]["summary"],
        }
    )


@app.get("/sessions/{session_id}/review/live-extraction-batch/{batch_run_id}/status")
async def session_live_extraction_batch_status(session_id: str, batch_run_id: str) -> JSONResponse:
    load_session(session_id)
    payload = live_extraction_batch_state_payload(batch_run_id)
    if not payload["success"] or payload.get("session_id") != session_id:
        return JSONResponse(
            {"success": False, "message": "Extraction batch was not found."},
            status_code=404,
        )
    return JSONResponse(payload)


@app.post("/sessions/{session_id}/review/live-extraction-batch/{batch_run_id}/cancel")
async def session_cancel_live_extraction_batch(session_id: str, batch_run_id: str) -> JSONResponse:
    load_session(session_id)
    state = LIVE_EXTRACTION_BATCH_RUNS.get(batch_run_id)
    if not state or state.get("session_id") != session_id:
        return JSONResponse(
            {"success": False, "message": "Extraction batch was not found."},
            status_code=404,
        )
    if state.get("status") in {"completed", "cancelled", "failed"}:
        return JSONResponse(live_extraction_batch_state_payload(batch_run_id))
    state["cancel_requested"] = True
    state["status"] = "cancelling"
    state["message"] = "Stopping after current file..."
    return JSONResponse(
        {
            "success": True,
            "message": "Stopping after current file...",
            "batch_run_id": batch_run_id,
            "status": state["status"],
            "summary": state["summary"],
        }
    )


@app.get("/sessions/{session_id}/export")
async def session_export_excel(request: Request, session_id: str):
    load_session(session_id)
    reviewed_rows = load_reviewed_rows(session_id)
    if not reviewed_rows:
        return render_review_page(
            request,
            error="Review and apply changes before exporting Excel.",
            session_id=session_id,
        )

    force = request.query_params.get("force") == "1"
    if not force:
        unresolved_count = sum(1 for row in reviewed_rows if row.get("requires_attention"))
        if unresolved_count:
            return RedirectResponse(
                url=f"/sessions/{session_id}/review?{urlencode({'export_warning': str(unresolved_count)})}",
                status_code=303,
            )

    export_path = export_reviewed_rows_to_excel(session_id, reviewed_rows)
    return FileResponse(
        export_path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=export_path.name,
    )


@app.get("/sessions/{session_id}/exports/{filename}")
async def session_download_export(session_id: str, filename: str) -> FileResponse:
    load_session(session_id)
    safe_name = Path(filename).name
    exports_dir = get_session_exports_directory(session_id).resolve()
    export_path = (exports_dir / safe_name).resolve()
    try:
        export_path.relative_to(exports_dir)
    except ValueError:
        raise HTTPException(status_code=404)
    if not export_path.is_file():
        raise HTTPException(status_code=404)
    return FileResponse(
        export_path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=safe_name,
    )


@app.get("/upload", response_class=HTMLResponse)
async def upload_page(request: Request) -> HTMLResponse:
    return render_upload_page(request)


@app.post("/upload", response_class=HTMLResponse)
async def upload_files(
    request: Request,
    files: list[UploadFile] = File(default=[]),
    session_id: str | None = None,
) -> HTMLResponse:
    selected_files = [file for file in files if file.filename]
    if not selected_files:
        return render_upload_page(request, error="No file selected.", session_id=session_id)

    result = await save_uploaded_files(selected_files, session_id)
    saved_files = result["saved_files"]
    rejected_files = result["invalid_files"] + result["empty_files"]
    duplicate_files = result["duplicate_files"]
    preprocessing_results = preprocess_uploaded_files(saved_files, session_id)
    preprocessing_failures = [
        item for item in preprocessing_results if item.get("status") == "failed"
    ]

    message = None
    error = None
    if saved_files:
        file_count = len(saved_files)
        failed_count = len(preprocessing_failures)
        if not session_id:
            message = f"Uploaded {file_count} file{'s' if file_count != 1 else ''} successfully."
        elif failed_count:
            message = (
                f"Uploaded {file_count} file{'s' if file_count != 1 else ''}. "
                f"{failed_count} file{'s' if failed_count != 1 else ''} could not be preprocessed."
            )
        else:
            message = f"Uploaded and preprocessed {file_count} file{'s' if file_count != 1 else ''} successfully."
    if rejected_files:
        invalid_count = len(rejected_files)
        error = f"{invalid_count} file{'s were' if invalid_count != 1 else ' was'} not uploaded."
    if duplicate_files:
        duplicate_messages = [str(file["reason"]) for file in duplicate_files]
        duplicate_notice = " ".join(duplicate_messages)
        message = f"{message} {duplicate_notice}" if message else duplicate_notice

    return render_upload_page(
        request,
        message=message,
        error=error,
        invalid_files=rejected_files,
        session_id=session_id,
    )


@app.get("/review", response_class=HTMLResponse)
async def review_page(request: Request) -> HTMLResponse:
    return render_review_page(request)


@app.post("/review", response_class=HTMLResponse)
async def save_review_rows(
    request: Request,
    session_id: str | None = None,
) -> HTMLResponse:
    form = await request.form()
    row_ids = form.getlist("row_id")
    workers = form.getlist("worker")
    dates = form.getlist("date")
    start_times = form.getlist("start_time")
    end_times = form.getlist("end_time")
    hours_worked = form.getlist("hours_worked")
    notes = form.getlist("notes")
    review_reasons = form.getlist("review_reason")
    review_statuses = form.getlist("review_status")
    hr_decisions = form.getlist("hr_decision")
    hr_correction_notes = form.getlist("hr_correction_note")
    extraction_modes = form.getlist("extraction_mode")
    source_original_filenames = form.getlist("source_original_filename")
    source_stored_filenames = form.getlist("source_stored_filename")
    source_paths = form.getlist("source_path")
    source_kinds = form.getlist("source_kind")
    source_can_previews = form.getlist("source_can_preview")
    source_types = form.getlist("source_type")
    source_type_labels = form.getlist("source_type_label")
    preprocessing_statuses = form.getlist("preprocessing_status")
    preprocessing_errors = form.getlist("preprocessing_error")
    preprocessed_filenames = form.getlist("preprocessed_filename")
    preprocessed_paths = form.getlist("preprocessed_path")
    preprocessed_session_paths = form.getlist("preprocessed_session_path")
    preprocessed_file_counts = form.getlist("preprocessed_file_count")
    attention_indexes = set(form.getlist("requires_attention"))

    submitted_rows = []
    for index, row_id in enumerate(row_ids):
        submitted_rows.append(
            {
                "row_id": str(row_id),
                "extraction_mode": str(extraction_modes[index]),
                "worker": str(workers[index]).strip(),
                "date": str(dates[index]).strip(),
                "start_time": str(start_times[index]).strip(),
                "end_time": str(end_times[index]).strip(),
                "hours_worked": str(hours_worked[index]).strip(),
                "notes": str(notes[index]),
                "requires_attention": str(index) in attention_indexes,
                "review_reason": str(review_reasons[index]).strip(),
                "review_status": determine_review_status(
                    {
                        "review_status": str(review_statuses[index]) if index < len(review_statuses) else "",
                        "requires_attention": str(index) in attention_indexes,
                        "review_reason": str(review_reasons[index]).strip(),
                    }
                ),
                "hr_decision": str(hr_decisions[index]).strip() if index < len(hr_decisions) else "",
                "hr_correction_note": str(hr_correction_notes[index]).strip() if index < len(hr_correction_notes) else "",
                "source_original_filename": str(source_original_filenames[index]),
                "source_stored_filename": str(source_stored_filenames[index]),
                "source_path": str(source_paths[index]),
                "source_kind": str(source_kinds[index]),
                "source_can_preview": source_can_previews[index] == "true",
                "source_type": str(source_types[index]),
                "source_type_label": str(source_type_labels[index]),
                "preprocessing_status": str(preprocessing_statuses[index]),
                "preprocessing_error": str(preprocessing_errors[index]),
                "preprocessed_filename": str(preprocessed_filenames[index]),
                "preprocessed_path": str(preprocessed_paths[index]),
                "preprocessed_session_path": str(preprocessed_session_paths[index]),
                "preprocessed_file_count": str(preprocessed_file_counts[index]),
            }
        )

    rows = submitted_rows
    if session_id:
        existing_rows = load_reviewed_rows(session_id)
        submitted_by_id = {str(row["row_id"]): row for row in submitted_rows}
        rows = []
        for existing_row in existing_rows:
            merged_row = submitted_by_id.get(str(existing_row.get("row_id") or ""))
            if merged_row is None:
                rows.append(existing_row)
                continue
            for field_name in AI_AUDIT_FIELDS:
                if field_name in existing_row:
                    merged_row[field_name] = existing_row[field_name]
            rows.append(merged_row)
        existing_ids = {str(row.get("row_id") or "") for row in existing_rows}
        rows.extend(
            row for row in submitted_rows
            if str(row.get("row_id") or "") not in existing_ids
        )
        save_reviewed_rows(session_id, rows)

    message = "Review changes applied."
    if session_id:
        message = "Review changes saved. Excel export is now available."

    return render_review_page(
        request,
        rows=rows,
        message=message,
        session_id=session_id,
    )


@app.get("/workers", response_class=HTMLResponse)
async def workers_page(request: Request) -> HTMLResponse:
    return render_workers_page(request)


@app.post("/workers/add", response_class=HTMLResponse)
async def add_worker(
    request: Request,
    name: str = Form(""),
    worker_type: str = Form(...),
    session_id: str | None = None,
) -> HTMLResponse:
    workers = load_workers()
    worker_name = name.strip()
    if not worker_name:
        return render_workers_page(
            request,
            workers=workers,
            error="Worker name cannot be blank.",
            session_id=session_id,
        )
    if worker_type not in WORKER_TYPES:
        return render_workers_page(
            request,
            workers=workers,
            error="Worker type must be Full-time or Part-time.",
            session_id=session_id,
        )
    if normalize_unique_value(worker_name) in {
        normalize_unique_value(worker["name"]) for worker in workers
    }:
        return render_workers_page(
            request,
            workers=workers,
            error="Worker already exists.",
            session_id=session_id,
        )

    workers.append({"name": worker_name, "worker_type": worker_type})
    save_workers(workers)
    return render_workers_page(request, workers=workers, message="Worker saved.", session_id=session_id)


@app.post("/workers/save", response_class=HTMLResponse)
async def update_workers(
    request: Request,
    session_id: str | None = None,
) -> HTMLResponse:
    form = await request.form()
    names = form.getlist("name")
    worker_types = form.getlist("worker_type")
    delete_indexes = set(form.getlist("delete_index"))

    workers = []
    worker_names = set()
    for index, name in enumerate(names):
        if str(index) in delete_indexes:
            continue

        worker_name = str(name).strip()
        worker_type = str(worker_types[index]).strip()
        if not worker_name:
            return render_workers_page(
                request,
                workers=load_workers(),
                error="Worker name cannot be blank.",
                session_id=session_id,
            )
        if worker_type not in WORKER_TYPES:
            return render_workers_page(
                request,
                workers=load_workers(),
                error="Worker type must be Full-time or Part-time.",
                session_id=session_id,
            )

        normalized_worker_name = normalize_unique_value(worker_name)
        if normalized_worker_name in worker_names:
            continue
        worker_names.add(normalized_worker_name)
        workers.append({"name": worker_name, "worker_type": worker_type})

    save_workers(workers)
    return render_workers_page(request, workers=workers, message="Worker list saved.", session_id=session_id)


@app.get("/sop-codes", response_class=HTMLResponse)
async def sop_codes_page(request: Request) -> HTMLResponse:
    return render_sop_codes_page(request)


@app.post("/sop-codes/add", response_class=HTMLResponse)
async def add_sop_code(
    request: Request,
    code: str = Form(""),
    meaning: str = Form(""),
    session_id: str | None = None,
) -> HTMLResponse:
    sop_codes = load_sop_codes()
    sop_code = code.strip().upper()
    sop_meaning = meaning.strip()
    if not sop_code or not sop_meaning:
        return render_sop_codes_page(
            request,
            sop_codes=sop_codes,
            error="SOP code and meaning cannot be blank.",
            session_id=session_id,
        )
    if sop_base_code_exists(sop_code, sop_codes):
        return render_sop_codes_page(
            request,
            sop_codes=sop_codes,
            error="SOP code already exists.",
            session_id=session_id,
        )

    sop_codes.append({"code": sop_code, "meaning": sop_meaning})
    save_sop_codes(sop_codes)
    return render_sop_codes_page(request, sop_codes=sop_codes, message="SOP code saved.", session_id=session_id)


@app.post("/sop-codes/save", response_class=HTMLResponse)
async def update_sop_codes(
    request: Request,
    session_id: str | None = None,
) -> HTMLResponse:
    form = await request.form()
    codes = form.getlist("code")
    meanings = form.getlist("meaning")
    delete_indexes = set(form.getlist("delete_index"))

    sop_codes = []
    sop_code_values = set()
    for index, code in enumerate(codes):
        if str(index) in delete_indexes:
            continue

        sop_code = str(code).strip().upper()
        sop_meaning = str(meanings[index]).strip()
        if not sop_code or not sop_meaning:
            return render_sop_codes_page(
                request,
                sop_codes=load_sop_codes(),
                error="SOP code and meaning cannot be blank.",
                session_id=session_id,
            )

        normalized_sop_code = normalize_unique_value(sop_code)
        if normalized_sop_code in sop_code_values:
            continue
        sop_code_values.add(normalized_sop_code)
        sop_codes.append({"code": sop_code, "meaning": sop_meaning})

    save_sop_codes(sop_codes)
    return render_sop_codes_page(
        request,
        sop_codes=sop_codes,
        message="SOP code list saved.",
        session_id=session_id,
    )


# Railway terminates TLS at its edge and forwards to this container over
# plain HTTP; without this, Starlette sees every request as http:// and
# url_for() emits http:// asset links, which browsers block as mixed
# content on an https:// page. Trusted for all hosts because the container
# is only reachable through Railway's edge, never directly from the internet.
app = ProxyHeadersMiddleware(app, trusted_hosts="*")
