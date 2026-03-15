#!/bin/bash
# PSiteDL GUI 启动脚本

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$PROJECT_DIR/.venv"

echo "🚀 启动 PSiteDL GUI..."

# 激活虚拟环境
source "$VENV_DIR/bin/activate"

# 运行 GUI
cd "$PROJECT_DIR"
python -m webvidgrab.site_gui "$@"
