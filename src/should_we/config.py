from __future__ import annotations

import json
import os
import re
import secrets
import shutil
from dataclasses import dataclass, field, replace
from datetime import date, timedelta
from pathlib import Path


def data_dir() -> Path:
    return Path(os.environ.get("SHOULD_WE_DATA", "data"))


@dataclass(frozen=True)
class Feature:
    key: str
    label: str


@dataclass(frozen=True)
class Evaluator:
    name: str
    weights: dict[str, int] = field(default_factory=dict)


@dataclass(frozen=True)
class ScoringConfig:
    project_name: str
    features: list[Feature]
    evaluators: list[Evaluator]
    voting_tokens: dict[str, str] = field(default_factory=dict)
    join_token: str | None = None
    join_expires_at: str | None = None


DEFAULT_LINK_DAYS = 30


def default_join_expiry() -> str:
    return (date.today() + timedelta(days=DEFAULT_LINK_DAYS)).isoformat()


def _label_to_key(label: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", label.strip().lower()).strip("_")


def project_paths(project: str) -> tuple[Path, Path]:
    base = data_dir() / project
    return base / "config.json", base / "options.json"


def list_projects() -> list[str]:
    root = data_dir()
    if not root.exists():
        return []
    projects: list[str] = []
    for d in sorted(root.iterdir()):
        if d.is_dir() and (d / "config.json").exists():
            projects.append(d.name)
    return projects


def delete_project(project: str) -> None:
    base = data_dir() / project
    if base.exists():
        shutil.rmtree(base)


def resolve_project(name: str | None = None) -> str:
    if name:
        cfg, _ = project_paths(name)
        if not cfg.exists():
            raise SystemExit(f"Project '{name}' not found. Run: pixi run projects")
        return name
    projects = list_projects()
    if not projects:
        raise SystemExit("No projects yet. Run: pixi run setup")
    if len(projects) == 1:
        return projects[0]
    raise SystemExit(
        f"Multiple projects found: {', '.join(projects)}.\n"
        f"Pick one with --project, e.g.: --project {projects[0]}"
    )


def load_config(project: str | None = None) -> ScoringConfig:
    project = resolve_project(project)
    cfg_path, _ = project_paths(project)
    raw = json.loads(cfg_path.read_text(encoding="utf-8"))

    features = [Feature(key=f["key"], label=f["label"]) for f in raw["features"]]
    evaluators = [
        Evaluator(name=e["name"], weights=e.get("weights", {})) for e in raw["evaluators"]
    ]

    return ScoringConfig(
        project_name=raw.get("project_name", project),
        features=features,
        evaluators=evaluators,
        voting_tokens=raw.get("voting_tokens", {}),
        join_token=raw.get("join_token"),
        join_expires_at=raw.get("join_expires_at"),
    )


def save_config(config: ScoringConfig, project: str | None = None) -> None:
    project = project or _label_to_key(config.project_name)
    cfg_path, _ = project_paths(project)
    data = {
        "project_name": config.project_name,
        "features": [{"key": f.key, "label": f.label} for f in config.features],
        "evaluators": [{"name": e.name, "weights": e.weights} for e in config.evaluators],
        "voting_tokens": config.voting_tokens,
        "join_token": config.join_token,
        "join_expires_at": config.join_expires_at,
    }
    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    cfg_path.write_text(json.dumps(data, indent=2, sort_keys=False) + "\n", encoding="utf-8")


def get_or_create_token(project: str, evaluator: str) -> str:
    config = load_config(project)
    tokens = dict(config.voting_tokens)
    token = tokens.get(evaluator)
    if not token:
        token = secrets.token_urlsafe(12)
        tokens[evaluator] = token
        save_config(replace(config, voting_tokens=tokens), project=project)
    return token


def regenerate_token(project: str, evaluator: str) -> str:
    config = load_config(project)
    tokens = dict(config.voting_tokens)
    token = secrets.token_urlsafe(12)
    tokens[evaluator] = token
    save_config(replace(config, voting_tokens=tokens), project=project)
    return token


def get_join_token(project: str) -> str:
    config = load_config(project)
    if config.join_token:
        return config.join_token
    token = secrets.token_urlsafe(12)
    save_config(replace(config, join_token=token), project=project)
    return token


def extend_join_link(project: str, days: int = DEFAULT_LINK_DAYS) -> str:
    config = load_config(project)
    expires_at = (date.today() + timedelta(days=days)).isoformat()
    save_config(replace(config, join_expires_at=expires_at), project=project)
    return expires_at


def join_link_days_left(config: ScoringConfig, today: date | None = None) -> int | None:
    """Days until the join link expires; None = never expires, 0 = expires today."""
    raw = config.join_expires_at
    if not raw:
        return None
    try:
        return (date.fromisoformat(raw) - (today or date.today())).days
    except ValueError:  # unreadable date → treat as already expired
        return -1


def join_link_expired(config: ScoringConfig, today: date | None = None) -> bool:
    left = join_link_days_left(config, today)
    return left is not None and left < 0


def add_evaluator(project: str, name: str) -> ScoringConfig:
    config = load_config(project)
    if any(e.name == name for e in config.evaluators):
        return config
    config = replace(config, evaluators=[*config.evaluators, Evaluator(name=name, weights={})])
    save_config(config, project=project)
    return config


def set_weights(project: str, evaluator: str, weights: dict[str, int]) -> None:
    config = load_config(project)
    evaluators = [
        Evaluator(name=e.name, weights=weights if e.name == evaluator else e.weights)
        for e in config.evaluators
    ]
    save_config(replace(config, evaluators=evaluators), project=project)
