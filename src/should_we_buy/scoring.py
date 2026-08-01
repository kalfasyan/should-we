from __future__ import annotations

from .config import Evaluator


def compute_scores(
    scores: dict[str, dict[str, float]], evaluators: list[Evaluator]
) -> dict[str, float]:
    breakdown: dict[str, float] = {}
    for ev in evaluators:
        ev_scores = scores.get(ev.name, {})
        numerator = 0.0
        denom = 0.0
        for feat_key, weight in ev.weights.items():
            s = float(ev_scores.get(feat_key, 0.0))
            w = float(weight)
            numerator += s * w
            denom += w
        breakdown[ev.name] = 0.0 if denom == 0.0 else numerator / denom
    return breakdown


def compute_combined(breakdown: dict[str, float]) -> float:
    if not breakdown:
        return 0.0
    return sum(breakdown.values()) / len(breakdown)
