<p align="center"><img src="docs/assets/logo.png" alt="should-we logo" width="160"></p>

<h1 align="center">should-we</h1>

<p align="center"><em>Pick one option together.</em></p>

<p align="center"><a href="https://buymeacoffee.com/kalfasyan"><img src="https://img.shields.io/badge/Buy%20me%20a%20coffee-FFDD00?logo=buymeacoffee&logoColor=black" alt="Buy me a coffee"></a></p>

Rank options (homes, cars, holiday spots, anything) when several people
need to agree. Everyone says how much each point matters to them and rates
every option. should-we weights each person's ratings by their own
priorities and combines everyone into one ranking.

- **No accounts.** Start a decision, share its link. Whoever has the link
  picks a name and takes part.
- **Phone first.** Installable as an app ("Add to Home Screen"), saves as
  you tap, refreshes every few seconds.
- **Self-hosted.** One small Docker image with no settings, run the same way
  as [Splitwiz](https://github.com/kalfasyan/splitwiz).

Version 2 is a rebuild. The Python version is release
[v1.0.0](https://github.com/kalfasyan/should-we/releases/tag/v1.0.0); see
[CHANGELOG.md](CHANGELOG.md).

## How it works

1. **Start a decision**: what you're deciding, and what matters (price,
   location, …). Or pick an example.
2. **Share the link.** Each person picks a name.
3. **Say what matters**: Don't care, A little, Important or Must-have, per
   point.
4. **Add and rate options**, 0 (bad) to 5 (great) on each point.
5. **Results**: each person's score for an option is their ratings averaged
   by their priorities; the option's score is the average over everyone
   who rated it. Big disagreements are marked "opinions split".

Anyone in the decision can edit the list of what matters later. For a choice
that comes back (job hunting, holidays), use **Start a new decision like this
one** at the bottom of a decision: it copies the points and your priorities.
Everything is saved in `pb_data` on your server.

## How it is built

| Part | Choice |
| --- | --- |
| Backend | [PocketBase](https://pocketbase.io) used as a Go framework (`backend/`), SQLite database |
| Rules and scoring | `backend/decide`, unit tested |
| API | `backend/app/routes.go`: a decision's id is its share link; your browser keeps a token proving which person you are |
| Web app | Svelte 5 + Vite + Tailwind (`web/`), installable PWA |
| Packaging | One Docker image (`Dockerfile`), published to `ghcr.io/kalfasyan/should-we` by GitHub Actions |

## Run it on a home server

Any machine with Docker:

```sh
mkdir should-we && cd should-we
curl -O https://raw.githubusercontent.com/kalfasyan/should-we/main/docker-compose.yml
docker compose up -d     # http://127.0.0.1:8091
```

Put it behind your reverse proxy with HTTPS (Caddy, nginx, DSM, …) to
share links outside your home. Data lives in `pb_data/` next to the compose
file.

### On a Synology NAS

1. **Container Manager**: install it from Package Center if it is missing.
2. **Folder**: in File Station, create `docker/should-we/pb_data`.
3. **Project**: Container Manager > Project > Create, name `should-we`,
   path `/volume1/docker/should-we`, and paste
   [`docker-compose.yml`](docker-compose.yml). Start it.
4. **Certificate**: Control Panel > Security > Certificate > Add > Let's
   Encrypt, for `should-we.<your-name>.synology.me` (your Synology DDNS
   name with `should-we.` in front).
5. **Reverse proxy**: Control Panel > Login Portal > Advanced > Reverse
   Proxy > Create. Source: HTTPS, `should-we.<your-name>.synology.me`,
   port 443. Destination: HTTP, `localhost`, port 8091. Then assign the
   certificate to it under Certificate > Settings.
6. Open `https://should-we.<your-name>.synology.me` and start a decision.

### Updating

Pull the new image and recreate the container (Container Manager: Image >
Update, then Project > Action > Build; anywhere else:
`docker compose pull && docker compose up -d`). Or build on your computer
and push straight to the NAS:

```sh
scripts/deploy-to-nas.sh you@your-nas-address
```

Images: `:2` follows the latest 2.x, `:2.0.0` is that exact release.

### Backups

Copy the `pb_data` folder (on a Synology: add `/volume1/docker/should-we`
to a Hyper Backup task). Optional: create an admin with
`docker exec -it should-we /app/should-we superuser upsert you@example.com 'password' --dir=/app/pb_data`
to browse the data at `/_/` and schedule PocketBase's own backups.

## Run it locally

```sh
# backend (needs Go 1.27+)
cd backend
go run . serve            # http://127.0.0.1:8090

# web app with hot reload (needs Node 22+), in another terminal
cd web
npm install
npm run dev               # proxies /api to :8090
```

Tests: `cd backend && go test ./...` and `cd web && npm test && npm run check`.

## Releasing

Bump `version` in `web/package.json`, add a CHANGELOG entry, merge, then
publish a GitHub release tagged `vX.Y.Z`. CI publishes the matching image
tags.

## Support

If should-we is useful to you, you can [buy me a coffee](https://buymeacoffee.com/kalfasyan) ☕

## License

[MIT](LICENSE)
