from __future__ import annotations

import json
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import cv2
from fastapi import UploadFile

from app.core.config import ALLOWED_IMAGE_EXTENSIONS, MAX_UPLOAD_MB, UPLOAD_DIR
from app.db.database import db_session
from app.services.calculation import calculate_group, money
from app.services.ocr import recognize_image


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_job(files: list[UploadFile]) -> dict:
    if not files:
        raise ValueError("请至少上传一张图片")

    job_id = str(uuid.uuid4())
    created_at = now_iso()
    filenames = [file.filename or "unknown" for file in files]

    with db_session() as conn:
        conn.execute(
            """
            INSERT INTO jobs (id, original_filenames, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (job_id, json.dumps(filenames, ensure_ascii=False), "processing", created_at, created_at),
        )

    try:
        for file in files:
            save_and_recognize_file(job_id, file)
        recalculate_job(job_id)
        set_job_status(job_id, "done", None)
    except Exception as exc:
        set_job_status(job_id, "failed", str(exc))
        raise

    return get_job(job_id)


def save_and_recognize_file(job_id: str, file: UploadFile) -> None:
    original_name = file.filename or "image"
    ext = Path(original_name).suffix.lower()
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        raise ValueError(f"不支持的文件类型: {original_name}")

    image_id = str(uuid.uuid4())
    job_dir = UPLOAD_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    stored_path = job_dir / f"{image_id}{ext}"

    size = 0
    max_size = MAX_UPLOAD_MB * 1024 * 1024
    with stored_path.open("wb") as target:
        while True:
            chunk = file.file.read(1024 * 1024)
            if not chunk:
                break
            size += len(chunk)
            if size > max_size:
                raise ValueError(f"文件超过大小限制: {original_name}")
            target.write(chunk)

    img = cv2.imread(str(stored_path))
    if img is None:
        raise ValueError(f"图片无法读取: {original_name}")
    height, width = img.shape[:2]

    with db_session() as conn:
        conn.execute(
            """
            INSERT INTO image_files (id, job_id, original_name, stored_path, width, height, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (image_id, job_id, original_name, str(stored_path), width, height, now_iso()),
        )

    recognition = recognize_image(stored_path, image_id)
    persist_recognition(job_id, recognition["groups"])


def persist_recognition(job_id: str, groups: list[dict]) -> None:
    with db_session() as conn:
        existing_count = conn.execute(
            "SELECT COUNT(*) FROM groups WHERE job_id = ?", (job_id,)
        ).fetchone()[0]
        sort_order = conn.execute(
            "SELECT COUNT(*) FROM items WHERE job_id = ?", (job_id,)
        ).fetchone()[0]

        for index, group in enumerate(groups, start=existing_count + 1):
            group_id = str(uuid.uuid4())
            conn.execute(
                """
                INSERT INTO groups (id, job_id, group_index, display_name, color_hex)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    group_id,
                    job_id,
                    index,
                    f"颜色组 {index}",
                    group.get("color_hex") or "#888888",
                ),
            )
            for item in group.get("items", []):
                sort_order += 1
                conn.execute(
                    """
                    INSERT INTO items (
                        id, job_id, group_id, image_file_id, raw_text, amount, tax,
                        bbox_x, bbox_y, bbox_w, bbox_h, ocr_confidence,
                        is_manual, is_corrected, sort_order
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(uuid.uuid4()),
                        job_id,
                        group_id,
                        item.get("image_file_id"),
                        item.get("raw_text") or "",
                        money(item.get("amount")),
                        money(item.get("tax")),
                        item.get("bbox_x"),
                        item.get("bbox_y"),
                        item.get("bbox_w"),
                        item.get("bbox_h"),
                        item.get("ocr_confidence"),
                        int(bool(item.get("is_manual"))),
                        int(bool(item.get("is_corrected"))),
                        sort_order,
                    ),
                )


def set_job_status(job_id: str, status: str, error_message: Optional[str]) -> None:
    with db_session() as conn:
        conn.execute(
            "UPDATE jobs SET status = ?, error_message = ?, updated_at = ? WHERE id = ?",
            (status, error_message, now_iso(), job_id),
        )


def list_jobs() -> list[dict]:
    with db_session() as conn:
        rows = conn.execute(
            """
            SELECT id, original_filenames, status, created_at, updated_at,
                   amount_total, tax_total, error_message
            FROM jobs
            ORDER BY created_at DESC
            """
        ).fetchall()
        return [job_row_to_dict(row) for row in rows]


def get_job(job_id: str) -> dict:
    with db_session() as conn:
        job = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        if job is None:
            raise KeyError("任务不存在")

        images = conn.execute(
            "SELECT * FROM image_files WHERE job_id = ? ORDER BY created_at", (job_id,)
        ).fetchall()
        groups = conn.execute(
            "SELECT * FROM groups WHERE job_id = ? ORDER BY group_index", (job_id,)
        ).fetchall()
        items = conn.execute(
            "SELECT * FROM items WHERE job_id = ? ORDER BY sort_order, id", (job_id,)
        ).fetchall()

    items_by_group: dict[str, list[dict]] = {}
    for item in items:
        item_dict = item_row_to_dict(item)
        items_by_group.setdefault(item["group_id"], []).append(item_dict)

    return {
        **job_row_to_dict(job),
        "images": [image_row_to_dict(row) for row in images],
        "groups": [
            {**group_row_to_dict(row), "items": items_by_group.get(row["id"], [])}
            for row in groups
        ],
    }


def get_image_file(image_id: str) -> dict:
    with db_session() as conn:
        row = conn.execute("SELECT * FROM image_files WHERE id = ?", (image_id,)).fetchone()
    if row is None:
        raise KeyError("图片不存在")
    return dict(row)


def replace_job_items(job_id: str, groups: list[dict]) -> dict:
    with db_session() as conn:
        job = conn.execute("SELECT id FROM jobs WHERE id = ?", (job_id,)).fetchone()
        if job is None:
            raise KeyError("任务不存在")

        sort_order = 0
        for group in groups:
            group_id = group["id"]
            existing = conn.execute(
                "SELECT id FROM groups WHERE id = ? AND job_id = ?", (group_id, job_id)
            ).fetchone()
            if existing is None:
                raise ValueError(f"颜色组不存在: {group_id}")

            incoming_ids = [item.get("id") for item in group.get("items", []) if item.get("id")]
            if incoming_ids:
                placeholders = ",".join("?" for _ in incoming_ids)
                conn.execute(
                    f"DELETE FROM items WHERE group_id = ? AND id NOT IN ({placeholders})",
                    [group_id, *incoming_ids],
                )
            else:
                conn.execute("DELETE FROM items WHERE group_id = ?", (group_id,))

            for item in group.get("items", []):
                sort_order += 1
                item_id = item.get("id") or str(uuid.uuid4())
                is_manual = bool(item.get("is_manual") or not item.get("id"))
                payload = (
                    item_id,
                    job_id,
                    group_id,
                    item.get("image_file_id"),
                    item.get("raw_text") or "",
                    money(item.get("amount")),
                    money(item.get("tax")),
                    item.get("bbox_x"),
                    item.get("bbox_y"),
                    item.get("bbox_w"),
                    item.get("bbox_h"),
                    item.get("ocr_confidence"),
                    int(is_manual),
                    int(bool(item.get("is_corrected"))),
                    sort_order,
                )
                conn.execute(
                    """
                    INSERT INTO items (
                        id, job_id, group_id, image_file_id, raw_text, amount, tax,
                        bbox_x, bbox_y, bbox_w, bbox_h, ocr_confidence,
                        is_manual, is_corrected, sort_order
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                        raw_text = excluded.raw_text,
                        amount = excluded.amount,
                        tax = excluded.tax,
                        is_manual = excluded.is_manual,
                        is_corrected = excluded.is_corrected,
                        sort_order = excluded.sort_order
                    """,
                    payload,
                )

    recalculate_job(job_id)
    return get_job(job_id)


def recalculate_job(job_id: str) -> None:
    with db_session() as conn:
        groups = conn.execute("SELECT * FROM groups WHERE job_id = ?", (job_id,)).fetchall()
        amount_total = 0.0
        tax_total = 0.0

        for group in groups:
            items = [
                dict(row)
                for row in conn.execute("SELECT amount, tax FROM items WHERE group_id = ?", (group["id"],))
            ]
            totals = calculate_group(items)
            amount_total += totals.amount_total
            tax_total += totals.tax_total
            conn.execute(
                """
                UPDATE groups
                SET amount_total = ?, tax_total = ?, formula_amount = ?, formula_tax = ?
                WHERE id = ?
                """,
                (
                    totals.amount_total,
                    totals.tax_total,
                    totals.formula_amount,
                    totals.formula_tax,
                    group["id"],
                ),
            )

        conn.execute(
            """
            UPDATE jobs
            SET amount_total = ?, tax_total = ?, updated_at = ?
            WHERE id = ?
            """,
            (money(amount_total), money(tax_total), now_iso(), job_id),
        )


def delete_job(job_id: str) -> None:
    job_dir = UPLOAD_DIR / job_id
    with db_session() as conn:
        exports = conn.execute("SELECT stored_path FROM exports WHERE job_id = ?", (job_id,)).fetchall()
        conn.execute("DELETE FROM jobs WHERE id = ?", (job_id,))

    if job_dir.exists():
        shutil.rmtree(job_dir, ignore_errors=True)
    for export in exports:
        Path(export["stored_path"]).unlink(missing_ok=True)


def job_row_to_dict(row) -> dict:
    return {
        "id": row["id"],
        "original_filenames": json.loads(row["original_filenames"]),
        "status": row["status"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "amount_total": money(row["amount_total"]),
        "tax_total": money(row["tax_total"]),
        "error_message": row["error_message"],
    }


def image_row_to_dict(row) -> dict:
    return {
        "id": row["id"],
        "job_id": row["job_id"],
        "original_name": row["original_name"],
        "width": row["width"],
        "height": row["height"],
        "created_at": row["created_at"],
    }


def group_row_to_dict(row) -> dict:
    return {
        "id": row["id"],
        "job_id": row["job_id"],
        "group_index": row["group_index"],
        "display_name": row["display_name"],
        "color_hex": row["color_hex"],
        "amount_total": money(row["amount_total"]),
        "tax_total": money(row["tax_total"]),
        "formula_amount": row["formula_amount"],
        "formula_tax": row["formula_tax"],
    }


def item_row_to_dict(row) -> dict:
    return {
        "id": row["id"],
        "job_id": row["job_id"],
        "group_id": row["group_id"],
        "image_file_id": row["image_file_id"],
        "raw_text": row["raw_text"],
        "amount": money(row["amount"]),
        "tax": money(row["tax"]),
        "bbox_x": row["bbox_x"],
        "bbox_y": row["bbox_y"],
        "bbox_w": row["bbox_w"],
        "bbox_h": row["bbox_h"],
        "ocr_confidence": row["ocr_confidence"],
        "is_manual": bool(row["is_manual"]),
        "is_corrected": bool(row["is_corrected"]),
        "sort_order": row["sort_order"],
    }
