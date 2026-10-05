from app.config import Settings
from or_router.router import cascade_should_stop, decision_from_score, plan_route


def test_plan_respects_budget():
    s = Settings(default_deadline_ms=20.0, safety_margin_ms=2.0)
    plan = plan_route(20.0, s)
    lat = 0.0
    for t in plan.tiers_to_run:
        if t.value == "T0":
            lat += s.tier0_latency_ms
        elif t.value == "T1":
            lat += s.tier1_latency_ms
        else:
            lat += s.tier2_latency_ms
    assert lat <= 20.0 - s.safety_margin_ms


def test_cascade_safe_exit():
    s = Settings(cascade_safe_upper=0.08)
    stop, reason = cascade_should_stop(0.05, s)
    assert stop and reason == "clearly_safe"


def test_decision_thresholds():
    s = Settings(approve_threshold=0.22, decline_threshold=0.55)
    assert decision_from_score(0.1, s).value == "approve"
    assert decision_from_score(0.35, s).value == "review"
    assert decision_from_score(0.8, s).value == "decline"
