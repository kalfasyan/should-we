#!/bin/sh
# Builds should-we on this computer and replaces the running container on the
# NAS. Everything in pb_data is kept and migrations run on start.
#
#   scripts/deploy-to-nas.sh user@nas-address
#
# Asks for the NAS password twice: once to copy, once for sudo.
set -e
TARGET=${1:?usage: $0 user@nas-address}
DIR=/volume1/docker/should-we
IMAGE=ghcr.io/selfhostit/should-we:2

cd "$(dirname "$0")/.."
docker build --platform linux/amd64 -t "$IMAGE" .

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
docker save "$IMAGE" | gzip > "$tmp/should-we-image.tar.gz"
cp docker-compose.yml "$tmp/"

echo "Copying to $TARGET:$DIR"
tar -C "$tmp" -cf - should-we-image.tar.gz docker-compose.yml | ssh "$TARGET" "mkdir -p $DIR/pb_data && tar -C $DIR -xf -"

# sudo on DSM doesn't search /usr/local/bin, so call docker by its full path
ssh -t "$TARGET" "cd $DIR && sudo /usr/local/bin/docker load -i should-we-image.tar.gz \
  && sudo /usr/local/bin/docker compose up -d --force-recreate \
  && rm should-we-image.tar.gz && sleep 5 && curl -s http://127.0.0.1:8091/api/health && echo"
