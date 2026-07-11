import json
import os
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any


def _data_root() -> Path:
    return Path(os.getenv("DATA_DIR", "."))


SESSIONS_DIR = _data_root() / "sessions"

_SESSION_ID_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


class SessionNotFoundError(Exception):
    pass


def is_valid_session_id(session_id: str) -> bool:
    return bool(_SESSION_ID_RE.fullmatch(session_id))


def build_session_id(year: int, month: int) -> str:
    return f"{year:04d}-{month:02d}"


def get_sessions_directory() -> Path:
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    return SESSIONS_DIR


def get_session_directory(session_id: str) -> Path:
    return get_sessions_directory() / session_id


def get_session_upload_directory(session_id: str) -> Path:
    return get_session_directory(session_id) / "uploads"


def get_session_preprocessed_directory(session_id: str) -> Path:
    preprocessed_dir = get_session_directory(session_id) / "preprocessed"
    preprocessed_dir.mkdir(parents=True, exist_ok=True)
    return preprocessed_dir


def get_session_review_directory(session_id: str) -> Path:
    review_dir = get_session_directory(session_id) / "review"
    review_dir.mkdir(parents=True, exist_ok=True)
    return review_dir


def get_session_exports_directory(session_id: str) -> Path:
    exports_dir = get_session_directory(session_id) / "exports"
    exports_dir.mkdir(parents=True, exist_ok=True)
    return exports_dir


def get_reviewed_rows_path(session_id: str) -> Path:
    return get_session_review_directory(session_id) / "reviewed_rows.json"


def load_reviewed_rows(session_id: str) -> list[dict[str, Any]]:
    reviewed_rows_path = get_reviewed_rows_path(session_id)
    if not reviewed_rows_path.exists():
        return []

    data = json.loads(reviewed_rows_path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        return []

    return [item for item in data if isinstance(item, dict)]


def save_reviewed_rows(session_id: str, rows: list[dict[str, Any]]) -> None:
    reviewed_rows_path = get_reviewed_rows_path(session_id)
    tmp_path = reviewed_rows_path.with_suffix(".tmp")
    tmp_path.write_text(
        json.dumps(rows, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    tmp_path.replace(reviewed_rows_path)


def ensure_session(year: int, month: int) -> dict[str, str | int]:
    session_id = build_session_id(year, month)
    session_dir = get_session_directory(session_id)
    uploads_dir = session_dir / "uploads"
    preprocessed_dir = session_dir / "preprocessed"
    review_dir = session_dir / "review"
    exports_dir = session_dir / "exports"
    uploads_dir.mkdir(parents=True, exist_ok=True)
    preprocessed_dir.mkdir(parents=True, exist_ok=True)
    review_dir.mkdir(parents=True, exist_ok=True)
    exports_dir.mkdir(parents=True, exist_ok=True)

    metadata_path = session_dir / "session.json"
    if metadata_path.exists():
        return load_session(session_id)

    now = datetime.now().isoformat(timespec="seconds")
    session = {
        "session_id": session_id,
        "year": year,
        "month": month,
        "status": "In Progress",
        "created_at": now,
        "updated_at": now,
    }
    metadata_path.write_text(json.dumps(session, indent=2), encoding="utf-8")
    return session


def load_session(session_id: str) -> dict[str, str | int]:
    if not is_valid_session_id(session_id):
        raise SessionNotFoundError(f"Invalid session_id: {session_id!r}")
    metadata_path = get_session_directory(session_id) / "session.json"
    if not metadata_path.exists():
        raise SessionNotFoundError(f"Session not found: {session_id!r}")
    return json.loads(metadata_path.read_text(encoding="utf-8"))


def delete_session(session_id: str) -> dict[str, str | int]:
    # load_session guards the rmtree: it rejects anything that is not a
    # valid YYYY-MM id (no traversal) and raises if the session is absent.
    session = load_session(session_id)
    shutil.rmtree(get_session_directory(session_id))
    return session


def list_sessions() -> list[dict[str, str | int]]:
    sessions = []
    sessions_dir = get_sessions_directory()
    for path in sorted(sessions_dir.iterdir(), reverse=True):
        if not path.is_dir():
            continue
        metadata_path = path / "session.json"
        if not metadata_path.exists():
            continue
        sessions.append(json.loads(metadata_path.read_text(encoding="utf-8")))
    return sessions
