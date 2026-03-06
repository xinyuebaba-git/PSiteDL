#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   ./run_psitedl_batch.sh /absolute/path/urls.txt [/absolute/path/output_dir]
#
# Exit codes:
#   0: success
#   1: usage/input error
#   2: runtime/dependency error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$SCRIPT_DIR"
VENV_DIR="$PROJECT_DIR/.venv"
PY_BIN="$VENV_DIR/bin/python"
PIP_BIN="$VENV_DIR/bin/pip"
PSITEDL_BIN="$VENV_DIR/bin/psitedl"

URL_FILE="${1:-}"
OUTPUT_DIR="${2:-$HOME/Downloads}"

if [[ -z "$URL_FILE" ]]; then
  echo "[error] missing url file argument."
  echo "usage: $0 /absolute/path/urls.txt [/absolute/path/output_dir]"
  exit 1
fi

if [[ ! -f "$URL_FILE" ]]; then
  echo "[error] url file not found: $URL_FILE"
  exit 1
fi

mkdir -p "$OUTPUT_DIR"

if [[ ! -x "$PY_BIN" ]]; then
  echo "[setup] creating venv: $VENV_DIR"
  python3 -m venv "$VENV_DIR"
fi

echo "[setup] installing/updating dependencies..."
"$PY_BIN" -m pip install -U pip >/dev/null
"$PIP_BIN" install -e "$PROJECT_DIR" >/dev/null
"$PIP_BIN" install -U yt-dlp playwright >/dev/null

if [[ ! -x "$PSITEDL_BIN" ]]; then
  echo "[error] psitedl not found in venv after install."
  exit 2
fi

echo "[run] psitedl --url-file $URL_FILE --output-dir $OUTPUT_DIR"
"$PSITEDL_BIN" --url-file "$URL_FILE" --output-dir "$OUTPUT_DIR"

