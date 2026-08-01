<p align="center"><img src="docs/assets/logo.png" alt="should-we logo" width="180"></p>

<h1 align="center">should-we</h1>

<p align="center">
  <em>Generic weighted ranking — decide together, not by volume.</em>
</p>

<p align="center">
  <a href="LICENSE"><img alt="License: MIT" src="https://img.shields.io/badge/license-MIT-blue.svg"></a>
  <a href="https://www.python.org/downloads/"><img alt="Python 3.13" src="https://img.shields.io/badge/python-3.13-blue"></a>
  <a href="https://pixi.sh"><img alt="Pixi" src="https://img.shields.io/badge/powered%20by-pixi-9b5de5"></a>
  <a href="https://docs.astral.sh/ruff/"><img alt="Ruff" src="https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json"></a>
  <a href="https://github.com/kalfasyan/should-we/actions/workflows/ci.yml"><img alt="CI" src="https://img.shields.io/github/actions/workflow/status/kalfasyan/should-we/ci.yml?label=CI"></a>
</p>

---

Rank options — homes, cars, vacation spots, anything — when multiple people
need to agree. Each person rates every option on the same set of features,
but each person also decides how much each feature *matters to them*: a car
nut weights "horsepower" higher while their partner weights "cup-holders".

The tool averages everyone's weighted scores into a final ranking. CLI or
web UI, your call.

## Features

- **Multi-person weighted scoring** — each evaluator defines personal feature weights
- **0–5 scoring scale** — same ratings for everyone, weighted per person
- **CLI + web UI** — dark-mode NiceGUI app (`pixi run ui`) with the same functionality
- **JSON on disk** — projects are plain files under `data/`; edit and `reprocess`

## Quick start (pixi)

Requires [pixi](https://pixi.prefix.dev/latest/installation/).

```bash
git clone git@github.com:kalfasyan/should-we.git
cd should-we
pixi install
```

**1. Set up a project** (interactive wizard):

```bash
pixi run setup
```

**2. Score options:**

```bash
pixi run new            # add an option (rates it for every evaluator)
pixi run list           # ranked results
pixi run show <name>    # one option's per-person breakdown
```

**3. Or use the web UI:**

```bash
pixi run ui
```

### All commands

| Command | What it does |
|---|---|
| `pixi run setup` | Interactive wizard: project name, people, features, weights |
| `pixi run new [-p <project>]` | Add an option, scoring it feature-by-feature |
| `pixi run list [-p <project>]` | List projects, or ranked options with `-p` |
| `pixi run show <name> [-p <project>]` | Show one option's breakdown |
| `pixi run reprocess [-p <project>]` | Recompute scores after hand-editing JSON |
| `pixi run delete <project>` | Delete a project and its options |
| `pixi run ui` | Launch the web app |

### Example: home-buying project

The repo ships with a real (anonymized) apartment-hunting project:

```bash
$ pixi run list -p home-buying
place-d  (combined=3.999)
place-g  (combined=3.911)
place-f  (combined=3.360)
place-a  (combined=3.137)
place-e  (combined=3.112)
place-b  (combined=2.675)
place-c  (combined=2.659)
```

## Scoring model

For each option, every evaluator rates each feature (0–5). Their personal
weights decide how much each feature counts. The combined score is the
average of all evaluators.

Alice (cares about Color, w=5) and Bob (cares about Price/Eco, w=5):

| | Price (w=3) | Color (w=5) | Eco (w=1) | **Result** |
|---|---|---|---|---|
| Alice's scores | 3 | 2 | 2 | — |
| Weighted | 3×3 | 2×5 | 2×1 | (9+10+2)/9 = **2.333** |

| | Price (w=5) | Color (w=3) | Eco (w=5) | **Result** |
|---|---|---|---|---|
| Bob's scores | 4 | 4 | 4 | — |
| Weighted | 4×5 | 4×3 | 4×5 | (20+12+20)/13 = **4.000** |

**Combined**: (2.333 + 4.000) / 2 = **3.167**

Full walkthrough: [docs/tutorial.md](docs/tutorial.md).

## Configuration

Each project lives in its own subdirectory under `data/`
(e.g. `data/car/config.json`). Run `pixi run setup`, or create/edit by hand:

```json
{
  "project_name": "home-buying",
  "features": [
    {"key": "price", "label": "Price"},
    {"key": "location", "label": "Location"}
  ],
  "evaluators": [
    {"name": "Alice", "weights": {"price": 5, "location": 3}},
    {"name": "Bob", "weights": {"price": 3, "location": 5}}
  ]
}
```

- `features`: order matters for prompting. `key` is the machine identifier, `label` is shown to the user.
- `evaluators`: one per person. `weights` map feature keys to importance (0 = irrelevant, 5 = critical).
- Every evaluator must have a weight for every feature.

Options live in `data/{project}/options.json` — edit by hand, then `pixi run reprocess`.

## Development

```bash
pixi run lint          # ruff check
pixi run lint-fix      # ruff check --fix
pixi run format        # ruff format --check
pixi run format-fix    # ruff format
pixi run test          # pytest
pixi run check         # lint + format + tests (what CI runs)
```

Pre-commit hooks (ruff lint + format) are configured; enable once with:

```bash
pixi run pre-commit-install
pixi run pre-commit    # run manually on all files
```

## License

[MIT](LICENSE)
