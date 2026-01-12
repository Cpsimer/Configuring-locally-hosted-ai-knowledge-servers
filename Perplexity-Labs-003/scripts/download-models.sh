#!/bin/bash
# ~/ai-idp/scripts/download-models.sh
# NGC & HuggingFace Model Downloader
# Integration: GitHub Student Pack, NGC Catalog, Meta Developer
# Version: 2.1 | Date: 2026-01-12

set -euo pipefail

# Configuration
MODEL_DIR="/mnt/models"
CACHE_DIR="/mnt/cache"
NGC_CLI_VERSION="3.41.0"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo "=========================================================="
echo "AI IDP Model Downloader (NGC & HuggingFace Integration)"
echo "Utilizing: GitHub Student Pack, NVIDIA Developer Access"
echo "=========================================================="

# 1. Install NGC CLI if missing (NVIDIA Developer Program)
install_ngc() {
    if ! command -v ngc &> /dev/null; then
        echo -e "${YELLOW}Installing NGC CLI...${NC}"
        wget -q "https://ngc.nvidia.com/downloads/ngccli_linux.zip" -O ngccli_linux.zip
        unzip -q ngccli_linux.zip
        chmod +x ngc-cli/ngc
        sudo mv ngc-cli/ngc /usr/local/bin/
        rm -rf ngc-cli ngccli_linux.zip
        echo -e "${GREEN}NGC CLI installed.${NC}"
    fi
}

# 2. Configure Credentials
setup_credentials() {
    # Check for NGC Key
    if [ -z "${NGC_API_KEY:-}" ]; then
        echo -e "${RED}ERROR: NGC_API_KEY not set.${NC}"
        echo "Export your key from https://ngc.nvidia.com/setup/api-key"
        echo "Usage: NGC_API_KEY=... ./download-models.sh"
        exit 1
    fi

    # Configure NGC
    ngc config set <<EOF > /dev/null
$NGC_API_KEY
json
no-nvc-cache
EOF
    echo -e "${GREEN}NGC Configured.${NC}"

    # Check for HuggingFace Token (GitHub Student Pack Benefit)
    if [ -z "${HF_TOKEN:-}" ]; then
        echo -e "${YELLOW}WARNING: HF_TOKEN not set. Some gated models (Llama 3) may fail.${NC}"
        echo "Use your GitHub Student Pack Pro token."
    else
        huggingface-cli login --token "$HF_TOKEN" --add-to-git-credential
    fi
}

# 3. Download Models
download_models() {
    mkdir -p "$MODEL_DIR"
    
    # --- TIER 1: RTX 5070 Ti (FP8) ---
    echo -e "\n${YELLOW}Downloading Tier 1 Models (FP8 for RTX 5070 Ti)...${NC}"
    
    # Llama 3.1 8B Instruct (FP8) - From NGC
    if [ ! -d "$MODEL_DIR/llama-3.1-8b-fp8" ]; then
        echo "Downloading Llama 3.1 8B FP8..."
        ngc registry model download-version "nvidia/llama-3_1-8b-instruct:1.0" \
            --dest "$MODEL_DIR/llama-3.1-8b-fp8"
    else
        echo "Llama 3.1 8B FP8 already exists."
    fi

    # --- TIER 2: CPU (Q4_K_M) ---
    echo -e "\n${YELLOW}Downloading Tier 2 Models (Q4 for Ryzen 9900X)...${NC}"
    
    # Llama 3.2 3B Instruct
    mkdir -p "$MODEL_DIR/llama-3.2-3b-q4"
    if [ ! -f "$MODEL_DIR/llama-3.2-3b-q4/Llama-3.2-3B-Instruct-Q4_K_M.gguf" ]; then
        huggingface-cli download "bartowski/Llama-3.2-3B-Instruct-GGUF" \
            "Llama-3.2-3B-Instruct-Q4_K_M.gguf" \
            --local-dir "$MODEL_DIR/llama-3.2-3b-q4"
    fi

    # --- TIER 3: HYBRID (70B) ---
    echo -e "\n${YELLOW}Downloading Tier 3 Models (70B Hybrid)...${NC}"
    
    # Llama 3.3 70B Instruct
    mkdir -p "$MODEL_DIR/llama-3.3-70b-q4"
    if [ ! -f "$MODEL_DIR/llama-3.3-70b-q4/Llama-3.3-70B-Instruct-Q4_K_M.gguf" ]; then
        huggingface-cli download "bartowski/Llama-3.3-70B-Instruct-GGUF" \
            "Llama-3.3-70B-Instruct-Q4_K_M.gguf" \
            --local-dir "$MODEL_DIR/llama-3.3-70b-q4"
    fi

    # --- TIER 4: EDGE (1B) ---
    echo -e "\n${YELLOW}Downloading Tier 4 Models (1B for Jetson/NPU)...${NC}"
    
    # Llama 3.2 1B Instruct
    mkdir -p "$MODEL_DIR/llama-3.2-1b-q4"
    if [ ! -f "$MODEL_DIR/llama-3.2-1b-q4/Llama-3.2-1B-Instruct-Q4_K_M.gguf" ]; then
        huggingface-cli download "bartowski/Llama-3.2-1B-Instruct-GGUF" \
            "Llama-3.2-1B-Instruct-Q4_K_M.gguf" \
            --local-dir "$MODEL_DIR/llama-3.2-1b-q4"
    fi
}

# 4. Verify Downloads
verify_downloads() {
    echo -e "\n${GREEN}Verifying downloads...${NC}"
    du -sh "$MODEL_DIR"/*
    echo -e "\nTotal Model Size: $(du -sh "$MODEL_DIR" | cut -f1)"
}

# Main
install_ngc
setup_credentials
download_models
verify_downloads
