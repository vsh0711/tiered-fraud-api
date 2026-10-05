from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import PlainTextResponse

from app.api.deps import get_engine_dep, require_user
from app.config import Settings, get_settings
from app.db.models import User
from app.services.eval_report import (
    build_capture_report,
    build_capture_report_from_upload,
    load_capture_report,
    persist_capture_report,
    sample_holdout_csv,
)
from ml.inference import InferenceEngine

router = APIRouter(prefix="/eval", tags=["eval"])


@router.get("/capture-report")
async def get_capture_report(_: User = Depends(require_user)):
    report = load_capture_report()
    if report is None:
        raise HTTPException(
            status_code=404,
            detail="No report yet; upload a CSV or POST /v1/eval/capture-report",
        )
    return report


@router.post("/capture-report")
async def run_capture_report(
    n_samples: int = Query(1200, ge=200, le=5000),
    _: User = Depends(require_user),
    engine: InferenceEngine = Depends(get_engine_dep),
    settings: Settings = Depends(get_settings),
):
    report = build_capture_report(engine, settings, n_samples=n_samples)
    persist_capture_report(report)
    return report


@router.post("/capture-report/upload")
async def upload_capture_report(
    file: UploadFile = File(..., description="CSV with labeled transactions"),
    _: User = Depends(require_user),
    engine: InferenceEngine = Depends(get_engine_dep),
    settings: Settings = Depends(get_settings),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing filename")
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty file")
    try:
        report = build_capture_report_from_upload(content, file.filename, engine, settings)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    persist_capture_report(report)
    return report


@router.get("/holdout-template.csv")
async def holdout_template(_: User = Depends(require_user)):
    csv_text = sample_holdout_csv(n_samples=80, seed=42)
    return PlainTextResponse(
        content=csv_text,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=holdout_template.csv"},
    )
