# Deploying should-we (public + mobile)

The web UI is a normal web app — a phone browser is already "the app". This
guide covers making it **public, HTTPS, and installable** (Progressive Web
App: home-screen icon, full-screen) plus the admin/expiry features that come
with it. Everything below was done against Fly.io's free tier; the same
principle applies to any host that gives you HTTPS and a persistent disk.

## What you get

- **Installable PWA** — Android Chrome: "Install app"; iOS Safari: "Add to
  Home Screen". Same URL, app icon, no URL bar.
- **Admin login** — the front page is a login screen. Project list, setup,
  tokens, and delete are admin-only.
- **Secret results links** — the group's results link embeds the project's
  join token; a bare `/results/<project>` URL requires admin login.
- **Expiring join links** — every new project's join link stops accepting
  new people after 30 days. The admin sees the date (yellow ≤ 7 days, red
  when expired) and can "Extend 30 days" from the Rankings tab. First-time
  joiners get a welcome card explaining the window. Existing members keep
  their personal voting links after expiry.

## One-time setup

```bash
brew install flyctl
fly auth login                      # opens browser; free plan needs a card on file
cd <repo>
fly launch --name should-we --region fra --no-deploy --yes
```

This writes `fly.toml`. The repo's version already contains the two
deployment-critical settings:

```toml
[env]
  FORWARDED_ALLOW_IPS = '*'        # trust Fly's HTTPS proxy for link building
[[mounts]]
  source = 'data'
  destination = '/app/data'        # votes survive redeploys
```

Create the data disk, then set the required secrets (the app fails closed
— no admins configured means nobody can log in):

```bash
fly volumes create data --size 1 --region fra
fly secrets set "SHOULD_WE_ADMINS={\"Yannis\": \"<password>\", \"Partner\": \"<password>\"}" \
  SHOULD_WE_STORAGE_SECRET=$(openssl rand -hex 16)
```

- `SHOULD_WE_ADMINS` — JSON map of admin name → password (admin login).
- `SHOULD_WE_STORAGE_SECRET` — signs the login session cookie (keep it
  secret; changing it logs everyone out).

## Deploy and use

```bash
fly deploy
```

1. Open `https://should-we.fly.dev` — log in as an admin.
2. Setup tab → create a project (its join link is valid 30 days).
3. Rankings tab → copy the join link to your group. The expiry line and
   "Extend 30 days" button live right under it.
4. "Copy results link" hands out the secret results link to the group.

## Updating / changing passwords

```bash
fly deploy                                  # after any code change
fly secrets set "SHOULD_WE_ADMINS={\"Yannis\": \"<new>\", ...}" && fly deploy   # new passwords
```

**Where are the admin credentials?** On Fly, as secrets — never in the repo,
never in the database. `fly secrets list` shows only the names (it prints a
digest, not the value); values cannot be read back, so store them in a
password manager the day you create them. Lost both? Set new ones with
`fly secrets set` and redeploy — old ones stop working instantly.

**Adding / removing admins** — edit the same secret (each entry in the JSON
map is one admin), then redeploy:

```bash
fly secrets set "SHOULD_WE_ADMINS={\"Yannis\": \"...\", \"Partner\": \"...\", \"Sam\": \"...\"}" && fly deploy
```

Every admin sees **every project** on the instance — there is no per-admin
separation. Give admin access only to people you trust with all projects
(what the join link gates is who can *vote* in a project, not who can
*manage* it). For fully separate groups, run a second instance.

**Is the login secure?** The session cookie is HTTPS-only and signed, password
checks are constant-time, and the app fails closed if the secrets are missing.
The login form has no rate limiting, so use long random passwords (like the
generated ones) rather than words.

## Local development

`pixi run ui` works out of the box with dev-only defaults baked into the
pixi task (`yannis`/`dev`, `partner`/`dev`, secret `dev-secret`) — fine on
`localhost`, never use those in production.

## Limits and gotchas

- Free tier: one 256MB VM (`fly.toml` already set); the machine
  auto-stops when idle and cold-starts in a few seconds on the next visit.
- If the login page ever says "No admins configured", `SHOULD_WE_ADMINS` is
  missing — set it with `fly secrets set` and redeploy. The app refuses to
  guess rather than open the door.
- Session cookies are HTTPS-only (`https_only` is on in `ui.run`).
- Old results/join links keep working after a join-link expiry — expiry
  only blocks *new* joiners; revoke a person by regenerating their token in
  the Rankings tab.
