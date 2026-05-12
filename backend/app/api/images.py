from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.services.jobs import get_image_file

router = APIRouter(prefix="/images", tags=["images"])


@router.get("/{image_id}")
def preview_image(image_id: str):
    try:
        image = get_image_file(image_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    path = Path(image["stored_path"])
    if not path.exists():
        raise HTTPException(status_code=404, detail="图片文件已清理")

    return FileResponse(path, filename=image["original_name"])
