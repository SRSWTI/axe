#!/bin/bash

# Configuration
VERSION="1.0.15"
BASE_URL="https://sensors-updates.srswti.com/darwin/arm64"
MIN_KERNEL_VERSION=26 # Tahoe (Darwin 26)

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== BodegaOS Sensors Installer ===${NC}"
echo -e "${BLUE}Checking system requirements...${NC}"

# 1. Check OS and Architecture
OS="$(uname -s)"
ARCH="$(uname -m)"

if [[ "$OS" != "Darwin" ]]; then
    echo -e "${RED}Error: This script is only for macOS (Darwin). Detected: $OS${NC}"
    exit 1
fi

if [[ "$ARCH" != "arm64" ]]; then
    echo -e "${RED}Error: BodegaOS Sensors requires Apple Silicon (arm64). Detected: $ARCH${NC}"
    exit 1
fi

# 2. Check macOS Version (Tahoe is macOS 16.x)
MACOS_VERSION=$(sw_vers -productVersion)
MAJOR_VERSION=$(echo "$MACOS_VERSION" | cut -d. -f1)

echo -e "  • macOS Version: $MACOS_VERSION"

if (( MAJOR_VERSION < 16 )); then
    echo -e "${RED}Error: Requires macOS Tahoe (Version 16.x) or newer. You are running macOS $MACOS_VERSION.${NC}"
    exit 1
fi

# 3. Check RAM
RAM_BYTES=$(sysctl -n hw.memsize)
RAM_GB=$((RAM_BYTES / 1024 / 1024 / 1024))
echo -e "  • System RAM: ${RAM_GB} GB"

# 4. Determine Edition
if (( RAM_GB > 32 )); then
    EDITION="Pro"
    FILENAME="BodegaOS Sensors Pro-${VERSION}-arm64.dmg"
    # URL encoded filename for the link
    URL_FILENAME="BodegaOS%20Sensors%20Pro-${VERSION}-arm64.dmg"
    DOWNLOAD_URL="${BASE_URL}/pro/${URL_FILENAME}"
    echo -e "${GREEN}✓ High-performance system detected (>32GB RAM). Selecting 'Pro' edition.${NC}"
else
    EDITION="Standard"
    FILENAME="BodegaOS Sensors-${VERSION}-arm64.dmg"
    URL_FILENAME="BodegaOS%20Sensors-${VERSION}-arm64.dmg"
    # Standard version is at the root of /darwin/arm64/
    DOWNLOAD_URL="${BASE_URL}/${URL_FILENAME}"
    echo -e "${YELLOW}✓ Standard system detected (<=32GB RAM). Selecting 'Standard' edition.${NC}"
fi

# 5. Download
DOWNLOAD_DIR="$HOME/Downloads"
FULL_PATH="${DOWNLOAD_DIR}/${FILENAME}"

echo -e "\n${BLUE}Downloading to ${DOWNLOAD_DIR}...${NC}"
echo -e "URL: $DOWNLOAD_URL\n"

# Use curl to download to specific path
curl -L -# -o "$FULL_PATH" "$DOWNLOAD_URL"

if [[ $? -eq 0 ]]; then
    echo -e "\n${GREEN}✓ Download complete: ${FILENAME}${NC}"
    echo -e "${BLUE}To install:${NC}"
    echo -e "1. Run: open \"${FULL_PATH}\""
    echo -e "2. Drag and drop the app icon into the Applications folder."
    echo -e "3. Click on the app in Applications to start using it."
else
    echo -e "\n${RED}✗ Download failed.${NC}"
    exit 1
fi
