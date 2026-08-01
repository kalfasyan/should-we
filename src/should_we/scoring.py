from __future__ import annotations

import statistics

from .config import Evaluator


def compute_scores(
    scores: dict[str, dict[str, float]], evaluators: list[Evaluator]
) -> dict[str, float]:
    by_name = {ev.name: ev for ev in evaluators}
    breakdown: dict[str, float] = {}
    for name, ev_scores in scores.items():
        ev = by_name.get(name)
        if ev is None or not ev.weights:
            continue
        numerator = 0.0
        denom = 0.0
        for feat_key, weight in ev.weights.items():
            s = float(ev_scores.get(feat_key, 0.0))
            w = float(weight)
            numerator += s * w
            denom += w
        if denom > 0.0:
            breakdown[name] = numerator / denom
    return breakdown


def compute_combined(breakdown: dict[str, float]) -> float:
    if not breakdown:
        return 0.0
    return sum(breakdown.values()) / len(breakdown)


def disagreement(breakdown: dict[str, float]) -> float | None:
    if len(breakdown) < 2:
        return None
    return statistics.stdev(breakdown.values())
