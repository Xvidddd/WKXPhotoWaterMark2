from __future__ import annotations
from pathlib import Path
import json
from typing import Any, Dict, List

from . import normalize_settings_for_save, normalize_settings_for_load
from app.store import ensure_dirs, get_templates_dir, get_last_session_file


def _safe_name(name: str) -> str:
    return "".join(c for c in name.strip() if c not in "\\/:*?\"<>|") or "template"


def save_template(name: str, settings: Dict[str, Any]) -> Path:
    ensure_dirs()
    tpl_dir = get_templates_dir()
    fname = _safe_name(name) + ".json"
    path = tpl_dir / fname
    data = normalize_settings_for_save(settings)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return path


def load_template(name: str) -> Dict[str, Any] | None:
    tpl_dir = get_templates_dir()
    path = tpl_dir / (name + ".json")
    if not path.exists():
        return None
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return normalize_settings_for_load(data)
    except Exception:
        return None


def list_templates() -> List[str]:
    ensure_dirs()
    tpl_dir = get_templates_dir()
    names: List[str] = []
    for p in tpl_dir.glob("*.json"):
        names.append(p.stem)
    return sorted(names)


def rename_template(old_name: str, new_name: str) -> bool:
    tpl_dir = get_templates_dir()
    old = tpl_dir / (old_name + ".json")
    if not old.exists():
        return False
    new = tpl_dir / (_safe_name(new_name) + ".json")
    if new.exists():
        # 若目标已存在，视为失败以避免覆盖
        return False
    old.rename(new)
    return True


def delete_template(name: str) -> bool:
    tpl_dir = get_templates_dir()
    path = tpl_dir / (name + ".json")
    if not path.exists():
        return False
    try:
        path.unlink()
        return True
    except Exception:
        return False


def save_last_session(settings: Dict[str, Any]) -> Path:
    ensure_dirs()
    path = get_last_session_file()
    data = normalize_settings_for_save(settings)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return path


def load_last_session() -> Dict[str, Any] | None:
    path = get_last_session_file()
    if not path.exists():
        return None
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return normalize_settings_for_load(data)
    except Exception:
        return None