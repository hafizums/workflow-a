from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.core.config import get_settings
from app.routers import assets, health, jobs, model_catalog, models, projects, runs, templates, workflows
from app.services.run_manager import run_manager

settings = get_settings()
ROOT_DIR = Path(__file__).resolve().parents[1]
WEB_DIR = ROOT_DIR / "web"


@asynccontextmanager
async def lifespan(app: FastAPI):
    del app
    await run_manager.start()
    try:
        yield
    finally:
        await run_manager.stop()


app = FastAPI(
    title=settings.app_name,
    description="Codex-ready FastAPI scaffold for a WaveSpeed node-canvas creative workflow app.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(models.router)
app.include_router(model_catalog.router)
app.include_router(projects.router)
app.include_router(assets.router)
app.include_router(runs.router)
app.include_router(workflows.router)
app.include_router(templates.router)
app.include_router(jobs.router)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content=jsonable_encoder({"detail": "Invalid request", "errors": exc.errors()}),
    )

app.mount("/uploads", StaticFiles(directory=settings.upload_dir), name="uploads")
app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")
