from __future__ import annotations

import json

from should_we.config import Evaluator, Feature, ScoringConfig, project_paths, save_config
from should_we.scoring import compute_combined, compute_scores
from should_we.storage import delete_option, load_options, reprocess_all, save_option

FEATURES = [
    Feature(key="price", label="Price"),
    Feature(key="color", label="Color"),
    Feature(key="eco", label="Eco"),
]
EVALUATORS = [
    Evaluator(name="Alice", weights={"price": 3, "color": 5, "eco": 1}),
    Evaluator(name="Bob", weights={"price": 5, "color": 3, "eco": 5}),
]


def _make_config() -> ScoringConfig:
    return ScoringConfig(
        project_name="test-project",
        features=FEATURES,
        evaluators=EVALUATORS,
    )


def test_compute_scores_matches_readme_example():
    alice = {"price": 3, "color": 2, "eco": 2}
    bob = {"price": 4, "color": 4, "eco": 4}
    breakdown = compute_scores(
        {"Alice": alice, "Bob": bob},
        _make_config().evaluators,
    )
    assert round(breakdown["Alice"], 3) == 2.333
    assert round(breakdown["Bob"], 3) == 4.0
    assert round(compute_combined(breakdown), 3) == 3.167


def test_zero_denominator_scores_zero():
    breakdown = compute_scores(
        {"Alice": {"price": 5}},
        [Evaluator(name="Alice", weights={"price": 0})],
    )
    assert breakdown["Alice"] == 0.0


def test_storage_roundtrip(monkeypatch, tmp_path):
    monkeypatch.setenv("SHOULD_WE_DATA", str(tmp_path))
    save_config(_make_config(), project="test-project")
    save_option(
        "home-a",
        {
            "Alice": {"price": 5, "color": 5, "eco": 5},
            "Bob": {"price": 5, "color": 5, "eco": 5},
        },
        project="test-project",
    )

    options = load_options("test-project")
    assert len(options) == 1
    assert options[0].name == "home-a"
    assert round(options[0].breakdown["Alice"], 3) == 5.0
    assert round(options[0].breakdown["Bob"], 3) == 5.0

    assert delete_option("home-a", project="test-project")
    assert load_options("test-project") == []
    assert not delete_option("home-a", project="test-project")


def test_reprocess_updates_stale_breakdown(monkeypatch, tmp_path):
    monkeypatch.setenv("SHOULD_WE_DATA", str(tmp_path))
    save_config(_make_config(), project="test-project")
    save_option("home-a", {"Alice": {"price": 3, "color": 2, "eco": 2}}, project="test-project")

    _, opt_path = project_paths("test-project")
    payload = json.loads(opt_path.read_text(encoding="utf-8"))
    payload[0]["breakdown"]["Alice"] = 99.0
    opt_path.write_text(json.dumps(payload), encoding="utf-8")

    assert reprocess_all("test-project") == 1
    assert round(load_options("test-project")[0].breakdown["Alice"], 3) == 2.333
