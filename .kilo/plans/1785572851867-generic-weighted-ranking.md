# Plan: Generic Weighted Ranking Refactor

## Goal

Refactor `home_purchase` into a generic `should_we_buy` package that ranks any kind of options (homes, cars, vacation spots, etc.) based on N evaluators' weighted opinions on user-defined features. Migrate existing data.

## Decisions

| Decision | Choice |
|---|---|
| Package name | `should_we_buy` |
| Config model | `data/config.json` (features + evaluators with weights), edited by hand |
| Data file | `data/options.json` (items being scored) |
| Migrate existing data | Yes, convert `data/homes.json` to new format |
| Score scale | 0–5 (unchanged, YAGNI to configure) |
| Combined score | Average of all evaluator normalized scores |
| Multi-project | No (YAGNI) — one project at a time |
| Tests | None (user explicitly said no) |

## New Data Schemas

### `data/config.json`
```json
{
  "project_name": "home-buying",
  "features": [
    {"key": "price", "label": "Price"},
    {"key": "will_to_buy", "label": "Will to buy"}
  ],
  "evaluators": [
    {
      "name": "Yannis",
      "weights": {"price": 5, "will_to_buy": 5}
    },
    {
      "name": "Natassa",
      "weights": {"price": 5, "will_to_buy": 4}
    }
  ]
}
```

### `data/options.json`
```json
[
  {
    "name": "takis",
    "scores": {"price": 4.0, "will_to_buy": 3.0},
    "breakdown": {
      "Yannis": 3.5,
      "Natassa": 3.33
    }
  }
]
```

Combined score (average of breakdown) is computed on-the-fly, not stored.

## Task List

### 1. Rename package: `home_purchase` → `should_we_buy`
- Rename `src/home_purchase/` → `src/should_we_buy/`
- Update `pixi.toml`: workspace name, task commands (`python -m home_purchase` → `python -m should_we_buy`)
- Delete `__pycache__/` directories

### 2. Create `src/should_we_buy/config.py`
- `Feature` dataclass (unchanged: `key`, `label`)
- `Evaluator` dataclass: `name`, `weights: dict[str, int]`
- `ScoringConfig` dataclass: `project_name`, `features: list[Feature]`, `evaluators: list[Evaluator]`
- `load_config(path)` → reads and validates `data/config.json`, returns `ScoringConfig`
- Validates that every evaluator weight key exists in features (like current `validate_weights` but generic)

### 3. Rewrite `src/should_we_buy/scoring.py`
- Remove hardcoded `WEIGHTS_YANNIS` / `WEIGHTS_NATASSA` imports
- `compute_scores(scores, evaluators: list[Evaluator])` → returns `dict[str, float]` (evaluator_name → normalized score)
- `compute_combined(breakdown: dict[str, float])` → average
- Delete `ScoreBreakdown` dataclass — use plain `dict[str, float]`

### 4. Rewrite `src/should_we_buy/storage.py`
- `Option` dataclass: `name: str`, `scores: dict[str, float]`, `breakdown: dict[str, float]`
- `load_options(path)` → reads `data/options.json`, returns `list[Option]`
- `save_option(name, scores, evaluators, path)` → computes breakdown, upserts into JSON
- `find_option(name, path)` → `Option | None`
- `reprocess_all(path)` → recomputes breakdown for all options based on config evaluators
- Remove CSV migration code (legacy cruft, no longer needed)
- All paths: `data/options.json` as default, config from `data/config.json`

### 5. Rewrite `src/should_we_buy/cli.py`
- Commands: `new`, `list`, `show`, `reprocess` (same verbs, generic labels)
- `new`: reads config for features, prompts for each feature score, saves option
- `list`: loads options, sorts by combined score desc, prints
- `show`: prints option name, per-evaluator breakdown, combined
- `reprocess`: recomputes all breakdowns from config
- Replace hardcoded "Yannis/Natassa" display with dynamic evaluator names

### 6. Delete `src/should_we_buy/features.py`
- Hardcoded features and weights are gone. Config-driven instead.

### 7. Migrate existing data
- Create `data/config.json` from current `FEATURES`, `WEIGHTS_YANNIS`, `WEIGHTS_NATASSA`
- Rename `data/homes.json` → `data/options.json` and restructure:
  - `breakdown` keys: `{"yannis": X, "natassa": Y}` → `{"Yannis": X, "Natassa": Y}` (capitalize evaluator names)
  - Drop `combined` from stored breakdown (computed on the fly)

### 8. Update `README.md`
- New package name, config-driven setup, generic language ("options" instead of "homes")
- Document `data/config.json` schema (edit by hand)
- Update pixi run examples

### 9. Update `pixi.toml`
- `name = "should_we_buy"`
- Tasks: `app`, `new`, `list`, `show`, `reprocess` → use `should_we_buy` module

## File Changes Summary

| File | Action |
|---|---|
| `src/home_purchase/**` | → Rename to `src/should_we_buy/` |
| `src/should_we_buy/features.py` | Delete |
| `src/should_we_buy/config.py` | New |
| `src/should_we_buy/scoring.py` | Rewrite (generic N-evaluator) |
| `src/should_we_buy/storage.py` | Rewrite (config-driven, drop CSV migration) |
| `src/should_we_buy/cli.py` | Rewrite (dynamic evaluator display) |
| `src/should_we_buy/__main__.py` | Trivial import path update |
| `src/should_we_buy/__init__.py` | Version unchanged |
| `data/config.json` | New (from current hardcoded features/weights) |
| `data/homes.json` | → Rename to `data/options.json`, restructure breakdown |
| `data/homes copy.json` | Delete (stale copy) |
| `pixi.toml` | Update name + task commands |
| `README.md` | Rewrite for generic usage |

## Validation

After implementation, run:
```bash
pixi run list     # should show existing homes ranked by new combined scores
pixi run show -- "takis"  # should show per-evaluator breakdown
pixi run reprocess  # should recompute and be idempotent
```
