# Dockerfile.builder - Buildozer APK构建环境
# 使用方法:
#   docker build -f Dockerfile.builder -t stock-apk-builder .
#   docker run -it --rm -v ${PWD}:/workspace stock-apk-builder

FROM ubuntu:22.04

LABEL description="A股短线决策工具 APK构建环境"
LABEL maintainer="stocktool"

ENV DEBIAN_FRONTEND=noninteractive
ENV BUILD_DIR=/workspace

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    python3-venv \
    python3-dev \
    git \
    wget \
    curl \
    unzip \
    build-essential \
    ccache \
    libncurses5 \
    libncurses5-dev \
    zlib1g-dev \
    libssl-dev \
    libffi-dev \
    libsqlite3-dev \
    autoconf \
    automake \
    libtool \
    pkg-config \
    openjdk-17-jdk \
    openjdk-17-jre \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 安装Cython和Buildozer
RUN pip3 install --upgrade pip setuptools wheel && \
    pip3 install cython==0.29.33 buildozer

# 配置Java环境
ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
ENV PATH=$JAVA_HOME/bin:$PATH

# 创建工作目录
WORKDIR /workspace

# 默认命令
CMD ["bash", "-c", "cd /workspace && buildozer android debug"]
