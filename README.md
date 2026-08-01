## should-we-buy — Generic Weighted Ranking CLI

Rank options (homes, cars, vacation spots, etc.) based on N evaluators' weighted opinions on user-defined features.

### Quick start (pixi)

- **Set up a project** (interactive wizard):
  - `pixi run setup`
- **List projects**:
  - `pixi run list`
- **List options in a project**:
  - `pixi run list -p <project>`
- **Create a new option** (interactive prompts):
  - `pixi run new [-p <project>]`
- **Show one option**:
  - `pixi run show <name> [-p <project>]`
- **After editing the JSON by hand, recompute scores**:
  - `pixi run reprocess [-p <project>]`

### Configuration

Run `pixi run setup` for an interactive wizard. Each project lives in its own
subdirectory under `data/` (e.g. `data/car/config.json`).

Or create/edit by hand:

```json
{
  "project_name": "home-buying",
  "features": [
    {"key": "price", "label": "Price"},
    {"key": "location", "label": "Location"}
  ],
  "evaluators": [
    {
      "name": "Alice",
      "weights": {"price": 5, "location": 3}
    },
    {
      "name": "Bob",
      "weights": {"price": 3, "location": 5}
    }
  ]
}
```

- `features`: order matters for prompting. `key` is the machine identifier, `label` is shown to the user.
- `evaluators`: one per person. `weights` map feature keys to importance (0 = irrelevant, 5 = critical).
- Every evaluator must have a weight for every feature.

### Example: home-buying project

The repo ships with a `home-buying` project — a real apartment hunting example
(anonymized). Try it:

```bash
$ pixi run list
Projects:
  home-buying  — "home-buying" (7 option(s))

$ pixi run list -p home-buying
place-d  (combined=3.999)
place-g  (combined=3.911)
place-f  (combined=3.360)
place-a  (combined=3.137)
place-e  (combined=3.112)
place-b  (combined=2.675)
place-c  (combined=2.659)

$ pixi run show place-d -p home-buying
Name: place-d
Alice:  3.893
Bob:    4.106
Combined: 3.999
```

Peek at `data/home-buying/config.json` to see the features and weights, and
`data/home-buying/options.json` for all the scores.

### Scoring model

**Flow**: first define features + weights (`pixi run setup`), then score each option (`pixi run new`).

For each option, every evaluator rates each feature (0–5). Their personal
weights determine how much each feature counts. The combined score is the
average of all evaluators.

**Example** — Alice (cares about Color, w=5) and Bob (cares about Price/Eco, w=5):

| | Price (w=3) | Color (w=5) | Eco (w=1) | **Result** |
|---|---|---|---|---|
| Alice's scores | 3 | 2 | 2 | — |
| Weighted | 3×3 | 2×5 | 2×1 | (9+10+2)/9 = **2.333** |

| | Price (w=5) | Color (w=3) | Eco (w=5) | **Result** |
|---|---|---|---|---|
| Bob's scores | 4 | 4 | 4 | — |
| Weighted | 4×5 | 4×3 | 4×5 | (20+12+20)/13 = **4.000** |

**Combined**: (2.333 + 4.000) / 2 = **3.167**

Full walkthrough: see `docs/tutorial.md`.

### Data storage

Each project has its own `data/{project}/options.json`. Edit it by hand and
run `reprocess` to recompute the final scores.
