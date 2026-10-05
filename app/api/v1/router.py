from fastapi import APIRouter

from app.api.v1 import auth, drift, evaluation, health, history, jobs, metrics, score

api_router = APIRouter(prefix="/v1")
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(score.router)
api_router.include_router(history.router)
api_router.include_router(jobs.router)
api_router.include_router(drift.router)
api_router.include_router(evaluation.router)
api_router.include_router(metrics.router)
