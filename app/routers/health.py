from fastapi import APIRouter, Depends

from app.config import Settings, get_settings
from app.models.schemas import HealthResponse
from ml.inference import InferenceEngine, get_engine

router = APIRouter(tags=["health"])


def _engine(settings: Settings = Depends(get_settings)) -> InferenceEngine:
    return get_engine(settings.models_dir)


@router.get("/health", response_model=HealthResponse)
def health(settings: Settings = Depends(get_settings), engine: InferenceEngine = Depends(_engine)):
    return HealthResponse(status="ok", models_loaded=engine.ready)
