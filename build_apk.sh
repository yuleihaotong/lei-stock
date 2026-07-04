#!/bin/bash
# =============================================================================
# build_apk.sh - 一键构建APK脚本
# 支持三种方式:
#   方式1: Docker构建（推荐，无需安装Android SDK）
#   方式2: 本地Buildozer构建（需安装Android SDK）
#   方式3: 手动打包（用于开发和测试）
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=========================================="
echo "  A股短线决策工具 APK构建脚本"
echo "=========================================="
echo ""

# ─── 检查参数 ───────────────────────────────────────────────────────

BUILD_MODE="${1:-docker}"

show_usage() {
    echo "用法: $0 [docker|local|help]"
    echo ""
    echo "  docker  - 使用Docker构建（推荐）"
    echo "  local   - 使用本地Buildozer构建"
    echo "  help    - 显示此帮助"
    exit 0
}

if [ "$BUILD_MODE" = "help" ]; then
    show_usage
fi

# ─── 方式1: Docker构建 ─────────────────────────────────────────────

build_with_docker() {
    echo ""
    echo "📦 方式1: Docker构建"
    echo ""

    # 检查Docker
    if ! command -v docker &> /dev/null; then
        echo "❌ 未安装Docker！"
        echo "   请先安装Docker: https://docs.docker.com/get-docker/"
        echo ""
        echo "   或在WSL2/Ubuntu中运行:"
        echo "   curl -fsSL https://get.docker.com | sh"
        exit 1
    fi

    echo "✅ Docker已安装"

    # 构建镜像
    echo "🔨 构建Docker镜像..."
    docker build -f Dockerfile.builder -t stock-apk-builder .

    # 运行构建
    echo "🚀 开始构建APK（首次构建约30-60分钟）..."
    docker run -it --rm \
        -v "$SCRIPT_DIR:/workspace" \
        -v "$HOME/.buildozer:/root/.buildozer" \
        stock-apk-builder \
        bash -c "cd /workspace && buildozer android debug"

    # 检查结果
    APK_FILE=$(find "$SCRIPT_DIR/bin" -name "*.apk" 2>/dev/null | head -1)
    if [ -f "$APK_FILE" ]; then
        echo ""
        echo "✅ APK构建成功！"
        echo "   位置: $APK_FILE"
        ls -lh "$APK_FILE"
    else
        echo ""
        echo "❌ APK构建失败！"
        echo "   检查 buildozer_build 目录中的日志"
    fi
}

# ─── 方式2: 本地Buildozer构建 ─────────────────────────────────────

build_local() {
    echo ""
    echo "📦 方式2: 本地Buildozer构建"
    echo ""

    # 检查依赖
    local MISSING=""

    if ! command -v python3 &> /dev/null; then
        MISSING="$MISSING python3"
    fi

    if ! command -v git &> /dev/null; then
        MISSING="$MISSING git"
    fi

    if ! command -v java &> /dev/null; then
        MISSING="$MISSING java"
    fi

    if [ -n "$MISSING" ]; then
        echo "❌ 缺少依赖:$MISSING"
        echo ""
        echo "   Ubuntu/Debian安装命令:"
        echo "   sudo apt update && sudo apt install -y python3 python3-pip git openjdk-17-jdk"
        echo ""
        echo "   macOS安装命令:"
        echo "   brew install python git openjdk@17"
        echo ""
        echo "   或者使用Docker构建: $0 docker"
        exit 1
    fi

    # 检查/安装buildozer
    if ! command -v buildozer &> /dev/null; then
        echo "📥 安装Buildozer..."
        pip3 install --upgrade buildozer cython
    fi

    # 检查/安装Android SDK
    if [ ! -d "$HOME/.buildozer/android/platform" ]; then
        echo "📥 首次运行将自动下载Android SDK (约2GB)"
        echo "   请确保网络连接正常"
    fi

    echo "🚀 开始构建APK..."
    buildozer android debug

    # 检查结果
    APK_FILE=$(find "$SCRIPT_DIR/bin" -name "*.apk" 2>/dev/null | head -1)
    if [ -f "$APK_FILE" ]; then
        echo ""
        echo "✅ APK构建成功！"
        echo "   位置: $APK_FILE"
        ls -lh "$APK_FILE"
    else
        echo ""
        echo "❌ APK构建失败！"
        echo "   检查 buildozer_build 目录中的日志"
    fi
}

# ─── 执行 ───────────────────────────────────────────────────────────

case "$BUILD_MODE" in
    docker)
        build_with_docker
        ;;
    local)
        build_local
        ;;
    *)
        show_usage
        ;;
esac
