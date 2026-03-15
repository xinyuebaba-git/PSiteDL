#!/bin/bash
# PSiteDL GUI 启动脚本

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PYTHON="$PROJECT_DIR/.venv/bin/python"
BREW_PYTHON="/opt/homebrew/bin/python3.11"

echo "启动 PSiteDL GUI..."

cd "$PROJECT_DIR"

if [ -x "$VENV_PYTHON" ]; then
  exec env TK_SILENCE_DEPRECATION=1 PYTHONPATH="$PROJECT_DIR/src" "$VENV_PYTHON" -m webvidgrab.site_gui "$@"
elif [ -x "$BREW_PYTHON" ]; then
  exec env TK_SILENCE_DEPRECATION=1 PYTHONPATH="$PROJECT_DIR/src" "$BREW_PYTHON" -m webvidgrab.site_gui "$@"
else
  exec env TK_SILENCE_DEPRECATION=1 PYTHONPATH="$PROJECT_DIR/src" python3 -m webvidgrab.site_gui "$@"
fi
