#!/usr/bin/env bash
# Create an isolated virtualenv and install pinned requirements.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="${VENV_DIR:-${ROOT_DIR}/.venv}"
PYTHON_BIN="${PYTHON_BIN:-python3}"

echo "🔧 Creating virtualenv at ${VENV_DIR} ..."
"${PYTHON_BIN}" -m venv "${VENV_DIR}"
source "${VENV_DIR}/bin/activate"

echo "⬆️  Upgrading pip ..."
pip install --upgrade pip

echo "📦 Installing requirements.txt ..."
pip install -r "${ROOT_DIR}/requirements.txt"

echo
echo "✅ Virtualenv ready."
echo "To use: source ${VENV_DIR}/bin/activate"
