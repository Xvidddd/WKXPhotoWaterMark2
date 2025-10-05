from pathlib import Path
import os

APP_DIR_NAME = "WKXPhotoWaterMark2"

def get_app_data_dir() -> Path:
    base = os.environ.get("APPDATA") or str(Path.home())
    return Path(base) / APP_DIR_NAME

def get_templates_dir() -> Path:
    return get_app_data_dir() / "templates"

def get_last_session_file() -> Path:
    return get_app_data_dir() / "last-session.json"

def ensure_dirs() -> None:
    app_dir = get_app_data_dir()
    tpl_dir = get_templates_dir()
    app_dir.mkdir(parents=True, exist_ok=True)
    tpl_dir.mkdir(parents=True, exist_ok=True)