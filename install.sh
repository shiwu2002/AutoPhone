#!/bin/bash

# AutoPhone 一键安装/更新脚本
# 用途：自动安装或更新 AutoPhone 命令行工具

set -e  # 遇到错误立即退出

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo_green() {
    echo -e "${GREEN}$1${NC}"
}

echo_yellow() {
    echo -e "${YELLOW}$1${NC}"
}

echo_red() {
    echo -e "${RED}$1${NC}"
}

# 获取当前脚本目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 检查是否安装了 Python 3
if ! command -v python3 &>/dev/null; then
    echo_red "错误: 未找到 python3，请先安装 Python 3.11 或更高版本"
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
if [[ $(printf '%s\n' "3.11" "$PYTHON_VERSION" | sort -V | head -n1) != "3.11" ]]; then
    echo_red "错误: 需要 Python 3.11 或更高版本，当前版本: $PYTHON_VERSION"
    exit 1
fi

# 检查是否安装了 pipx
if ! command -v pipx &>/dev/null; then
    echo_yellow "pipx 未安装，正在安装 pipx..."
    python3 -m pip install --user pipx
    python3 -m pipx ensurepath
    echo_green "pipx 安装完成"
else
    echo_green "pipx 已安装"
fi

# 检查当前目录是否为 AutoPhone 项目
if [[ ! -f "$SCRIPT_DIR/pyproject.toml" || ! -f "$SCRIPT_DIR/phone_agent/cli.py" ]]; then
    echo_red "错误: 未在 AutoPhone 项目根目录中找到必要的文件"
    exit 1
fi

echo_yellow "正在安装/更新 AutoPhone..."

# 如果已经安装过，先卸载
if pipx list | grep -q autophone; then
    echo_yellow "发现已安装的 AutoPhone，正在更新..."
    pipx upgrade autophone || pipx uninstall autophone
else
    echo_green "首次安装 AutoPhone..."
fi

# 使用 pipx 安装当前项目
cd "$SCRIPT_DIR"
python3 -m pipx install --force .

echo_green "AutoPhone 安装/更新完成！"
echo_green "你现在可以在任何地方使用 'autophone' 命令了"
echo_green ""
echo_green "使用示例:"
echo_green "  autophone --help"
echo_green "  autophone run \"打开微信\""
echo_green "  autophone wifi list"
echo_green ""
echo_green "要更新 AutoPhone，只需进入项目目录并运行此脚本即可。"