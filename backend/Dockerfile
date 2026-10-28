# BASE_REGISTRY 默认走 docker.io；国内拉不到 docker.io 时可换 daocloud / 阿里云 / 自建镜像源：
#   docker-compose build --build-arg BASE_REGISTRY=docker.m.daocloud.io
# 或写到 docker-compose.yml 的 build.args / 环境变量里
ARG BASE_REGISTRY=docker.io
FROM ${BASE_REGISTRY}/library/python:3.11-slim

ARG APT_MIRROR=mirrors.tuna.tsinghua.edu.cn
ARG PIP_INDEX=https://pypi.tuna.tsinghua.edu.cn/simple

RUN rm -f /etc/apt/sources.list && \
    rm -rf /etc/apt/sources.list.d/* && \
    echo "deb https://${APT_MIRROR}/debian bookworm main contrib non-free non-free-firmware" > /etc/apt/sources.list && \
    echo "deb https://${APT_MIRROR}/debian bookworm-updates main contrib non-free non-free-firmware" >> /etc/apt/sources.list && \
    echo "deb https://${APT_MIRROR}/debian-security bookworm-security main contrib non-free non-free-firmware" >> /etc/apt/sources.list && \
    apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg curl && \
    rm -rf /var/lib/apt/lists/*

ENV PATH="/usr/bin:${PATH}"
ENV HF_ENDPOINT=https://hf-mirror.com

WORKDIR /app

# 先复制 requirements.txt 利用层缓存
COPY ./backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -i ${PIP_INDEX} -r requirements.txt
# CloakBrowser（抖音游客 Cookie）需要 Chromium 运行库 + 中日韩/emoji 字体。
# 包名按 Debian 12 (bookworm) 列出；不能用 `playwright install-deps`，它在本镜像里会去找
# Ubuntu 24.04 的 *t64 包名而失败。浏览器二进制本身（~200MB）在首次启动时按需下载到
# CLOAKBROWSER_CACHE_DIR（见 docker-compose.yml）。
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libasound2 libatk-bridge2.0-0 libatk1.0-0 libatspi2.0-0 libcairo2 libcups2 \
        libdbus-1-3 libdrm2 libexpat1 libgbm1 libglib2.0-0 libgtk-3-0 libnspr4 libnss3 \
        libpango-1.0-0 libudev1 libx11-6 libx11-xcb1 libxcb1 libxcomposite1 libxcursor1 \
        libxdamage1 libxext6 libxfixes3 libxi6 libxkbcommon0 libxrandr2 libxshmfence1 libxtst6 \
        fonts-liberation fonts-noto-color-emoji fonts-freefont-ttf fonts-unifont \
        fonts-ipafont-gothic fonts-wqy-zenhei fonts-tlwg-loma-otf && \
    rm -rf /var/lib/apt/lists/*

# 再复制应用代码（频繁变动不影响 pip 缓存层）
COPY ./backend /app

CMD ["python", "main.py"]
