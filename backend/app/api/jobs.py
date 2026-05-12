from fastapi import APIRouter, File, HTTPException, UploadFile

from app.services.exports import create_export
from app.services.jobs import create_job, delete_job, get_job, list_jobs, replace_job_items

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("/upload")
def upload_images(files: list[UploadFile] = File(...)):
    try:
        return create_job(files)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("")
def jobs():
    return list_jobs()


@router.get("/{job_id}")
def job_detail(job_id: str):
    try:
        return get_job(job_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.put("/{job_id}/items")
def update_items(job_id: str, payload: dict):
    try:
        return replace_job_items(job_id, payload.get("groups", []))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{job_id}/export")
def export_job(job_id: str):
    try:
        return create_export(job_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/{job_id}")
def remove_job(job_id: str):
    delete_job(job_id)
    return {"ok": True}

