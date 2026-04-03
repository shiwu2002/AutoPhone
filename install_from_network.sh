#!/bin/bash

# AutoPhone 一键网络安装脚本
# 用途：从 GitHub 下载并安装 AutoPhone 命令行工具

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
    # 重新加载 PATH
    export PATH="$HOME/.local/bin:$PATH"
    echo_green "pipx 安装完成"
else
    echo_green "pipx 已安装"
fi

# 临时目录
TEMP_DIR=$(mktemp -d)
echo_yellow "正在下载 AutoPhone 到临时目录..."

# 下载项目（使用 GitHub 的 zip 文件）
curl -L https://github.com/shiwu2002/AutoPhone/archive/main.zip -o "$TEMP_DIR/autophone.zip"
unzip "$TEMP_DIR/autophone.zip" -d "$TEMP_DIR/"

PROJECT_DIR="$TEMP_DIR/AutoPhone-main"

echo_yellow "正在安装 AutoPhone..."

# 使用 pipx 安装项目
cd "$PROJECT_DIR"
python3 -m pipx install --force .

# 清理临时文件
rm -rf "$TEMP_DIR"

echo_green "AutoPhone 安装完成！"
echo_green "你现在可以在任何地方使用 'autophone' 命令了"
echo_green ""
echo_green "使用示例:"
echo_green "  autophone --help"
echo_green "  autophone run \"打开微信\""
echo_green "  autophone wifi list"
echo_green ""
echo_green "要更新 AutoPhone，只需再次运行此脚本即可。"