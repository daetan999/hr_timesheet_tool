from pathlib import Path
from uuid import uuid4
import hashlib
import json
import os
import re

from fastapi import UploadFile

from services.session_store import get_session_preprocessed_directory, get_session_upload_directory


def _data_root() -> Path:
    return Path(os.getenv("DATA_DIR", "."))


UPLOAD_DIR = _data_root() / "uploads"
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".heic", ".pdf"}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".heic"}
PDF_EXTENSION = ".pdf"
PREPROCESSING_MANIFEST_FILENAME = "preprocessing_manifest.json"
MAX_IMAGE_DIMENSION = 2400
JPEG_QUALITY = 92
MAX_UPLOAD_BYTES = 50 * 1024 * 1024
SOURCE_TYPE_LABELS = {
    "physical_time_card": "Physical Time Card",
    "multi_worker_attendance_table": "Multi Worker Attendance Table",
    "pdf_or_excel_style": "PDF / Excel Style",
    "unknown": "Unknown",
}
MULTI_WORKER_HINTS = {
    "attendance",
    "attendence",
    "table",
    "roster",
    "summary",
    "workers",
    "multi",
    "multiple",
}
PHYSICAL_CARD_HINTS = {
    "card",
    "timecard",
    "time-card",
    "stamp",
    "stamped",
    "photo",
    "image",
    "front",
    "back",
}
PDF_EXCEL_HINTS = {
    "excel",
    "xlsx",
    "xls",
    "pdf",
    "print",
    "printed",
    "export",
}


def get_upload_directory() -> Path:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    return UPLOAD_DIR


def resolve_upload_directory(session_id: str | None = None) -> Path:
    if session_id:
        upload_dir = get_session_upload_directory(session_id)
        upload_dir.mkdir(parents=True, exist_ok=True)
        return upload_dir
    return get_upload_directory()


def is_allowed_file(filename: str) -> bool:
    return Path(filename).suffix.lower() in ALLOWED_EXTENSIONS


def build_stored_filename(original_filename: str) -> str:
    return f"{uuid4().hex}_{Path(original_filename).name}"


def get_original_filename_from_stored_name(stored_filename: str) -> str:
    if "_" not in stored_filename:
        return stored_filename
    return stored_filename.split("_", 1)[1]


def classify_source_file(filename: str) -> str:
    """Conservative source type classification for mock extraction routing."""
    path = Path(filename)
    extension = path.suffix.lower()
    normalized_name = path.stem.lower().replace("_", " ").replace("-", " ")
    compact_name = normalized_name.replace(" ", "")

    if any(hint in normalized_name or hint in compact_name for hint in MULTI_WORKER_HINTS):
        return "multi_worker_attendance_table"

    if extension == ".pdf" or any(
        hint in normalized_name or hint in compact_name for hint in PDF_EXCEL_HINTS
    ):
        return "pdf_or_excel_style"

    if extension in IMAGE_EXTENSIONS and any(
        hint in normalized_name or hint in compact_name for hint in PHYSICAL_CARD_HINTS
    ):
        return "physical_time_card"

    if extension in IMAGE_EXTENSIONS:
        return "physical_time_card"

    return "unknown"


def get_source_type_label(source_type: str) -> str:
    return SOURCE_TYPE_LABELS.get(source_type, SOURCE_TYPE_LABELS["unknown"])


def calculate_file_hash(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def calculate_path_hash(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def build_existing_upload_hashes(upload_dir: Path) -> set[str]:
    hashes = set()
    for path in upload_dir.iterdir():
        if not path.is_file():
            continue
        try:
            hashes.add(calculate_path_hash(path))
        except OSError:
            continue
    return hashes


def get_preprocessing_manifest_path(session_id: str) -> Path:
    return get_session_preprocessed_directory(session_id) / PREPROCESSING_MANIFEST_FILENAME


def load_preprocessing_manifest(session_id: str | None = None) -> list[dict[str, object]]:
    if not session_id:
        return []

    manifest_path = get_preprocessing_manifest_path(session_id)
    if not manifest_path.exists():
        return []

    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    if not isinstance(data, list):
        return []

    return [item for item in data if isinstance(item, dict)]


def save_preprocessing_manifest(session_id: str, manifest: list[dict[str, object]]) -> None:
    manifest_path = get_preprocessing_manifest_path(session_id)
    tmp_path = manifest_path.with_suffix(".tmp")
    tmp_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    tmp_path.replace(manifest_path)


def get_preprocessing_manifest_by_upload(
    session_id: str | None = None,
) -> dict[str, dict[str, object]]:
    return {
        str(item.get("stored_filename", "")): item
        for item in load_preprocessing_manifest(session_id)
        if item.get("stored_filename")
    }


def build_preprocessed_filename(
    stored_filename: str,
    *,
    page_number: int | None = None,
) -> str:
    path = Path(stored_filename)
    stem = re.sub(r"[^A-Za-z0-9._-]+", "_", path.stem).strip("._-")
    if not stem:
        stem = uuid4().hex
    if page_number is not None:
        return f"{stem}_page_{page_number}.jpg"
    return f"{stem}.jpg"


def build_preprocessed_file_metadata(
    path: Path,
    *,
    session_id: str,
    page_number: int | None = None,
) -> dict[str, str | int | None]:
    return {
        "filename": path.name,
        "path": str(path),
        "session_relative_path": f"{session_id}/preprocessed/{path.name}",
        "size_kb": f"{path.stat().st_size / 1024:.1f}",
        "page_number": page_number,
    }


def normalize_pillow_image(image):
    from PIL import Image, ImageOps

    image = ImageOps.exif_transpose(image)
    if max(image.size) > MAX_IMAGE_DIMENSION:
        image.thumbnail((MAX_IMAGE_DIMENSION, MAX_IMAGE_DIMENSION), Image.Resampling.LANCZOS)

    if image.mode in {"RGBA", "LA"} or (
        image.mode == "P" and "transparency" in image.info
    ):
        background = Image.new("RGB", image.size, (255, 255, 255))
        alpha = image.convert("RGBA").getchannel("A")
        background.paste(image.convert("RGBA"), mask=alpha)
        return background

    if image.mode != "RGB":
        return image.convert("RGB")

    return image


def preprocess_image_file(
    source_path: Path,
    output_dir: Path,
    *,
    session_id: str,
) -> list[dict[str, str | int | None]]:
    from PIL import Image

    if source_path.suffix.lower() == ".heic":
        from pillow_heif import register_heif_opener

        register_heif_opener()

    output_path = output_dir / build_preprocessed_filename(source_path.name)
    with Image.open(source_path) as image:
        normalized_image = normalize_pillow_image(image)
        normalized_image.save(output_path, format="JPEG", quality=JPEG_QUALITY, optimize=True)

    return [build_preprocessed_file_metadata(output_path, session_id=session_id)]


def preprocess_pdf_file(
    source_path: Path,
    output_dir: Path,
    *,
    session_id: str,
) -> list[dict[str, str | int | None]]:
    import fitz
    from PIL import Image

    preprocessed_files = []
    with fitz.open(source_path) as document:
        if document.page_count == 0:
            raise ValueError("PDF has no pages.")

        for page_index in range(document.page_count):
            page = document.load_page(page_index)
            pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
            image = Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)
            normalized_image = normalize_pillow_image(image)
            output_path = output_dir / build_preprocessed_filename(
                source_path.name,
                page_number=page_index + 1,
            )
            normalized_image.save(
                output_path,
                format="JPEG",
                quality=JPEG_QUALITY,
                optimize=True,
            )
            preprocessed_files.append(
                build_preprocessed_file_metadata(
                    output_path,
                    session_id=session_id,
                    page_number=page_index + 1,
                )
            )

    return preprocessed_files


def build_preprocessing_manifest_entry(
    *,
    uploaded_file: dict[str, str],
    session_id: str,
) -> dict[str, object]:
    source_path = Path(uploaded_file["path"])
    output_dir = get_session_preprocessed_directory(session_id)
    source_type = uploaded_file.get("source_type") or classify_source_file(
        uploaded_file["original_filename"]
    )

    entry: dict[str, object] = {
        "original_filename": uploaded_file["original_filename"],
        "stored_filename": uploaded_file["stored_filename"],
        "source_path": uploaded_file["path"],
        "file_hash": uploaded_file.get("file_hash", ""),
        "file_status": uploaded_file.get("file_status", "active"),
        "source_type": source_type,
        "source_type_label": get_source_type_label(str(source_type)),
        "status": "success",
        "error": "",
        "preprocessed_files": [],
    }

    try:
        extension = source_path.suffix.lower()
        if extension == PDF_EXTENSION:
            preprocessed_files = preprocess_pdf_file(source_path, output_dir, session_id=session_id)
        elif extension in IMAGE_EXTENSIONS:
            preprocessed_files = preprocess_image_file(source_path, output_dir, session_id=session_id)
        else:
            raise ValueError("Unsupported file type for preprocessing.")

        entry["preprocessed_files"] = preprocessed_files
    except Exception as exc:
        entry["status"] = "failed"
        entry["error"] = f"{type(exc).__name__}: {exc}"

    return entry


def preprocess_uploaded_files(
    saved_files: list[dict[str, str]],
    session_id: str | None = None,
) -> list[dict[str, object]]:
    if not session_id or not saved_files:
        return []

    existing_manifest = load_preprocessing_manifest(session_id)
    retained_entries = [
        item
        for item in existing_manifest
        if item.get("stored_filename") not in {file["stored_filename"] for file in saved_files}
    ]
    new_entries = [
        build_preprocessing_manifest_entry(uploaded_file=file, session_id=session_id)
        for file in saved_files
    ]
    manifest = retained_entries + new_entries
    save_preprocessing_manifest(session_id, manifest)
    return new_entries


def build_file_metadata(path: Path) -> dict[str, str]:
    file_hash = ""
    try:
        file_hash = calculate_path_hash(path)
    except OSError:
        pass

    source_type = classify_source_file(get_original_filename_from_stored_name(path.name))
    return {
        "original_filename": get_original_filename_from_stored_name(path.name),
        "stored_filename": path.name,
        "path": str(path),
        "size_kb": f"{path.stat().st_size / 1024:.1f}",
        "file_hash": file_hash,
        "file_status": "active",
        "source_type": source_type,
        "source_type_label": get_source_type_label(source_type),
    }


async def save_uploaded_files(
    files: list[UploadFile],
    session_id: str | None = None,
) -> dict[str, list[dict[str, str]]]:
    upload_dir = resolve_upload_directory(session_id)
    saved_files = []
    invalid_files = []
    empty_files = []
    duplicate_files = []
    existing_hashes = build_existing_upload_hashes(upload_dir)

    for file in files:
        original_filename = Path(file.filename or "").name
        if not original_filename:
            empty_files.append({"filename": "Unnamed file", "reason": "No file selected."})
            continue

        if not is_allowed_file(original_filename):
            invalid_files.append(
                {
                    "filename": original_filename,
                    "reason": "Unsupported file type.",
                }
            )
            continue

        stored_filename = build_stored_filename(original_filename)
        saved_path = upload_dir / stored_filename
        content = await file.read()
        if not content:
            empty_files.append({"filename": original_filename, "reason": "File is empty."})
            continue

        if len(content) > MAX_UPLOAD_BYTES:
            invalid_files.append(
                {
                    "filename": original_filename,
                    "reason": f"File too large (max {MAX_UPLOAD_BYTES // (1024 * 1024)} MB).",
                }
            )
            continue

        file_hash = calculate_file_hash(content)
        if session_id and file_hash in existing_hashes:
            duplicate_files.append(
                {
                    "filename": original_filename,
                    "reason": f"Duplicate file skipped: {original_filename}",
                }
            )
            continue

        saved_path.write_bytes(content)
        existing_hashes.add(file_hash)
        source_type = classify_source_file(original_filename)
        saved_files.append(
            {
                "original_filename": original_filename,
                "stored_filename": stored_filename,
                "path": str(saved_path),
                "file_hash": file_hash,
                "file_status": "active",
                "source_type": source_type,
                "source_type_label": get_source_type_label(source_type),
            }
        )

    return {
        "saved_files": saved_files,
        "invalid_files": invalid_files,
        "empty_files": empty_files,
        "duplicate_files": duplicate_files,
    }


def delete_uploaded_file(session_id: str, stored_filename: str) -> dict[str, object]:
    safe_stored_filename = Path(stored_filename).name
    upload_path = get_session_upload_directory(session_id) / safe_stored_filename
    preprocessed_dir = get_session_preprocessed_directory(session_id)
    manifest = load_preprocessing_manifest(session_id)
    manifest_entry = next(
        (
            item
            for item in manifest
            if item.get("stored_filename") == safe_stored_filename
        ),
        None,
    )

    deleted_preprocessed_files = []
    if manifest_entry:
        preprocessed_files = manifest_entry.get("preprocessed_files", [])
        if isinstance(preprocessed_files, list):
            for preprocessed_file in preprocessed_files:
                if not isinstance(preprocessed_file, dict):
                    continue

                filename = str(preprocessed_file.get("filename") or "")
                path = str(preprocessed_file.get("path") or "")
                preprocessed_filename = Path(filename or path).name
                if not preprocessed_filename:
                    continue

                preprocessed_path = preprocessed_dir / preprocessed_filename
                if preprocessed_path.exists():
                    preprocessed_path.unlink()
                    deleted_preprocessed_files.append(preprocessed_filename)
    else:
        fallback_stem = Path(build_preprocessed_filename(safe_stored_filename)).stem
        for preprocessed_path in preprocessed_dir.glob(f"{fallback_stem}*.jpg"):
            if preprocessed_path.is_file():
                preprocessed_path.unlink()
                deleted_preprocessed_files.append(preprocessed_path.name)

    upload_deleted = False
    if upload_path.exists() and upload_path.is_file():
        upload_path.unlink()
        upload_deleted = True

    updated_manifest = [
        item
        for item in manifest
        if item.get("stored_filename") != safe_stored_filename
    ]
    if len(updated_manifest) != len(manifest):
        save_preprocessing_manifest(session_id, updated_manifest)

    return {
        "upload_deleted": upload_deleted,
        "deleted_preprocessed_files": deleted_preprocessed_files,
        "manifest_updated": len(updated_manifest) != len(manifest),
    }


def list_uploaded_files(session_id: str | None = None) -> list[dict[str, str]]:
    upload_dir = resolve_upload_directory(session_id)
    files = []
    for path in sorted(upload_dir.iterdir(), key=lambda item: item.stat().st_mtime, reverse=True):
        if not path.is_file():
            continue

        files.append(build_file_metadata(path))

    return files
