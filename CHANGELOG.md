# Changelog

## Unreleased

- The project moved to the [selfhostit](https://github.com/selfhostit)
  organization. New images are published as `ghcr.io/selfhostit/should-we`;
  update the `image:` line in your `docker-compose.yml`.

## 2.1.0

- **Start a new decision like this one**: copies the title and what matters,
  joins you under the same name with the same priorities, and leaves options
  and ratings empty. Handy for a recurring choice such as job hunting.
- **Edit what matters** after starting: add or remove points for everyone.
  Ratings for points that stay are kept; options rated before a new point show
  "New point to rate".
- Hide a decision from the "Your decisions" list on the start screen.

## 2.0.0

A rebuild, with the same stack and deployment as Splitwiz. Not compatible
with 1.x data.

- **No accounts.** Anyone opens the app, starts a decision and shares its
  link. Whoever has the link picks a name, says what matters to them, adds
  and rates options, and sees the ranking. No admins, passwords or `.env`.
- **PocketBase (Go) + Svelte**, in one small Docker image
  (`ghcr.io/kalfasyan/should-we:2`) that needs no settings. Works behind any
  reverse proxy without WebSocket headers.
- Priorities are words (Don't care, A little, Important, Must-have) and
  everything saves as you tap. Scoring is unchanged: each person's ratings
  weighted by their priorities, averaged over everyone who rated an option.
- Removed: the CLI, admin screens, test users, join-link expiry, charts and
  CSV/JSON export.

## 1.0.0

The Python + NiceGUI app: admin login, join links, weighted 0–5 voting,
charts and export. Image: `ghcr.io/kalfasyan/should-we:fc2bf2c8cc2d27048d1b7cbf498253f2100da347`.
