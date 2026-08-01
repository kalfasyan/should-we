from __future__ import annotations

import json
import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path

DATA_DIR = Path("data")

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


def _label_to_key(label: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", label.strip().lower()).strip("_")


def project_paths(project: str) -> tuple[Path, Path]:
    base = DATA_DIR / project
    return base / "config.json", base / "options.json"


def list_projects() -> list[str]:
    if not DATA_DIR.exists():
        return []
    projects: list[str] = []
    for d in sorted(DATA_DIR.iterdir()):
        if d.is_dir() and (d / "config.json").exists():
            projects.append(d.name)
    return projects


def delete_project(project: str) -> None:
    base = DATA_DIR / project
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
    evaluators = [Evaluator(name=e["name"], weights=e.get("weights", {})) for e in raw["evaluators"]]

    _validate_config(features, evaluators)
    return ScoringConfig(
        project_name=raw.get("project_name", project),
        features=features,
        evaluators=evaluators,
    )


def save_config(config: ScoringConfig, project: str | None = None) -> None:
    project = project or _label_to_key(config.project_name)
    cfg_path, _ = project_paths(project)
    _validate_config(config.features, config.evaluators)
    data = {
        "project_name": config.project_name,
        "features": [{"key": f.key, "label": f.label} for f in config.features],
        "evaluators": [{"name": e.name, "weights": e.weights} for e in config.evaluators],
    }
    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    cfg_path.write_text(json.dumps(data, indent=2, sort_keys=False) + "\n", encoding="utf-8")


def _validate_config(features: list[Feature], evaluators: list[Evaluator]) -> None:
    feature_keys = {f.key for f in features}
    for ev in evaluators:
        missing = sorted(feature_keys - set(ev.weights.keys()))
        extra = sorted(set(ev.weights.keys()) - feature_keys)
        if missing or extra:
            raise ValueError(
                f"Weight profile '{ev.name}' mismatch. missing={missing!r} extra={extra!r}"
            )
