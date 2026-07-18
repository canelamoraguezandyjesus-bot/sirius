#!/usr/bin/env bash
set -euo pipefail

readonly UV_VERSION="0.11.29"
readonly BOOTSTRAP_DIR="${TMPDIR:-/tmp}/sirius-cloud-uv-${UV_VERSION}"
readonly PYTHON_MIRROR="https://releases.astral.sh/github/python-build-standalone/releases/download"

run() {
  printf '>>> '
  printf '%q ' "$@"
  printf '\n'
  "$@"
}

if command -v python3 >/dev/null 2>&1; then
  bootstrap_python="python3"
elif command -v python >/dev/null 2>&1; then
  bootstrap_python="python"
else
  echo "No bootstrap Python interpreter is available." >&2
  exit 1
fi

if [ ! -x "${BOOTSTRAP_DIR}/bin/uv" ]; then
  run "${bootstrap_python}" -m venv "${BOOTSTRAP_DIR}"
  run "${BOOTSTRAP_DIR}/bin/python" -m pip install \
    --disable-pip-version-check \
    --no-input \
    "uv==${UV_VERSION}"
fi

cd "$(dirname "${BASH_SOURCE[0]}")/.."

export UV_PYTHON_INSTALL_MIRROR="${PYTHON_MIRROR}"
readonly UV="${BOOTSTRAP_DIR}/bin/uv"

run "${UV}" --version
run "${UV}" python install 3.14
run "${UV}" sync --frozen
run "${UV}" run python -c \
  'import sys; assert sys.version_info[:2] == (3, 14), sys.version; print(sys.version)'
run "${UV}" run ruff format --check .
run "${UV}" run ruff check .
run "${UV}" run mypy src tests
run "${UV}" run pytest
run git diff --check
run git status --short

printf '%s\n' "CLOUD_CHECKS_PASSED"
