"""Operations-research routing: knapsack-on-depth with latency budget."""

from __future__ import annotations

from dataclasses import dataclass

from app.config import Settings
from app.models.schemas import Decision, TierName


@dataclass(frozen=True)
class TierSpec:
    name: TierName
    latency_ms: float
    marginal_utility_fn: str  # metadata for docs


@dataclass
class RoutePlan:
    tiers_to_run: list[TierName]
    expected_utility: float
    budget_ms: float
    rationale: str


def tier_specs(settings: Settings) -> list[TierSpec]:
    return [
        TierSpec(TierName.t0_rules, settings.tier0_latency_ms, "rules"),
        TierSpec(TierName.t1_fast, settings.tier1_latency_ms, "fast_ml"),
        TierSpec(TierName.t2_full, settings.tier2_latency_ms, "full_ml"),
    ]


def decision_from_score(score: float, settings: Settings) -> Decision:
    if score >= settings.decline_threshold:
        return Decision.decline
    if score >= settings.approve_threshold:
        return Decision.review
    return Decision.approve


def cascade_should_stop(score: float, settings: Settings) -> tuple[bool, str]:
    if score <= settings.cascade_safe_upper:
        return True, "clearly_safe"
    if score >= settings.cascade_fraud_lower:
        return True, "clearly_fraud"
    return False, ""


def estimate_tier_utility(
    tier: TierName,
    prior_score: float,
    settings: Settings,
) -> float:
    """Expected utility increment for running this tier (heuristic for planning)."""
    if tier == TierName.t0_rules:
        detection = settings.fraud_value * (0.55 * prior_score + 0.05)
    elif tier == TierName.t1_fast:
        detection = settings.fraud_value * (0.75 * prior_score + 0.08)
    else:
        detection = settings.fraud_value * (0.92 * prior_score + 0.1)

    latency = {
        TierName.t0_rules: settings.tier0_latency_ms,
        TierName.t1_fast: settings.tier1_latency_ms,
        TierName.t2_full: settings.tier2_latency_ms,
    }[tier]
    latency_cost = latency * settings.latency_penalty_per_ms
    review = settings.review_cost * max(0, prior_score - settings.approve_threshold)
    return detection - latency_cost - 0.25 * review


def plan_route(
    deadline_ms: float,
    settings: Settings,
    prior_score: float = 0.15,
) -> RoutePlan:
    """
    Resource-constrained knapsack on model depth:
    pick prefix of [T0,T1,T2] maximizing utility s.t. sum(latency)+margin <= D.
    Chance constraint approximated via requiring T1 when prior in ambiguous band.
    """
    specs = tier_specs(settings)
    budget = deadline_ms - settings.safety_margin_ms
    best: RoutePlan | None = None

    cumulative = 0.0
    chosen: list[TierName] = []
    total_u = 0.0
    for spec in specs:
        if cumulative + spec.latency_ms > budget:
            break
        marginal = estimate_tier_utility(spec.name, prior_score, settings)
        if marginal <= 0 and spec.name != TierName.t0_rules:
            break
        chosen.append(spec.name)
        cumulative += spec.latency_ms
        total_u += marginal
        prior_score = min(0.95, prior_score + 0.12)

    if not chosen:
        chosen = [TierName.t0_rules]
        total_u = estimate_tier_utility(TierName.t0_rules, 0.15, settings)

    # Chance constraint: ambiguous band needs at least T1 if budget allows
    ambiguous = 0.25 <= prior_score <= 0.65
    if ambiguous and TierName.t1_fast not in chosen:
        lat_t1 = settings.tier0_latency_ms + settings.tier1_latency_ms
        if lat_t1 <= budget:
            if TierName.t0_rules not in chosen:
                chosen.insert(0, TierName.t0_rules)
            if TierName.t1_fast not in chosen:
                chosen.append(TierName.t1_fast)

    rationale = f"knapsack_depth budget={budget:.1f}ms tiers={','.join(t.name for t in chosen)}"
    plan = RoutePlan(
        tiers_to_run=chosen,
        expected_utility=total_u,
        budget_ms=budget,
        rationale=rationale,
    )
    if best is None or plan.expected_utility >= (best.expected_utility if best else -1e9):
        best = plan
    return best or plan
