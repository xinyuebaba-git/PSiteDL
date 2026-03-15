#!/bin/bash
# PSiteDL 命令行启动脚本
# 使用方法：./run_psitedl.sh [URL] [选项]

set -e

# 项目目录
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$PROJECT_DIR/.venv"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}  PSiteDL v0.4.0 启动器${NC}"
echo -e "${GREEN}================================${NC}"

# 检查虚拟环境
if [ ! -d "$VENV_DIR" ]; then
    echo -e "${YELLOW}⚠️  虚拟环境不存在，正在创建...${NC}"
    cd "$PROJECT_DIR"
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -U pip
    pip install -e ".[dev]"
    echo -e "${GREEN}✅ 虚拟环境创建完成${NC}"
else
    echo -e "${GREEN}✅ 虚拟环境已存在${NC}"
fi

# 激活虚拟环境
source "$VENV_DIR/bin/activate"

# 检查依赖
echo -e "${YELLOW}📦 检查依赖...${NC}"
pip install -q -e .

# 运行 PSiteDL
if [ $# -eq 0 ]; then
    echo ""
    echo -e "${GREEN}使用方法:${NC}"
    echo "  ./run_psitedl.sh <URL> [选项]"
    echo ""
    echo -e "${GREEN}示例:${NC}"
    echo "  ./run_psitedl.sh 'https://example.com/video'"
    echo "  ./run_psitedl.sh --url-file urls.txt --concurrency 3"
    echo ""
    echo -e "${GREEN}常用选项:${NC}"
    echo "  --output-dir DIR     输出目录 (默认：~/Downloads)"
    echo "  --concurrency N      并发数 (默认：3)"
    echo "  --browser BROWSER    浏览器 (chrome/firefox/edge)"
    echo "  --bandwidth-limit N  带宽限制 (Mbps, 0=无限制)"
    echo "  --help               显示帮助"
    echo ""
else
    echo -e "${YELLOW}🚀 启动 PSiteDL...${NC}"
    echo ""
    cd "$PROJECT_DIR"
    python -m webvidgrab.site_cli "$@"
fi
