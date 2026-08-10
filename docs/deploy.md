# Deploying should-we (public + mobile)

The web UI is a normal web app — a phone browser is already "the app". This
guide covers making it **public, HTTPS, and installable** (Progressive Web
App: home-screen icon, full-screen) plus the admin/expiry features that come
with it. Everything below runs on an Oracle Cloud **Always Free** VM; the
same principle applies to any host that gives you HTTPS and a persistent
disk.

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

1. **Oracle VM** (Always Free): compute instance, Ubuntu 24.04, public IPv4.
   `VM.Standard.E2.1.Micro` (1 GB RAM) is plenty for this app once you add
   swap; free ARM `VM.Standard.A1.Flex` shapes work too when capacity is
   available. Add swap on small shapes:
   ```bash
   sudo fallocate -l 2G /swapfile && sudo chmod 600 /swapfile
   sudo mkswap /swapfile && sudo swapon /swapfile
   echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
   ```
2. **Networking — both layers, or nothing works**:
   - OCI security list: ingress TCP 80 and 443 from `0.0.0.0/0`.
   - The VM's own firewall (the Ubuntu image ships one that only allows
     SSH — it silently rejects everything else):
     ```bash
     sudo apt install -y iptables-persistent
     sudo iptables -I INPUT -p tcp -m state --state NEW --dport 80 -j ACCEPT
     sudo iptables -I INPUT -p tcp -m state --state NEW --dport 443 -j ACCEPT
     sudo netfilter-persistent save
     ```
3. **Domain**: point an A record (`@`) at the VM's public IP (Porkbun,
   Namecheap, any registrar). The public IP survives stop/start but is
   released if the VM is terminated — never terminate and recreate it, or
   the URL and every link die.
4. **Install Docker, Caddy, and the app** (the repo is public — no creds):
   ```bash
   sudo apt update && sudo apt install -y docker.io docker-compose-v2
   sudo usermod -aG docker ubuntu && newgrp docker
   sudo apt install -y debian-keyring debian-archive-keyring apt-transport-https curl
   curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
   curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list
   sudo apt update && sudo apt install -y caddy
   sudo mkdir -p /opt/should-we && sudo chown ubuntu /opt/should-we
   git clone https://github.com/kalfasyan/should-we.git /opt/should-we
   ```
5. **Secrets** in `/opt/should-we/.env` (root-only: `chmod 600`). The app
   fails closed — no admins configured means nobody can log in:
   ```ini
   SHOULD_WE_ADMINS={"Yannis": "<password>", "Partner": "<password>"}
   SHOULD_WE_STORAGE_SECRET=<openssl rand -hex 16>
   FORWARDED_ALLOW_IPS=127.0.0.1
   ```
6. **Start**:
   ```bash
   cd /opt/should-we && docker compose up -d --build
   ```
7. **Caddy** — `/etc/caddy/Caddyfile`, then reload:
   ```
   should-we.xyz {
       reverse_proxy 127.0.0.1:8080
   }
   ```
   ```bash
   sudo caddy reload --config /etc/caddy/Caddyfile
   ```
   Caddy issues and renews the HTTPS certificate automatically. On a fresh
   host give it a couple of minutes: it retries with backoff (temporarily
   via Let's Encrypt's staging endpoint) until the DNS and ports settle.

## Deploy and use

1. Open `https://should-we.xyz` — log in as an admin.
2. Setup tab → create a project (its join link is valid 30 days).
3. Rankings tab → copy the join link to your group. The expiry line and
   "Extend 30 days" button live right under it.
4. "Copy results link" hands out the secret results link to the group.

## Updating / changing passwords

```bash
ssh ubuntu@<vm-ip> 'cd /opt/should-we && git pull && sudo docker compose up -d --build'
```

New passwords or a new storage secret: edit `/opt/should-we/.env` on the
VM, then `sudo docker compose restart`.

**Where are the admin credentials?** In `/opt/should-we/.env` on the VM
(root-only) — never in the repo. Keep a copy in a password manager the day
you create them; the file is the only copy. Lost both? Edit `.env` with new
ones and restart — old ones stop working instantly.

**Adding / removing admins** — edit the same file (each entry in the JSON
map is one admin), then restart:

```bash
sudo nano /opt/should-we/.env && sudo docker compose restart
```

Every admin sees **every project** on the instance — there is no per-admin
separation. Give admin access only to people you trust with all projects
(what the join link gates is who can *vote* in a project, not who can
*manage* it). For fully separate groups, run a second instance.

**Is the login secure?** The session cookie is HTTPS-only and signed,
password checks are constant-time, and the app fails closed if the secrets
are missing. The login form has no rate limiting, so use long random
passwords (like the generated ones) rather than words.

## Local development

`pixi run ui` works out of the box with dev-only defaults baked into the
pixi task (`yannis`/`dev`, `partner`/`dev`, secret `dev-secret`) — fine on
`localhost`, never use those in production.

## Limits and gotchas

- Free-tier VMs are small — add swap (step 1 above) or the Docker build can
  OOM on 1 GB shapes.
- Both firewalls matter: the OCI security list **and** the VM's iptables.
  Missing either looks like the site is down while everything looks fine
  inside the VM.
- If the login page ever says "No admins configured", `SHOULD_WE_ADMINS` is
  missing from `.env` — fix it and restart. The app refuses to guess rather
  than open the door.
- Session cookies are HTTPS-only (`https_only` is on in `ui.run`).
- The public IP is released only if the VM is **terminated** — back up
  `/opt/should-we/data` (it is the whole app state) rather than ever
  recreating the VM from scratch.
- Old results/join links keep working after a join-link expiry — expiry
  only blocks *new* joiners; revoke a person by regenerating their token in
  the Rankings tab.
