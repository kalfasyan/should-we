from __future__ import annotations

import json

from should_we.config import (
    Evaluator,
    Feature,
    ScoringConfig,
    add_evaluator,
    get_join_token,
    get_or_create_token,
    load_config,
    project_paths,
    regenerate_token,
    save_config,
    set_weights,
)
from should_we.scoring import compute_combined, compute_scores, disagreement
from should_we.storage import (
    delete_option,
    load_options,
    load_votes,
    reprocess_all,
    save_option,
    save_vote,
    update_notes,
)

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
    assert breakdown == {}
    assert compute_combined(breakdown) == 0.0


def test_unvoted_evaluator_not_counted():
    breakdown = compute_scores(
        {"Alice": {"price": 4, "color": 4, "eco": 4}},
        _make_config().evaluators,
    )
    assert set(breakdown) == {"Alice"}
    assert compute_combined(breakdown) == 4.0


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


def test_voting_tokens_roundtrip(monkeypatch, tmp_path):
    monkeypatch.setenv("SHOULD_WE_DATA", str(tmp_path))
    save_config(_make_config(), project="test-project")
    t1 = get_or_create_token("test-project", "Alice")
    assert t1
    assert load_config("test-project").voting_tokens["Alice"] == t1
    t2 = regenerate_token("test-project", "Alice")
    assert t2 != t1
    assert load_config("test-project").voting_tokens["Alice"] == t2


def test_old_config_without_tokens_loads(monkeypatch, tmp_path):
    monkeypatch.setenv("SHOULD_WE_DATA", str(tmp_path))
    save_config(_make_config(), project="test-project")
    cfg_path, _ = project_paths("test-project")
    raw = json.loads(cfg_path.read_text(encoding="utf-8"))
    del raw["voting_tokens"]
    del raw["join_token"]
    cfg_path.write_text(json.dumps(raw), encoding="utf-8")
    assert load_config("test-project").voting_tokens == {}
    assert load_config("test-project").join_token is None


def test_join_token_created_once(monkeypatch, tmp_path):
    monkeypatch.setenv("SHOULD_WE_DATA", str(tmp_path))
    save_config(_make_config(), project="test-project")
    t1 = get_join_token("test-project")
    assert load_config("test-project").join_token == t1
    assert get_join_token("test-project") == t1


def test_add_evaluator_idempotent_and_weights(monkeypatch, tmp_path):
    monkeypatch.setenv("SHOULD_WE_DATA", str(tmp_path))
    save_config(_make_config(), project="test-project")
    add_evaluator("test-project", "Charlie")
    add_evaluator("test-project", "Charlie")
    assert len(load_config("test-project").evaluators) == 3
    set_weights("test-project", "Charlie", {"price": 1, "color": 1, "eco": 1})
    charlie = next(e for e in load_config("test-project").evaluators if e.name == "Charlie")
    assert charlie.weights == {"price": 1, "color": 1, "eco": 1}
    alice = next(e for e in load_config("test-project").evaluators if e.name == "Alice")
    assert alice.weights == {"price": 3, "color": 5, "eco": 1}


def test_save_vote_merges_and_tracks(monkeypatch, tmp_path):
    monkeypatch.setenv("SHOULD_WE_DATA", str(tmp_path))
    save_config(_make_config(), project="test-project")
    save_option("home-a", {"Alice": {"price": 5, "color": 5, "eco": 5}}, project="test-project")
    save_vote("test-project", "Bob", "home-a", {"price": 1, "color": 1, "eco": 1})

    opts = load_options("test-project")
    assert opts[0].scores["Alice"]["price"] == 5.0
    assert opts[0].scores["Bob"]["price"] == 1.0
    assert round(opts[0].breakdown["Bob"], 3) == 1.0
    assert "home-a" in load_votes("test-project")["Bob"]


def test_option_notes_roundtrip(monkeypatch, tmp_path):
    monkeypatch.setenv("SHOULD_WE_DATA", str(tmp_path))
    save_config(_make_config(), project="test-project")
    save_option(
        "home-a",
        {"Alice": {"price": 5, "color": 5, "eco": 5}},
        project="test-project",
        notes="https://a.example",
    )
    assert load_options("test-project")[0].notes == "https://a.example"

    save_vote("test-project", "Bob", "home-a", {"price": 1, "color": 1, "eco": 1})
    assert load_options("test-project")[0].notes == "https://a.example"

    _, opt_path = project_paths("test-project")
    raw = json.loads(opt_path.read_text(encoding="utf-8"))
    del raw[0]["notes"]
    opt_path.write_text(json.dumps(raw), encoding="utf-8")
    assert load_options("test-project")[0].notes == ""


def test_update_notes_only_changes_notes(monkeypatch, tmp_path):
    monkeypatch.setenv("SHOULD_WE_DATA", str(tmp_path))
    save_config(_make_config(), project="test-project")
    save_option(
        "home-a",
        {"Alice": {"price": 5, "color": 5, "eco": 5}},
        project="test-project",
        notes="old",
    )
    assert update_notes("home-a", "new note", project="test-project")
    opt = load_options("test-project")[0]
    assert opt.notes == "new note"
    assert opt.scores["Alice"]["price"] == 5.0
    assert round(opt.breakdown["Alice"], 3) == 5.0
    assert not update_notes("ghost", "x", project="test-project")


def test_disagreement():
    assert disagreement({"A": 5.0, "B": 5.0}) == 0.0
    assert disagreement({"A": 1.0, "B": 5.0}) >= 1.5
    assert disagreement({"A": 4.0}) is None
