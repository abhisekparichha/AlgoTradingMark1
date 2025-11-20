#!/usr/bin/env bash
set -euo pipefail

# Pulls or clones the Quant India repository onto a local drive.
# Usage:
#   REPO_URL=https://github.com/... TARGET_DIR=$HOME/quant-india ./scripts/pull_repo.sh

REPO_URL=${REPO_URL:-https://github.com/abhisekparichha/AlgoTradingMark1.git}
TARGET_DIR=${TARGET_DIR:-"$HOME/quant-india"}

if [ -d "$TARGET_DIR/.git" ]; then
  echo "[pull_repo] Repository already exists. Updating $TARGET_DIR ..."
  git -C "$TARGET_DIR" fetch --all --prune
  git -C "$TARGET_DIR" checkout main
  git -C "$TARGET_DIR" pull --ff-only origin main
else
  echo "[pull_repo] Cloning $REPO_URL into $TARGET_DIR ..."
  git clone "$REPO_URL" "$TARGET_DIR"
fi

echo "[pull_repo] Repository ready at $TARGET_DIR"
