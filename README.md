<p align="center"><img src="docs/assets/logo.png" alt="should-we logo" width="256"></p>

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

- **Multi-person weighted scoring** — each person decides how much each feature matters to them
- **One join link** — everyone picks a name, sets their weights, adds options, and votes from their own phone
- **0–5 scoring scale** — same ratings for everyone, weighted per person
- **Comparison charts** — bar chart of combined scores plus an options×people heatmap (missing cell = hasn't voted yet)
- **Notes & links per option** — add a link or note next to any option, shown in the heatmap tooltip
- **Disagreement marker** — options with widely split opinions are flagged in the rankings
- **Templates** — one-click project start for apartments, cars, vacations, laptops
- **Installable PWA** — "Add to Home Screen" on any phone: app icon, full-screen ([docs/deploy.md](docs/deploy.md))
- **Admin login + expiring join links** — password-protected control room; join links stop accepting new people after 30 days (extend anytime)
- **CLI + web UI** — dark-mode NiceGUI app (`pixi run ui`) with the same functionality
- **JSON on disk** — projects are plain files under `data/`; edit and `reprocess`
- **CSV export + read-only results page** — share or download the outcome

## Using the hosted app

The public instance is live at **https://should-we.fly.dev** — no install
for voters, works in any phone browser, and installable as a full-screen
PWA (Android: "Install app"; iOS: "Add to Home Screen").

**As an admin (project owner):**

1. Open https://should-we.fly.dev and log in with your admin name and
   password (the ones set via `SHOULD_WE_ADMINS` — see
   [docs/deploy.md](docs/deploy.md)).
2. **Setup tab** → project name + feature labels (or pick a template) →
   Save Config.
3. **Rankings tab** → copy the **join link** and send it to your group. It
   expires 30 days after the project is created — the date is shown with an
   "Extend 30 days" button next to it.
4. Watch the vote-status line fill in as people vote, then share the
   **results link** ("Copy results link") when you're done.

**As a group member:**

1. Open the join link on your phone.
2. Pick a name → set how much each feature matters to you → add options →
   rate them (0–5 sliders).
3. That's it — no account, no install. The welcome card explains how long
   the join link stays valid.

**FAQ**

- **Do I have to pay?** No — the hosted app runs on Fly.io's free tier (one
  small VM; signup requires a card but you're only billed if you scale up).
  No domain needed: `should-we.fly.dev` is free.
- **Do I need to deploy every time I want to use it?** No. `fly deploy` is
  only for shipping code changes. The app runs on its own; it pauses when
  nobody has it open and wakes in a few seconds on the next visit.
- **Is there a link I can use?** https://should-we.fly.dev — plus one join
  link and one results link per project (both copied from the Rankings tab).
- **How does a new person get started?** Open the join link, pick a name,
  vote. That's the whole onboarding.
- **Where is the data?** On the Fly volume (encrypted, survives redeploys),
  and locally in `data/` if you run the app on your own machine.

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

For each option, every person rates each feature (0–5). Their personal
weights decide how much each feature counts. The combined score is the
average of everyone who voted on that option (people who haven't voted or
haven't set weights don't count).

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

## Host it

Your whole group can vote from their own phones, no installs, no accounts:
the owner sets up the project and shares the join link. Everyone picks a
name, sets how much each feature matters to them (sliders), then adds
options and rates them with sliders — the vote-status line in Rankings
updates live, and charts refresh on any reload.

**Local** (same machine / LAN):

```bash
docker build -t should-we .
docker run -d -p 8080:8080 -v $(pwd)/data:/app/data should-we
```

Or with compose (same result, rebuilds as needed):

```bash
docker compose up -d
```

**Public + mobile (recommended):** the full deploy procedure — HTTPS,
installable PWA, admin login, expiring join links — is in
[docs/deploy.md](docs/deploy.md). The live app: `https://should-we.fly.dev`.

- Data lives in `data/` on the host (volume). `SHOULD_WE_DATA` overrides it; `SHOULD_WE_HOST` sets the bind address (default `127.0.0.1`).
- The web UI's admin area is password-protected: set `SHOULD_WE_ADMINS` (JSON map of admin name → password) and `SHOULD_WE_STORAGE_SECRET` (session signing), or nobody can log in (fail closed). Dev defaults ship in the `ui` pixi task; see [docs/deploy.md](docs/deploy.md).
- Join links expire 30 days after a project is created — the Rankings tab shows the date with an "Extend 30 days" button. Expiry only blocks new joiners; existing members keep their voting links.
- Results: `/results/<project>` requires admin login; the shareable link is `/results/<project>/<join-token>` (the "Copy results link" button gives it). Voting links are bearer secrets — regenerate a token to revoke that person.

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
- `evaluators`: one per person, created when they join via the join link. `weights` map feature keys to importance (0 = irrelevant, 5 = critical) and are set by each person on their voting page.
- `voting_tokens` / `join_token`: per-person and per-project secrets for the links.
- `join_expires_at`: ISO date when the join link stops accepting new people (created 30 days out; `null` or absent = never expires).

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
