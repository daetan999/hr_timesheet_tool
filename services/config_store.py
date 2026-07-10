import json
import os
from pathlib import Path
from typing import Any


def _data_root() -> Path:
    return Path(os.getenv("DATA_DIR", "."))


CONFIG_DIR = _data_root() / "config"
WORKERS_FILE = CONFIG_DIR / "workers.json"
SOP_CODES_FILE = CONFIG_DIR / "sop_codes.json"
CROP_TEMPLATES_FILE = CONFIG_DIR / "crop_templates.json"


def _ensure_json_list_file(path: Path) -> None:
    CONFIG_DIR.mkdir(exist_ok=True)
    if not path.exists():
        path.write_text("[]\n", encoding="utf-8")


def _load_list(path: Path) -> list[dict[str, Any]]:
    _ensure_json_list_file(path)
    with path.open(encoding="utf-8") as config_file:
        data = json.load(config_file)

    if not isinstance(data, list):
        return []

    return [item for item in data if isinstance(item, dict)]


def _save_list(path: Path, records: list[dict[str, Any]]) -> None:
    _ensure_json_list_file(path)
    path.write_text(
        json.dumps(records, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _load_dict(path: Path) -> dict[str, Any]:
    CONFIG_DIR.mkdir(exist_ok=True)
    if not path.exists():
        path.write_text("{}\n", encoding="utf-8")
    with path.open(encoding="utf-8") as config_file:
        data = json.load(config_file)

    return data if isinstance(data, dict) else {}


def load_workers() -> list[dict[str, str]]:
    workers = []
    for worker in _load_list(WORKERS_FILE):
        name = str(worker.get("name", "")).strip()
        worker_type = str(worker.get("worker_type", "")).strip()
        if name and worker_type:
            workers.append({"name": name, "worker_type": worker_type})
    return workers


def save_workers(workers: list[dict[str, str]]) -> None:
    _save_list(WORKERS_FILE, workers)


def load_sop_codes() -> list[dict[str, str]]:
    sop_codes = []
    for sop_code in _load_list(SOP_CODES_FILE):
        code = str(sop_code.get("code", "")).strip()
        meaning = str(sop_code.get("meaning", "")).strip()
        if code and meaning:
            sop_codes.append({"code": code, "meaning": meaning})
    return sop_codes


def save_sop_codes(sop_codes: list[dict[str, str]]) -> None:
    _save_list(SOP_CODES_FILE, sop_codes)


def load_crop_templates() -> dict[str, dict[str, Any]]:
    templates = {}
    for key, template in _load_dict(CROP_TEMPLATES_FILE).items():
        if isinstance(template, dict):
            templates[str(key)] = template
    return templates


def normalize_sop_code_value(code: str) -> str:
    return " ".join(code.split()).casefold()


def normalize_sop_code_display(code: str) -> str:
    return " ".join(code.split())


def sop_code_exists(code: str, sop_codes: list[dict[str, str]] | None = None) -> bool:
    normalized_code = normalize_sop_code_value(code)
    if not normalized_code:
        return False

    return normalized_code in {
        normalize_sop_code_value(item["code"])
        for item in sop_codes if item.get("code")
    }
