#!/bin/sh
# Builds should-we on this computer and replaces the running container on the
# NAS. Projects and votes in data/ are kept.
#
#   scripts/deploy-to-nas.sh user@nas-address
#
# On the first run it also creates the .env file on the NAS with one admin
# account and prints that admin's password once.
# Asks for the NAS password a few times: to copy, and once for sudo.
set -e
TARGET=${1:?usage: $0 user@nas-address}
DIR=/volume1/docker/should-we
IMAGE=ghcr.io/kalfasyan/should-we:latest

cd "$(dirname "$0")/.."
docker build --platform linux/amd64 -t "$IMAGE" .

if ! ssh "$TARGET" "test -f $DIR/.env"; then
  printf 'Admin name for the first login [admin]: '
  read -r admin
  admin=${admin:-admin}
  password=$(openssl rand -hex 12)
  secret=$(openssl rand -hex 16)
  printf "SHOULD_WE_ADMINS='{\"%s\": \"%s\"}'\nSHOULD_WE_STORAGE_SECRET=%s\n" \
    "$admin" "$password" "$secret" |
    ssh "$TARGET" "mkdir -p $DIR/data && umask 077 && cat > $DIR/.env"
  echo "Created $DIR/.env. Log in as '$admin' with password: $password"
  echo "Save it in your password manager; it is not shown again."
fi

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
docker save "$IMAGE" | gzip > "$tmp/should-we-image.tar.gz"
cp docker-compose.nas.yml "$tmp/docker-compose.yml"

echo "Copying to $TARGET:$DIR"
tar -C "$tmp" -cf - should-we-image.tar.gz docker-compose.yml | ssh "$TARGET" "mkdir -p $DIR/data && tar -C $DIR -xf -"

# sudo on DSM doesn't search /usr/local/bin, so call docker by its full path
ssh -t "$TARGET" "cd $DIR && sudo /usr/local/bin/docker load -i should-we-image.tar.gz \
  && sudo /usr/local/bin/docker compose up -d --force-recreate \
  && rm should-we-image.tar.gz && sleep 5 \
  && curl -s -o /dev/null -w 'should-we answered HTTP %{http_code}\n' http://127.0.0.1:8080/"
