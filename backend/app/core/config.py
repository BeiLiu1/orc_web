import os
from pathlib import Path


APP_NAME = "Invoice OCR Web"
STORAGE_DIR = Path(os.getenv("STORAGE_DIR", "/app/storage"))
DB_PATH = Path(os.getenv("DB_PATH", STORAGE_DIR / "db" / "invoice_ocr.sqlite3"))
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", STORAGE_DIR / "uploads"))
EXPORT_DIR = Path(os.getenv("EXPORT_DIR", STORAGE_DIR / "exports"))
MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "25"))
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN", "")

ALLOWED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg"}


def ensure_storage_dirs() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
