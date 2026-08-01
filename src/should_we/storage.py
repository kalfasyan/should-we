from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from .config import ScoringConfig, load_config, project_paths, resolve_project
from .scoring import compute_scores


@dataclass
class Option:
    name: str
    scores: dict[str, dict[str, float]] = field(default_factory=dict)
    breakdown: dict[str, float] = field(default_factory=dict)


def _read_json(path: Path) -> list[dict]:
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("[]\n", encoding="utf-8")
        return []
    raw = json.loads(path.read_text(encoding="utf-8"))
    return raw if isinstance(raw, list) else []


def _write_json(path: Path, payload: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n", encoding="utf-8")


def _normalize_scores(
    raw_scores: dict | None, config: ScoringConfig
) -> dict[str, dict[str, float]]:
    raw_scores = raw_scores or {}
    scores: dict[str, dict[str, float]] = {}
    for ev in config.evaluators:
        ev_raw = raw_scores.get(ev.name, {})
        if not isinstance(ev_raw, dict):
            ev_raw = {}
        ev_scores: dict[str, float] = {}
        for feat in config.features:
            v = ev_raw.get(feat.key, 0.0)
            try:
                ev_scores[feat.key] = float(v)
            except (TypeError, ValueError):
                ev_scores[feat.key] = 0.0
        scores[ev.name] = ev_scores
    return scores


def load_options(project: str | None = None) -> list[Option]:
    project = resolve_project(project)
    config = load_config(project)
    _, opt_path = project_paths(project)
    raw = _read_json(opt_path)
    options: list[Option] = []
    for item in raw:
        name = str(item.get("name", "")).strip()
        if not name:
            continue
        scores = _normalize_scores(item.get("scores"), config)
        breakdown_raw = item.get("breakdown") or {}
        breakdown = {}
        for k, v in breakdown_raw.items():
            try:
                breakdown[str(k)] = float(v)
            except (TypeError, ValueError):
                breakdown[str(k)] = 0.0
        options.append(Option(name=name, scores=scores, breakdown=breakdown))
    return options


def save_option(
    name: str,
    scores: dict[str, dict[str, float]],
    project: str | None = None,
) -> Option:
    project = resolve_project(project)
    config = load_config(project)
    _, opt_path = project_paths(project)
    normalized_scores = _normalize_scores(scores, config)
    breakdown = compute_scores(normalized_scores, config.evaluators)

    payload = _read_json(opt_path)
    record = {
        "name": name,
        "scores": normalized_scores,
        "breakdown": {k: round(v, 4) for k, v in breakdown.items()},
    }

    existing_idx = next(
        (i for i, h in enumerate(payload) if str(h.get("name", "")).strip() == name),
        None,
    )
    if existing_idx is None:
        payload.append(record)
    else:
        payload[existing_idx] = record

    _write_json(opt_path, payload)
    return Option(name=name, scores=normalized_scores, breakdown=breakdown)


def find_option(name: str, project: str | None = None) -> Option | None:
    for opt in load_options(project):
        if opt.name == name:
            return opt
    return None


def delete_option(name: str, project: str | None = None) -> bool:
    project = resolve_project(project)
    _, opt_path = project_paths(project)
    payload = _read_json(opt_path)
    remaining = [item for item in payload if str(item.get("name", "")).strip() != name]
    if len(remaining) == len(payload):
        return False
    _write_json(opt_path, remaining)
    return True


def reprocess_all(project: str | None = None) -> int:
    project = resolve_project(project)
    config = load_config(project)
    _, opt_path = project_paths(project)
    payload = _read_json(opt_path)
    processed = 0
    for item in payload:
        name = (item.get("name") or "").strip()
        if not name:
            continue
        scores = _normalize_scores(item.get("scores"), config)
        breakdown = compute_scores(scores, config.evaluators)
        item["scores"] = scores
        item["breakdown"] = {k: round(v, 4) for k, v in breakdown.items()}
        processed += 1
    _write_json(opt_path, payload)
    return processed
