# Running should-we on a Synology NAS

The same setup as Splitwiz: one Docker image from `ghcr.io`, run by
Container Manager, reachable over HTTPS through DSM's reverse proxy. Every
step that changes the NAS is done by you, in DSM or over SSH.

## Install

1. **Container Manager**: install it from Package Center if it is missing.
2. **Data folder**: in File Station, create `docker/should-we/data`.
3. **Secrets**: the app refuses all logins until admins are configured. The
   easiest way is to run the deploy script once from your computer (see
   *Updating* below): on its first run it creates
   `/volume1/docker/should-we/.env` with one admin and prints the password.
   To do it by hand instead, SSH into the NAS and run:
   ```sh
   cd /volume1/docker/should-we && umask 077 && cat > .env <<EOT
   SHOULD_WE_ADMINS='{"Yannis": "$(openssl rand -hex 12)"}'
   SHOULD_WE_STORAGE_SECRET=$(openssl rand -hex 16)
   EOT
   cat .env   # note the password; add more admins to the JSON map later
   ```
4. **Project**: Container Manager > Project > Create, name `should-we`, path
   `/volume1/docker/should-we`, and paste
   [`docker-compose.nas.yml`](../docker-compose.nas.yml). Start it.
   - The image is published publicly at `ghcr.io/kalfasyan/should-we` by
     GitHub Actions on every push to `main`. If the package shows as private
     on GitHub, change its visibility (Packages > should-we > Package
     settings), or skip the pull entirely and use the deploy script, which
     builds the image on your computer.
5. **Address and certificate**: reuse the Synology DDNS name you set up for
   Splitwiz with a subdomain, `should-we.<your-name>.synology.me`. In
   Control Panel > Security > Certificate > Add > Get a certificate from
   Let's Encrypt, request it for that name. If the subdomain does not
   resolve, use the main hostname on another port instead (for example
   8443) and forward that port in the router as well.
6. **Reverse proxy**: Control Panel > Login Portal > Advanced > Reverse Proxy
   > Create:
   - Source: HTTPS, hostname `should-we.<your-name>.synology.me`, port 443
   - Destination: HTTP, `localhost`, port 8080
   - **Custom Header > Create > WebSocket.** should-we's pages talk to the
     server over a WebSocket; without these two headers the page loads but
     buttons do nothing.
7. **Certificate**: Control Panel > Security > Certificate > Settings, assign
   the new certificate to that reverse-proxy entry.
8. Open `https://should-we.<your-name>.synology.me`, log in with the admin
   from step 3, and create a project.

Logins only work over HTTPS (the session cookie is HTTPS-only), so always use
the reverse-proxy address, not `http://<nas-ip>:8080`.

## Updating

From a computer with Docker and SSH access to the NAS:

```sh
scripts/deploy-to-nas.sh you@your-nas-address
```

It builds the image locally, copies it over and recreates the container. Or,
after a push to `main`, pull the new image in Container Manager (Image >
`ghcr.io/kalfasyan/should-we` > Update) and then Project > should-we > Action
> Build. Projects and votes stay in `data/`.

## Admins and passwords

Edit `/volume1/docker/should-we/.env` (each entry in the `SHOULD_WE_ADMINS`
JSON map is one admin), then restart the project in Container Manager.

## Backups

Everything (projects, votes, test users, login sessions) is in
`/volume1/docker/should-we/data`. Add `/volume1/docker/should-we` to a Hyper
Backup task, and use "Export data" on a project's Rankings tab for a
portable copy.

## Moving projects from the Oracle VM

Copy the VM's `/opt/should-we/data` into the NAS data folder, for example:

```sh
ssh ubuntu@<vm-ip> 'sudo tar -C /opt/should-we -czf - data' \
  | ssh you@your-nas-address 'tar -C /volume1/docker/should-we -xzf -'
```

Join and voting links keep working once the group uses the new address in
place of `should-we.xyz` (or point that domain at the NAS).
