#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLIENT_DIR="$ROOT_DIR/client"
SERVER_PUBLIC_DIR="$ROOT_DIR/server/public"

cd "$CLIENT_DIR"
npm ci
npm run build

mkdir -p "$SERVER_PUBLIC_DIR"
find "$SERVER_PUBLIC_DIR" -mindepth 1 -maxdepth 1 -exec rm -rf {} +
cp -R dist/. "$SERVER_PUBLIC_DIR"/
