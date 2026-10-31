#!/usr/bin/env bash
# usage: docker-compose.sh [up|down|check|ps|logs|build]
set -euo pipefail
umask 077

PROJECT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
COMPOSE_FILE="$PROJECT_DIR/compose.yaml"
PROJECT_NAME=solarman-exporter
CONTAINER_NAME=solarman-exporter
MODE=${1:-up}

die() { printf 'error: %s\n' "$*" >&2; exit 1; }

case $MODE in
    up | down | check | ps | logs | build) ;;
    *) die "usage: $0 [up|down|check|ps|logs|build]" ;;
esac

command -v docker >/dev/null 2>&1 || die "docker is not installed"
docker info >/dev/null 2>&1 || die "the Docker daemon is not running"
docker compose version >/dev/null 2>&1 || die "the docker compose v2+ plugin is required"

[[ -f $COMPOSE_FILE ]] || die "missing $COMPOSE_FILE"
[[ -f $PROJECT_DIR/.env ]] || die "missing $PROJECT_DIR/.env (start from .env.example)"

compose() { docker compose --project-directory "$PROJECT_DIR" -p "$PROJECT_NAME" -f "$COMPOSE_FILE" "$@"; }

compose config --quiet

container_exists() { docker container inspect "$CONTAINER_NAME" >/dev/null 2>&1; }

foreign_container() {
    container_exists || return 1
    local owner
    owner=$(docker inspect --format '{{ index .Config.Labels "com.docker.compose.project" }}' "$CONTAINER_NAME" 2>/dev/null || true)
    [[ $owner != "$PROJECT_NAME" ]]
}

port_in_use() { (exec 3<>/dev/tcp/127.0.0.1/9800) 2>/dev/null; }

case $MODE in
    check)
        printf 'ok: %s validates, .env present, nothing started\n' "$COMPOSE_FILE"
        foreign_container && printf 'note: container %s exists outside this project; "up" will refuse until it is removed\n' "$CONTAINER_NAME"
        if ! container_exists && port_in_use; then
            printf 'note: port 9800 is already in use; stop solarman-exporter.service before "up"\n'
        fi
        exit 0
        ;;
    build)
        compose build
        exit 0
        ;;
    down)
        compose down --remove-orphans
        exit 0
        ;;
    ps)
        compose ps
        exit 0
        ;;
    logs)
        compose logs --tail=100 -f
        exit 0
        ;;
esac

foreign_container && die "container $CONTAINER_NAME exists outside this project; remove it first (docker rm $CONTAINER_NAME)"
if ! container_exists && port_in_use; then
    die "port 9800 is already in use; stop solarman-exporter.service (sudo systemctl stop solarman-exporter) first"
fi

compose up -d --build --remove-orphans
compose ps
printf 'started %s\nlogs: %s logs\n' "$PROJECT_NAME" "$0"
