# Base image with Python 3.12
FROM python:3.12-slim

# Prevent interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    QT_QPA_PLATFORM=xcb

# Install system dependencies:
# - Qt6/PyQt6 GUI runtime libraries (XCB, OpenGL, EGL, fonts, DBus)
# - Archive extraction utilities (7z, bzip2, tar, gzip, xz, unzip, zip)
# - Dev & testing tools (xvfb for headless GUI testing, git, curl, build tools)
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Qt6 / GUI requirements
    libgl1 \
    libegl1 \
    libgl1-mesa-dri \
    libxkbcommon-x11-0 \
    libxcb-cursor0 \
    libxcb-icccm4 \
    libxcb-image0 \
    libxcb-keysyms1 \
    libxcb-randr0 \
    libxcb-render-util0 \
    libxcb-shape0 \
    libxcb-sync1 \
    libxcb-xfixes0 \
    libxcb-xinerama0 \
    libxcb-xinput0 \
    libdbus-1-3 \
    libfontconfig1 \
    libglib2.0-0 \
    libxrender1 \
    libxi6 \
    # Archive tools
    p7zip-full \
    bzip2 \
    tar \
    gzip \
    xz-utils \
    unzip \
    zip \
    # Dev & headless testing
    xvfb \
    xauth \
    x11-utils \
    git \
    procps \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /workspace

# Install Python packages
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir \
       py7zr \
       pytest \
       pytest-qt

# Default command keeps the container alive for dev or running tests
CMD ["bash"]
