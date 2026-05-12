from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.services.exports import get_export

router = APIRouter(prefix="/exports", tags=["exports"])


@router.get("/{export_id}/download")
def download_export(export_id: str):
    try:
        export = get_export(export_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return FileResponse(
        export["stored_path"],
        filename=export["filename"],
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
