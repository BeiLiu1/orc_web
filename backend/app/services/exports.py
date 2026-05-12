from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

import pandas as pd

from app.core.config import EXPORT_DIR
from app.db.database import db_session
from app.services.jobs import get_job


def create_export(job_id: str) -> dict:
    job = get_job(job_id)
    export_id = str(uuid.uuid4())
    created_at = datetime.now(timezone.utc).isoformat()
    filename = f"invoice-ocr-{job_id[:8]}.xlsx"
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    stored_path = EXPORT_DIR / f"{export_id}.xlsx"

    summary_rows = []
    detail_rows = []
    for group in job["groups"]:
        summary_rows.append(
            {
                "颜色组": group["display_name"],
                "颜色值": group["color_hex"],
                "含税金额合计": group["amount_total"],
                "税费合计": group["tax_total"],
                "含税金额计算式": group["formula_amount"],
                "税费计算式": group["formula_tax"],
            }
        )
        for index, item in enumerate(group["items"], start=1):
            detail_rows.append(
                {
                    "颜色组": group["display_name"],
                    "序号": index,
                    "图片名": find_image_name(job, item["image_file_id"]),
                    "原始识别文本": item["raw_text"],
                    "含税金额": item["amount"],
                    "税费": item["tax"],
                    "是否人工新增": "是" if item["is_manual"] else "否",
                    "是否人工修改": "是" if item["is_corrected"] else "否",
                    "框坐标": format_bbox(item),
                }
            )

    with pd.ExcelWriter(stored_path, engine="openpyxl") as writer:
        pd.DataFrame(summary_rows).to_excel(writer, sheet_name="汇总", index=False)
        pd.DataFrame(detail_rows).to_excel(writer, sheet_name="明细", index=False)

    with db_session() as conn:
        conn.execute(
            """
            INSERT INTO exports (id, job_id, filename, stored_path, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (export_id, job_id, filename, str(stored_path), created_at),
        )

    return {"id": export_id, "filename": filename, "created_at": created_at}


def get_export(export_id: str) -> dict:
    with db_session() as conn:
        row = conn.execute("SELECT * FROM exports WHERE id = ?", (export_id,)).fetchone()
    if row is None:
        raise KeyError("导出文件不存在")
    return dict(row)


def find_image_name(job: dict, image_file_id: Optional[str]) -> str:
    if image_file_id is None:
        return ""
    for image in job["images"]:
        if image["id"] == image_file_id:
            return image["original_name"]
    return ""


def format_bbox(item: dict) -> str:
    values = [item.get("bbox_x"), item.get("bbox_y"), item.get("bbox_w"), item.get("bbox_h")]
    if any(value is None for value in values):
        return ""
    return f'{item["bbox_x"]},{item["bbox_y"]},{item["bbox_w"]},{item["bbox_h"]}'
