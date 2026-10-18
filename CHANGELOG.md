# Changelog

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
