#!/usr/bin/env python3
"""Seed demo score history for the dashboard (with realistic decision mix)."""

from __future__ import annotations

import argparse
import asyncio
import uuid

from sqlalchemy import text

from app.config import get_settings
from app.db.session import async_session_factory, init_db
from app.models.schemas import RoutingMode, TransactionRequest
from app.services.bootstrap import ensure_bootstrap_data
from app.services.scoring import score_and_persist
from app.services.thresholds import apply_trained_thresholds
from ml.inference import get_engine, reset_engine
from sim.generator import GeneratorConfig, generate_transactions, row_to_request_dict


async def main(n: int = 200, reset: bool = False) -> None:
    settings = apply_trained_thresholds(get_settings())
    await init_db()
    await ensure_bootstrap_data(settings)
    reset_engine()
    engine = get_engine(settings.models_dir)
    if not engine.ready:
        engine.load()

    async with async_session_factory() as db:
        if reset:
            await db.execute(text("TRUNCATE score_events RESTART IDENTITY CASCADE"))
            await db.commit()
            print("Cleared score_events")

        df = generate_transactions(
            GeneratorConfig(n_samples=n, seed=21, fraud_rate_target=0.045)
        )
        for i, row in df.iterrows():
            body = TransactionRequest(
                **row_to_request_dict(row, request_id=f"seed_{uuid.uuid4().hex[:12]}")
            )
            mode = RoutingMode.optimized if i % 2 == 0 else RoutingMode.baseline
            await score_and_persist(
                body=body, mode=mode, engine=engine, settings=settings, db=db
            )
    print(f"Seeded {n} score events")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-n", type=int, default=200)
    parser.add_argument("--reset", action="store_true", help="Truncate score_events first")
    args = parser.parse_args()
    asyncio.run(main(n=args.n, reset=args.reset))
