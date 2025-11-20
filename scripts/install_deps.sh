#!/usr/bin/env bash
set -euo pipefail

# Creates a virtual environment and installs all project dependencies.
# Usage:
#   ./scripts/install_deps.sh
#   VENV_PATH=.venv-prod ./scripts/install_deps.sh

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_PATH=${VENV_PATH:-"$ROOT_DIR/.venv"}

python3 -m venv "$VENV_PATH"
# shellcheck disable=SC1090
source "$VENV_PATH/bin/activate"

pip install --upgrade pip setuptools wheel
pip install -e "$ROOT_DIR"[dev]

echo "[install_deps] Virtualenv: $VENV_PATH"
echo "[install_deps] Installed project in editable mode with dev extras."
