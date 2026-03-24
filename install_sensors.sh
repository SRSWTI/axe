#!/bin/bash
# Configuration
VERSION="1.0.87"
BASE_URL="https://sensors-updates.srswti.com/darwin/arm64"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

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
    URL_FILENAME="BodegaOS%20Sensors%20Pro-${VERSION}-arm64.dmg"
    DOWNLOAD_URL="${BASE_URL}/pro/${URL_FILENAME}"
    echo -e "${GREEN}✓ High-performance system detected (>32GB RAM). Selecting 'Pro' edition.${NC}"
else
    EDITION="Standard"
    FILENAME="BodegaOS Sensors-${VERSION}-arm64.dmg"
    URL_FILENAME="BodegaOS%20Sensors-${VERSION}-arm64.dmg"
    DOWNLOAD_URL="${BASE_URL}/${URL_FILENAME}"
    echo -e "${YELLOW}✓ Standard system detected (<=32GB RAM). Selecting 'Standard' edition.${NC}"
fi

# 5. Download
DOWNLOAD_DIR="$HOME/Downloads"
SENSORS_PATH="${DOWNLOAD_DIR}/${FILENAME}"
echo -e "\n${BLUE}Downloading BodegaOS Sensors to ${DOWNLOAD_DIR}...${NC}"
echo -e "URL: $DOWNLOAD_URL\n"
curl -L -# -o "$SENSORS_PATH" "$DOWNLOAD_URL"
SENSORS_STATUS=$?

if [[ $SENSORS_STATUS -ne 0 ]]; then
    echo -e "\n${RED}✗ Download failed.${NC}"
    exit 1
fi

echo -e "\n${GREEN}✓ Download complete! File saved to: ${DOWNLOAD_DIR}${NC}"
echo -e "\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}        INSTALLATION INSTRUCTIONS${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

echo -e "\n${YELLOW}Step 1 — Open the DMG:${NC}"
echo -e "  Open ${BLUE}~/Downloads/${FILENAME}${NC}"

echo -e "\n${YELLOW}Step 2 — Install:${NC}"
echo -e "  Drag ${GREEN}BodegaOS Sensors${NC} into the ${BLUE}Applications${NC} folder"
echo -e "  Wait for the copy to finish before continuing."

echo -e "\n${YELLOW}Step 3 — Launch:${NC}"
echo -e "  Open ${GREEN}BodegaOS Sensors${NC} from your Applications folder."
echo -e "  If macOS asks to confirm, click ${GREEN}Open${NC}."

echo -e "\n${YELLOW}Step 4 — Enable the Inference Engine:${NC}"
echo -e "  Find the ${GREEN}Bodega Inference Engine${NC} toggle and turn it ${GREEN}ON${NC}."
echo -e "  Wait until the toggle turns ${GREEN}GREEN${NC} — that means it's active."

read -p "  Toggle is green? Press Enter to continue..."

echo -e "\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}  ✓ Bodega Inference Engine is ready on localhost:44468${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"