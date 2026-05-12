from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.exports import router as exports_router
from app.api.images import router as images_router
from app.api.jobs import router as jobs_router
from app.core.config import ACCESS_TOKEN, APP_NAME, ensure_storage_dirs
from app.db.database import init_db


app = FastAPI(title=APP_NAME)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def access_token_guard(request: Request, call_next):
    if ACCESS_TOKEN and request.method != "OPTIONS" and request.url.path != "/health":
        token = request.headers.get("x-access-token") or request.query_params.get("token")
        if token != ACCESS_TOKEN:
            return JSONResponse(status_code=401, content={"detail": "未授权访问"})
    return await call_next(request)


@app.on_event("startup")
def startup() -> None:
    ensure_storage_dirs()
    init_db()


@app.get("/health")
def health():
    return {"ok": True}


app.include_router(jobs_router, prefix="/api")
app.include_router(exports_router, prefix="/api")
app.include_router(images_router, prefix="/api")
