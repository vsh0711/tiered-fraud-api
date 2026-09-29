from __future__ import annotations

import time

from app.config import Settings
from app.models.schemas import Decision, RoutingMode, ScoreResponse, TierName, TierResult, TransactionRequest
from ml.inference import InferenceEngine
from or_router.router import cascade_should_stop, decision_from_score, plan_route


def score_transaction(
    req: TransactionRequest,
    mode: RoutingMode,
    engine: InferenceEngine,
    settings: Settings,
) -> ScoreResponse:
    deadline = req.deadline_ms or settings.default_deadline_ms
    tiers_executed: list[TierResult] = []
    cumulative = 0.0
    early_exit = False
    score = 0.15
    or_utility = None
    meta: dict = {}

    if mode == RoutingMode.baseline:
        plan_tiers = [TierName.t0_rules, TierName.t1_fast, TierName.t2_full]
        meta["routing"] = "baseline_always_t2"
    else:
        plan = plan_route(deadline, settings)
        plan_tiers = plan.tiers_to_run
        or_utility = plan.expected_utility
        meta["routing"] = plan.rationale

    for tier in plan_tiers:
        lat_budget = _tier_latency(tier, settings)
        if cumulative + lat_budget > deadline + settings.safety_margin_ms:
            meta["budget_exceeded"] = True
            break

        score, n_feat, sim_latency = _execute_tier(tier, req, engine, settings)
        cumulative += sim_latency
        tiers_executed.append(
            TierResult(tier=tier, score=score, latency_ms=round(sim_latency, 3), features_used=n_feat)
        )

        if mode == RoutingMode.optimized:
            stop, reason = cascade_should_stop(score, settings)
            t0_score = tiers_executed[0].score if tiers_executed else score
            if stop and tier == TierName.t1_fast and abs(t0_score - score) >= 0.35:
                stop = False
                meta["disagreement_guard"] = "t0_t1_mismatch_continue"
            if stop:
                early_exit = True
                meta["early_exit_reason"] = reason
                break
            # If still ambiguous and T2 fits budget, extend plan dynamically
            if (
                tier == TierName.t1_fast
                and settings.approve_threshold <= score <= settings.decline_threshold
                and TierName.t2_full not in [t.tier for t in tiers_executed]
                and cumulative + settings.tier2_latency_ms <= deadline
            ):
                score2, n2, lat2 = _execute_tier(TierName.t2_full, req, engine, settings)
                cumulative += lat2
                tiers_executed.append(
                    TierResult(
                        tier=TierName.t2_full,
                        score=score2,
                        latency_ms=round(lat2, 3),
                        features_used=n2,
                    )
                )
                score = score2
                break

    if tiers_executed:
        score = tiers_executed[-1].score

    decision = decision_from_score(score, settings)
    return ScoreResponse(
        request_id=req.request_id,
        routing_mode=mode,
        decision=decision,
        fraud_probability=round(score, 6),
        tiers_executed=tiers_executed,
        cumulative_latency_ms=round(cumulative, 3),
        deadline_ms=deadline,
        early_exit=early_exit,
        or_utility=or_utility,
        metadata=meta,
    )


def _tier_latency(tier: TierName, settings: Settings) -> float:
    return {
        TierName.t0_rules: settings.tier0_latency_ms,
        TierName.t1_fast: settings.tier1_latency_ms,
        TierName.t2_full: settings.tier2_latency_ms,
    }[tier]


def _execute_tier(
    tier: TierName,
    req: TransactionRequest,
    engine: InferenceEngine,
    settings: Settings,
) -> tuple[float, int, float]:
    d = req.model_dump()
    t0 = time.perf_counter()
    if tier == TierName.t0_rules:
        score, n_feat = engine.score_t0_rules(d), 6
    elif tier == TierName.t1_fast:
        score, n_feat = engine.score_t1(d)
    else:
        score, n_feat = engine.score_t2(d)
    elapsed_ms = (time.perf_counter() - t0) * 1000
    sim_latency = _tier_latency(tier, settings) * 0.4 + elapsed_ms
    return score, n_feat, sim_latency
