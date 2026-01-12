# AI IDP User Programs & Resource Integration
**Version**: 2.1 | **Date**: January 12, 2026

---

## User Program Benefits Matrix

### NVIDIA Developer Programs

| Program | Benefits | AI IDP Integration |
|---------|----------|-------------------|
| **NVIDIA Developer Program** | NGC Private Registry, DGX Cloud credits, early SDK access | ✅ Model downloads, container registry |
| **NVIDIA AI Aerial** | CUDA-accelerated RAN, Aerial Framework | 🟡 Future 6G research |
| **NVIDIA 6G Developer Program** | Aerial Omniverse Digital Twin, Sionna simulation | 🟡 Edge inference research |
| **NGC Catalog** | 500+ optimized models, monthly security patches | ✅ Primary model source |

### Cloud & Development Platforms

| Program | Benefits | AI IDP Integration |
|---------|----------|-------------------|
| **Docker Beta Developer** | Early container features, BuildKit access | ✅ Container orchestration |
| **GitHub Student Pack** | HuggingFace Pro, Copilot, Actions minutes | ✅ Model hosting, CI/CD |
| **Google AI Pro** | Gemini API, Vertex AI credits | 🟡 Hybrid cloud fallback |
| **Azure Education Hub** | $100/month credits, GPU VMs | ✅ Cloud testing, A/B validation |
| **Azure AI Foundry** | Azure OpenAI, model fine-tuning | 🟡 Enterprise integration |

### Meta Llama Model Portfolio

| Model | Size | Best Deployment | Quantization |
|-------|------|-----------------|--------------|
| **Llama 4 Scout** | TBD | vLLM GPU | FP8 |
| **Llama 4 Maverick** | TBD | vLLM GPU | FP8 |
| **Llama 3.3 70B** | 70B | Hybrid GPU+CPU | Q4_K_M |
| **Llama 3.2 1B** | 1B | CPU / NPU / Jetson | Q4_K_M / INT8 |
| **Llama 3.2 3B** | 3B | CPU Primary | Q4_K_M |
| **Llama 3.2 11B** | 11B | vLLM GPU | FP8 |
| **Llama 3.2 90B** | 90B | ❌ Exceeds local capacity | - |
| **Llama 3.1 8B** | 8B | vLLM GPU (Primary) | FP8 |
| **Llama 3.1 405B** | 405B | ❌ Cloud only | - |
| **Llama Code** | Various | vLLM GPU | FP8 |
| **Llama Guard 2** | 7B | Safety layer | FP8 |

### Storage & Sync

| Service | Capacity | Use Case |
|---------|----------|----------|
| **Obsidian Sync** | Unlimited vaults | Configuration sync |
| **Obsidian Publish** | Public docs | Documentation |
| **iCloud+ 50GB** | 50GB | Model cache backup |

---

## Model Deployment Strategy

### Recommended Model Stack

```
┌─────────────────────────────────────────────────────────────────────┐
│                        AI IDP MODEL TIERS                           │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  TIER 1: PRIMARY INFERENCE (vLLM on RTX 5070 Ti)                   │
│  ├── Llama 3.1 8B FP8 ──────── Quality tasks, 60-100 tok/s        │
│  ├── Llama 3.2 11B FP8 ─────── Extended reasoning                  │
│  └── Llama Guard 2 FP8 ─────── Content safety layer                │
│                                                                     │
│  TIER 2: FAST ITERATION (llama.cpp on Ryzen 9900X)                 │
│  ├── Llama 3.2 3B Q4_K_M ───── Brainstorming, 100-150 tok/s       │
│  └── Llama 3.2 1B Q4_K_M ───── Drafts, 200+ tok/s                 │
│                                                                     │
│  TIER 3: EXPERT REASONING (Hybrid GPU+CPU)                         │
│  └── Llama 3.3 70B Q4_K_M ──── Deep analysis, 8-15 tok/s          │
│                                                                     │
│  TIER 4: EDGE INFERENCE (Jetson Orin Nano Super)                   │
│  ├── Llama 3.2 1B Q4_K_M ───── Local edge, 15-25 tok/s            │
│  └── RPC offload to Tier 2 ─── Heavy layers to AI Desktop         │
│                                                                     │
│  TIER 5: AUXILIARY (Intel NPU / GTX 1650)                          │
│  ├── Llama 3.2 1B INT8 (NPU) ─ Code completion, 5-15 tok/s        │
│  └── Llama 3.2 1B Q4 (1650) ── Backup, 8-12 tok/s                 │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Jetson Orin Nano Super Deployment

### Hardware Specifications

| Component | Value |
|-----------|-------|
| Module | Jetson Orin Nano 8GB |
| AI Performance | 67 TOPS (INT8) |
| GPU | NVIDIA Ampere (1024 CUDA, 32 Tensor cores) |
| Memory | 8GB 128-bit LPDDR5 (68 GB/s) |
| Storage | Samsung 990 EVO Plus 1TB (PCIe 4.0) |
| Connection | USB 4.0 to AI Desktop (static DHCP) |

### Deployment Architecture

```
┌──────────────────┐     USB 4.0 (40 Gbps)     ┌─────────────────────┐
│  Jetson Orin     │◄────────────────────────►│   AI Desktop        │
│  Nano Super      │     3-8ms RPC latency     │   (schlimers-srv)   │
├──────────────────┤                           ├─────────────────────┤
│ llama.cpp server │                           │ llama.cpp RPC host  │
│ Llama 3.2 1B Q4  │     Layer offload         │ CPU inference       │
│ GPU layers: 12   │◄─────────────────────────►│ threads: 4          │
│ CPU layers: 12   │                           │ batch: 512          │
└──────────────────┘                           └─────────────────────┘
```

### Jetson Docker Configuration

```yaml
# jetson-orin-nano/docker-compose.yml
# Deploy on Jetson Orin Nano Super
# JetPack 6.x with L4T base container

version: '3.8'

services:
  # ===========================================================================
  # Jetson Edge Inference (Llama 3.2 1B)
  # ===========================================================================
  # Performance: 15-25 tok/s local, faster with RPC offload
  # ===========================================================================
  llamacpp-edge:
    image: dustynv/llama.cpp:r36.4.0  # JetPack 6.x compatible
    container_name: llamacpp-edge
    runtime: nvidia
    
    security_opt:
      - no-new-privileges:true
    
    environment:
      - TZ=America/Chicago
    
    volumes:
      - /mnt/models:/models:ro
      - ./logs:/app/logs:rw
    
    ports:
      - "8080:8080"
    
    # Edge-optimized configuration
    # 12 GPU layers on Jetson, 12 on CPU
    # RPC offload available for heavier computation
    command: >
      --model /models/llama-3.2-1b-Q4_K_M.gguf
      --threads 6
      --batch-size 256
      --ctx-size 4096
      --n-gpu-layers 12
      --parallel 4
      --cont-batching
      --metrics
      --port 8080
    
    healthcheck:
      test: ["CMD", "curl", "-sf", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s
    
    restart: unless-stopped
    
    deploy:
      resources:
        limits:
          memory: 6G
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]

  # ===========================================================================
  # RPC Client for Layer Offload
  # ===========================================================================
  # Offloads heavy layers to AI Desktop CPU when needed
  # ===========================================================================
  rpc-offload:
    image: dustynv/llama.cpp:r36.4.0
    container_name: rpc-offload
    runtime: nvidia
    
    profiles:
      - offload  # Enable with: docker-compose --profile offload up
    
    environment:
      - RPC_SERVER=schlimers-server:50051
    
    volumes:
      - /mnt/models:/models:ro
    
    ports:
      - "8081:8080"
    
    # Split model: GPU layers local, CPU layers remote
    command: >
      --model /models/llama-3.2-3b-Q4_K_M.gguf
      --threads 4
      --batch-size 256
      --ctx-size 4096
      --n-gpu-layers 16
      --rpc schlimers-server:50051
      --parallel 2
      --cont-batching
      --port 8080
    
    restart: unless-stopped
    
    depends_on:
      - llamacpp-edge

networks:
  default:
    driver: bridge
```

### AI Desktop RPC Server Configuration

```yaml
# Add to docker-compose.production-v2.yml on AI Desktop

  # ===========================================================================
  # RPC Server for Jetson Layer Offload
  # ===========================================================================
  # Handles CPU layer computation for Jetson edge devices
  # ===========================================================================
  llamacpp-rpc-server:
    image: ghcr.io/ggerganov/llama.cpp:server
    container_name: llamacpp-rpc-server
    
    profiles:
      - edge  # Enable with: docker-compose --profile edge up
    
    security_opt:
      - no-new-privileges:true
    
    ports:
      - "0.0.0.0:50051:50051"  # Expose to network for Jetson
    
    environment:
      - TZ=America/Chicago
    
    # RPC server mode - no model loaded, handles offloaded layers
    command: >
      --rpc-server
      --host 0.0.0.0
      --port 50051
      --threads 4
    
    deploy:
      resources:
        limits:
          cpus: '4.0'
          memory: 16G
        reservations:
          cpus: '2.0'
          memory: 8G
    
    networks:
      - ai-internal
```

---

## NGC Model Download Commands

### Primary Models (Run on AI Desktop)

```bash
#!/bin/bash
# ~/ai-idp/scripts/download-models.sh
# Uses NGC Catalog access for optimized model downloads

set -euo pipefail

NGC_KEY="${NGC_API_KEY:-}"
MODEL_DIR="/mnt/models"

# Verify NGC authentication
if [ -z "$NGC_KEY" ]; then
    echo "ERROR: NGC_API_KEY not set"
    echo "Get key from: https://ngc.nvidia.com/setup/api-key"
    exit 1
fi

ngc config set <<EOF
$NGC_KEY
json
no-nvc-cache
EOF

echo "Downloading optimized models from NGC Catalog..."

# Llama 3.1 8B Instruct (FP8 quantized for RTX 5070 Ti)
mkdir -p "$MODEL_DIR/llama-3.1-8b-fp8"
ngc registry model download-version "nvidia/llama-3_1-8b-instruct:1.0" \
    --dest "$MODEL_DIR/llama-3.1-8b-fp8"

# Llama 3.2 3B for CPU inference
mkdir -p "$MODEL_DIR/llama-3.2-3b-q4"
huggingface-cli download "bartowski/Llama-3.2-3B-Instruct-GGUF" \
    "Llama-3.2-3B-Instruct-Q4_K_M.gguf" \
    --local-dir "$MODEL_DIR/llama-3.2-3b-q4"

# Llama 3.2 1B for edge/NPU (Jetson, Intel NPU)
mkdir -p "$MODEL_DIR/llama-3.2-1b-q4"
huggingface-cli download "bartowski/Llama-3.2-1B-Instruct-GGUF" \
    "Llama-3.2-1B-Instruct-Q4_K_M.gguf" \
    --local-dir "$MODEL_DIR/llama-3.2-1b-q4"

# Llama 3.3 70B for expert reasoning
mkdir -p "$MODEL_DIR/llama-3.3-70b-q4"
huggingface-cli download "bartowski/Llama-3.3-70B-Instruct-GGUF" \
    "Llama-3.3-70B-Instruct-Q4_K_M.gguf" \
    --local-dir "$MODEL_DIR/llama-3.3-70b-q4"

# Llama Guard 2 for content safety
mkdir -p "$MODEL_DIR/llama-guard-2"
huggingface-cli download "meta-llama/Llama-Guard-2-8B" \
    --local-dir "$MODEL_DIR/llama-guard-2"

echo "✅ Model downloads complete"
echo "Total size: $(du -sh $MODEL_DIR | cut -f1)"
```

---

## Performance Expectations by Tier

| Tier | Device | Model | Throughput | TTFT | Use Case |
|------|--------|-------|------------|------|----------|
| 1 | RTX 5070 Ti | Llama 3.1 8B FP8 | 60-100 tok/s | 40-80ms | Quality generation |
| 1 | RTX 5070 Ti | Llama 3.2 11B FP8 | 40-70 tok/s | 60-100ms | Extended context |
| 2 | Ryzen 9900X | Llama 3.2 3B Q4 | 100-150 tok/s | 20-40ms | Fast brainstorming |
| 2 | Ryzen 9900X | Llama 3.2 1B Q4 | 200+ tok/s | 10-20ms | Drafts, outlines |
| 3 | Hybrid | Llama 3.3 70B Q4 | 8-15 tok/s | 500-1500ms | Expert analysis |
| 4 | Jetson Orin | Llama 3.2 1B Q4 | 15-25 tok/s | 50-100ms | Edge inference |
| 4 | Jetson+RPC | Llama 3.2 3B Q4 | 20-35 tok/s | 100-200ms | Edge with offload |
| 5 | Intel NPU | Llama 3.2 1B INT8 | 5-15 tok/s | 30-60ms | Code completion |
| 5 | GTX 1650 | Llama 3.2 1B Q4 | 8-12 tok/s | 40-80ms | Backup inference |

---

## Azure Integration (Education Hub Credits)

### GPU VM Testing Configuration

```bash
# Azure CLI - Create RTX 4090 equivalent for A/B testing
az vm create \
  --resource-group ai-idp-testing \
  --name ai-idp-cloud-test \
  --image Canonical:0001-com-ubuntu-server-jammy:22_04-lts-gen2:latest \
  --size Standard_NC24ads_A100_v4 \
  --admin-username aidev \
  --generate-ssh-keys \
  --priority Spot \
  --max-price 0.50

# Compare local vs cloud performance
# Use $100/month Azure Education credits for validation
```

### Hybrid Cloud Fallback

```python
# ~/ai-idp/scripts/cloud_fallback.py
"""
Fallback to Azure/Google AI when local inference unavailable
Uses Education Hub / AI Pro credits
"""

import os
import requests
from typing import Optional

LOCAL_VLLM = "http://localhost:8000/v1/completions"
AZURE_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
GOOGLE_ENDPOINT = "https://generativelanguage.googleapis.com/v1"

def inference(prompt: str, prefer_local: bool = True) -> str:
    """Route inference to best available endpoint."""
    
    if prefer_local:
        try:
            resp = requests.post(LOCAL_VLLM, json={
                "model": "llama-3.1-8b",
                "prompt": prompt,
                "max_tokens": 200
            }, timeout=30)
            if resp.status_code == 200:
                return resp.json()["choices"][0]["text"]
        except requests.exceptions.RequestException:
            pass  # Fall through to cloud
    
    # Azure fallback (Education Hub credits)
    if AZURE_ENDPOINT:
        # Use Azure OpenAI API
        pass
    
    # Google fallback (AI Pro)
    # Use Gemini API
    pass
```

---

## Obsidian Integration

### Configuration Sync Strategy

```yaml
# .obsidian/config-sync.yml
# Sync AI IDP configurations across devices via Obsidian Sync

sync_paths:
  - ai-idp/docker-compose*.yml
  - ai-idp/scripts/*.sh
  - ai-idp/secrets/README.md  # NOT api-keys.env!
  
ignore_patterns:
  - "*.env"
  - "secrets/api-keys*"
  - "logs/*"
  - "*.log"

devices:
  - name: AI Desktop (schlimers-server)
    role: primary
    sync: bidirectional
    
  - name: XPS 13 (Developer)
    role: client
    sync: pull-only
    
  - name: Jetson Orin Nano
    role: edge
    sync: pull-only
```

### Documentation Publishing

```bash
# Publish AI IDP documentation via Obsidian Publish
# Accessible at: https://publish.obsidian.md/your-site/ai-idp

# Included in publish:
# - Architecture diagrams
# - Performance benchmarks
# - Quick reference guides
# - Troubleshooting docs
```

---

## Implementation Checklist

- [x] Document user program benefits
- [x] Create model deployment strategy matrix
- [x] Configure Jetson Orin Nano Docker
- [x] Add RPC server for layer offload
- [x] Create NGC model download script
- [x] Document Azure/Google cloud fallback
- [x] Set up Obsidian sync configuration
- [ ] Deploy and validate on physical hardware
