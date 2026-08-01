# Tutorial — Score Your First Thing

First, [install pixi](https://pixi.prefix.dev/latest/installation/).

Let's rank something. Could be a house, a car, a vacation spot — anything you
and someone else need to agree on.

We'll do this in 3 steps:

1. Define what matters and who cares (setup)
2. Score your options
3. See who wins

> **Tip — web UI:** don't like the terminal? Run `pixi run ui` for a
> dark-mode web app that does everything below with a few clicks — see
> [Web UI walkthrough](#web-ui-walkthrough).

---

## Step 1: Setup — What Are We Judging?

Run the setup wizard. It asks 4 questions:

```bash
pixi run setup
```

```
What are you thinking of buying? (this will be the project name, e.g. 'apartment', 'vacation', 'car'): car

Who's making this decision together? (comma-separated names, e.g. 'Alice, Bob'): Alice, Bob

What are the things you care about when picking one?
(comma-separated, e.g. 'Price, Location, Parking'): Price, Speed, Comfort

Now, how much does each feature matter to each of you?
  0 = don't care  |  3 = important  |  5 = dealbreaker

How much do these matter to you, Alice?
  Price (0–5): 5
  Speed (0–5): 3
  Comfort (0–5): 2

How much do these matter to you, Bob?
  Price (0–5): 3
  Speed (0–5): 5
  Comfort (0–5): 4

All set! Config saved to data/car/.
  3 feature(s), 2 people. Ready to `pixi run new`.
```

That's it. Each project gets its own directory under `data/` —
`data/car/config.json` and `data/car/options.json` for this one.

```json
{
  "project_name": "car",
  "features": [
    {"key": "price", "label": "Price"},
    {"key": "speed", "label": "Speed"},
    {"key": "comfort", "label": "Comfort"}
  ],
  "evaluators": [
    {
      "name": "Alice",
      "weights": {"price": 5, "speed": 3, "comfort": 2}
    },
    {
      "name": "Bob",
      "weights": {"price": 3, "speed": 5, "comfort": 4}
    }
  ]
}
```

**Features** — what you're grading. Keys are auto-generated from labels
(lowercase, underscores). Order matters: it's the order you'll be prompted.

**Evaluators** — the people with opinions. Weights go from 0 to 5:

| Weight | Meaning |
|--------|---------|
| 0 | I don't care at all |
| 3 | Important |
| 5 | Make or break |

> **Want to tweak later?** Edit `data/car/config.json` by hand, then run
> `pixi run reprocess` to update existing scores. Or run `pixi run setup` to
> create a whole new project.

---

## Step 2: Your First Option

```bash
pixi run new
```

(Add `-p car` if you have multiple projects.)

Name it, then each evaluator scores every feature:

```
Option name: tesla

--- Scores from Alice (0–5, Enter to skip) ---
  Price: 4
  Speed: 5
  Comfort: 3

--- Scores from Bob (0–5, Enter to skip) ---
  Price: 3
  Speed: 4
  Comfort: 5
```

Hit Enter on any feature to skip it (score = 0). Each person rates
independently — Alice might love the speed, Bob might not care.

Then:

```
Saved.

Alice:  4.100
Bob:    4.083
Combined: 4.092
```

Alice's scores are weighted by Alice's preferences. Bob's by Bob's.
No arguing — just math. Here's exactly how:

---

### How the Math Works

Let's walk through a real example. We set up a car project with Alice and Bob:

```json
{
  "features": ["Price", "Color", "Eco"],
  "evaluators": [
    {"name": "Alice", "weights": {"price": 3, "color": 5, "eco": 1}},
    {"name": "Bob",   "weights": {"price": 5, "color": 3, "eco": 5}}
  ]
}
```

Alice cares most about Color. Bob cares about Price and Eco. Now we score a car:

```
--- Scores from Alice ---      --- Scores from Bob ---
  Price: 3                       Price: 4
  Color: 2                       Color: 4
  Eco:   2                       Eco:   4
```

**For Alice**: each score multiplied by her weight, then divided by total weight:

$$\frac{(3 \times 3) + (2 \times 5) + (2 \times 1)}{3 + 5 + 1} = \frac{9 + 10 + 2}{9} = \frac{21}{9} = 2.333$$

**For Bob**: same formula with his weights:

$$\frac{(4 \times 5) + (4 \times 3) + (4 \times 5)}{5 + 3 + 5} = \frac{20 + 12 + 20}{13} = \frac{52}{13} = 4.000$$

**Combined**: average of the two:

$$\frac{2.333 + 4.000}{2} = 3.167$$

That's the number you see in the leaderboard.

> **Key insight:** Alice rated the car lower (mostly 2s and 3s) and the
> features she cares about got low scores. Bob rated everything highly and
> cares deeply about Price and Eco, which he gave 4s. So Bob's own score
> (4.0) is much higher than Alice's (2.3). The combined score (3.2) is the
> middle ground.

---

## Step 3: The Leaderboard

```bash
pixi run list -p car
```

```
tesla    (combined=4.092)
bmw      (combined=3.450)
fiat     (combined=2.100)
```

Sorted by combined score (average of everyone's normalized score). Highest
first.

Drill into one:

```bash
pixi run show tesla -p car
```

```
Name: tesla
Alice:  4.100
Bob:    4.083
Combined: 4.092
```

---

## Web UI Walkthrough

The web app (`pixi run ui`) replaces the terminal flow with a few clicks and
adds charts:

1. **Setup tab** — type a project name and feature labels, or pick a
   template (apartment, car, laptop, vacation). Save Config.
2. **Share the link** — a "Project ready!" dialog appears with the join
   link. Copy it and send it to the group.
3. **Everyone joins** — the join link asks for a name, then drops them on
   their voting page: sliders for how much each feature matters to them,
   then an "Add an option" box with an optional link/note, and rating
   sliders (0–5, step 0.5) per option. Duplicate option names are blocked;
   links/notes can be edited per option via "Save note".
4. **Rankings tab** — bar chart of combined scores and an
   options×people heatmap at the top (hover a cell for the score and note;
   a missing cell means that person hasn't voted). Below, the ranked list
   shows ✅/⏳ next to each person per option, and a 🤔 tag when people
   disagree strongly (standard deviation ≥ 1.5).
5. **Share results** — a read-only results page at `/results/<project>`
   shows the charts without the editing controls.

---

## Starting a New Project

Run `pixi run setup` again. Each project lives in its own subdirectory
under `data/` (e.g., `data/car/`, `data/home-buying/`).

```bash
pixi run list
```

```
Projects:
  car          — "car" (2 option(s))
  home-buying  — "home-buying" (7 option(s))
```

With one project, commands auto-detect. With multiple, add `-p`:

```bash
pixi run new -p car
pixi run list -p home-buying
pixi run show tesla -p car
```

Or just edit `data/{project}/config.json` and `data/{project}/options.json`
by hand — they're plain JSON.

---

## The Fine Print

| Command | Does |
|---------|------|
| `pixi run setup` | Create a new project interactively |
| `pixi run list` | List all projects |
| `pixi run list -p <project>` | List options in a project, ranked |
| `pixi run new [-p <project>]` | Add an option interactively |
| `pixi run show <name> [-p <project>]` | Inspect one option |
| `pixi run reprocess [-p <project>]` | Re-score everything (after editing JSON by hand) |
| `pixi run ui` | Launch the web app |

`-p` is optional when only one project exists.

**Scoring**: `(score × weight) for each feature ÷ total weight` per evaluator,
then average everyone's results.

**Data**: each project in `data/{project}/config.json` (features, people,
tokens), `data/{project}/options.json` (scores, breakdowns, per-option
notes), and `data/{project}/votes.json` (who has voted). Plain JSON. Edit,
share, version-control.
