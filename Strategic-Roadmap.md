# Strategic Roadmap: High-Performance Unified Local AI Ecosystem

**Date:** October 7, 2025  
**Author:** MLOps, Systems Integration, and Knowledge Management Architecture Analysis  
**System Status:** Desktop configured (Ubuntu 25.10, CUDA 13.0.1, Driver 580.95.05, CTK 1.17.8)

---

## Executive Summary

This roadmap transforms your multi-node infrastructure (RTX 5070 Ti Desktop + XPS 15 + XPS 13) into a high-performance, privacy-focused AI development and knowledge management ecosystem. The architecture leverages Docker Swarm orchestration, NVIDIA NGC containers, and an intelligent Obsidian vault integration to create a "self-recommending knowledge forge" that captures, processes, and surfaces insights from your AI development lifecycle.

**Critical Success Factors:**
- **Network Optimization:** 2.5G topology with strategic bottleneck mitigation
- **Workload Distribution:** GPU-exclusive Desktop, CPU-offload to XPS 15, portable access via XPS 13
- **Knowledge Synergy:** Automated AI → Obsidian pipelines via n8n webhooks
- **Future-Proof Architecture:** Modular service definitions supporting wireless simulation and edge research

---

## 1. System Architecture & Integration Refinements

### 1.1 Bottleneck Analysis & Mitigation Strategy

#### Current Network Topology Critical Points

```
[Desktop RTX 5070 Ti] ←→ [Flex Mini 2.5G Switch] ←→ [USG] ←→ [WD NAS]
       ↓                           ↓
[XPS 15 Wi-Fi]              [XPS 13 via USB-C]
```

**Identified Bottlenecks (Priority Ordered):**

| Bottleneck | Impact | Mitigation Strategy | Expected Gain |
|------------|--------|---------------------|---------------|
| **XPS 15 Wi-Fi Connectivity** | High | Hardwire XPS 15 to Flex Mini switch via available eth port or secondary 2.5G adapter | 3-5x throughput (Wi-Fi ~300Mbps → 2.5Gbps) |
| **NAS ↔ Desktop Data Path** | High | Currently routed through USG; move NAS to Flex Mini for direct 2.5G path | 40% latency reduction |
| **Model Loading Latency** | Medium | Implement GPUDirect Storage from NVMe; stage models locally on Desktop's Samsung 990 PRO | 2-3x faster load times |
| **Swarm Overlay Network Overhead** | Low-Medium | Use host networking for GPU services; reserve overlay for CPU workloads | 10-15% improvement |

#### NVIDIA GPUDirect Storage Implementation Roadmap

**Phase 1: NVMe Optimization (Current State)**
```bash
# Verify GDS compatibility
nvidia-smi gds-info

# Enable NVMe direct access for containers
# Add to Docker daemon.json on Desktop
{
  "runtimes": {
    "nvidia": {
      "path": "nvidia-container-runtime",
      "runtimeArgs": ["--gpus", "all", "--device", "/dev/nvme0n1"]
    }
  },
  "storage-driver": "overlay2",
  "storage-opts": [
    "overlay2.override_kernel_check=true"
  ]
}
```

**Phase 2: NAS Integration (Future)**
1. Install NVIDIA MLNX_OFED drivers for RDMA support (when NAS supports)
2. Configure GDS-enabled volumes:
```yaml
volumes:
  model_cache:
    driver: local
    driver_opts:
      type: nfs
      o: "addr=<NAS_IP>,nfsvers=4.2,rw,gds=enabled"
      device: ":/models"
```

**Practical Application:**
- **Current:** Stage models on Desktop's 2TB NVMe (15 GB/s reads) → Direct GPU mapping
- **Future:** NAS → GDS-RDMA → GPU VRAM (bypassing CPU, saving 128GB DDR5 for compute)

### 1.2 Docker Swarm Service Strategy

#### Cluster Initialization

```bash
# On Desktop (Manager Node)
docker swarm init --advertise-addr <DESKTOP_IP>

# Label Desktop for GPU workloads
docker node update --label-add gpu=true --label-add type=manager $(docker node ls -q)

# On XPS 15 (Worker Node - after hardwiring!)
docker swarm join --token <WORKER_TOKEN> <DESKTOP_IP>:2377

# Label XPS 15 for CPU workloads
docker node update --label-add cpu=true --label-add type=worker <XPS15_NODE_ID>
```

#### Master Stack Definition

Create `/workspaces/docker-swarm-stack.yml`:

```yaml
version: '3.8'

networks:
  gpu_net:
    driver: overlay
    attachable: true
  cpu_net:
    driver: overlay
    attachable: true

volumes:
  model_storage:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: /mnt/models  # Desktop NVMe mount point
  data_processing:
    driver: local
    driver_opts:
      type: nfs
      o: "addr=<NAS_IP>,nolock,soft,rw"
      device: ":/data"
  obsidian_vault:
    driver: local
    driver_opts:
      type: nfs
      o: "addr=<NAS_IP>,nolock,soft,rw"
      device: ":/obsidian"

services:
  # ============ GPU-Exclusive Services (Desktop) ============
  
  nim_inference:
    image: nvcr.io/nim/meta/llama-3.1-8b-instruct:latest
    networks:
      - gpu_net
    volumes:
      - model_storage:/models:ro
    deploy:
      placement:
        constraints:
          - node.labels.gpu==true
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
          memory: 16G
        limits:
          memory: 32G
      restart_policy:
        condition: on-failure
    environment:
      - CUDA_VISIBLE_DEVICES=0
      - NIM_MODEL_PATH=/models/llama-3.1-8b
      - NIM_TENSOR_PARALLEL_SIZE=1
      - NIM_MAX_BATCH_SIZE=128
      - NIM_USE_PAGED_ATTENTION=true
    ports:
      - "8000:8000"  # OpenAI-compatible API
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  triton_server:
    image: nvcr.io/nvidia/tritonserver:24.12-py3
    networks:
      - gpu_net
    volumes:
      - model_storage:/models:ro
    deploy:
      placement:
        constraints:
          - node.labels.gpu==true
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
          memory: 8G
        limits:
          memory: 16G
    environment:
      - CUDA_VISIBLE_DEVICES=0
    ports:
      - "8001:8001"  # gRPC
      - "8002:8002"  # REST
    command: tritonserver --model-repository=/models --strict-model-config=false

  nemo_training:
    image: nvcr.io/nvidia/nemo:24.12
    networks:
      - gpu_net
    volumes:
      - model_storage:/workspace
      - data_processing:/data:ro
    deploy:
      mode: replicated
      replicas: 0  # Scale on-demand
      placement:
        constraints:
          - node.labels.gpu==true
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
          memory: 32G
        limits:
          memory: 64G
    environment:
      - NEMO_EXPM_VERSION=24.12
      - HYDRA_FULL_ERROR=1

  tensorrt_optimizer:
    image: nvcr.io/nvidia/tensorrt:24.12-py3
    networks:
      - gpu_net
    volumes:
      - model_storage:/workspace
    deploy:
      mode: replicated
      replicas: 0  # On-demand
      placement:
        constraints:
          - node.labels.gpu==true
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
          memory: 16G

  # ============ CPU-Offload Services (XPS 15) ============

  n8n_automation:
    image: n8nio/n8n:latest
    networks:
      - cpu_net
    volumes:
      - /mnt/n8n:/home/node/.n8n
      - obsidian_vault:/obsidian
    deploy:
      placement:
        constraints:
          - node.labels.cpu==true
      resources:
        limits:
          cpus: '4.0'
          memory: 8G
      restart_policy:
        condition: any
    environment:
      - N8N_BASIC_AUTH_ACTIVE=true
      - N8N_BASIC_AUTH_USER=${N8N_USER}
      - N8N_BASIC_AUTH_PASSWORD=${N8N_PASSWORD}
      - N8N_HOST=0.0.0.0
      - N8N_PORT=5678
      - WEBHOOK_URL=http://<DESKTOP_IP>:5678
      - GENERIC_TIMEZONE=America/New_York
    ports:
      - "5678:5678"

  postgres_mlops:
    image: postgres:16-alpine
    networks:
      - cpu_net
    volumes:
      - /mnt/postgres:/var/lib/postgresql/data
    deploy:
      placement:
        constraints:
          - node.labels.cpu==true
      resources:
        limits:
          cpus: '2.0'
          memory: 4G
    environment:
      - POSTGRES_DB=mlops
      - POSTGRES_USER=${DB_USER}
      - POSTGRES_PASSWORD=${DB_PASSWORD}
    ports:
      - "5432:5432"

  data_preprocessing:
    image: python:3.11-slim
    networks:
      - cpu_net
    volumes:
      - data_processing:/data
      - ./scripts:/scripts:ro
    deploy:
      mode: replicated
      replicas: 0  # Job-based
      placement:
        constraints:
          - node.labels.cpu==true
      resources:
        limits:
          cpus: '8.0'  # Leverage XPS 15's i9
          memory: 32G
    command: python /scripts/preprocess.py

  monitoring_stack:
    image: prom/prometheus:latest
    networks:
      - cpu_net
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - /mnt/prometheus:/prometheus
    deploy:
      placement:
        constraints:
          - node.labels.cpu==true
      resources:
        limits:
          cpus: '1.0'
          memory: 2G
    ports:
      - "9090:9090"

  # ============ Multi-Node Services ============

  redis_cache:
    image: redis:7-alpine
    networks:
      - gpu_net
      - cpu_net
    deploy:
      placement:
        constraints:
          - node.labels.gpu==true  # Co-locate with GPU for low-latency
      resources:
        limits:
          cpus: '1.0'
          memory: 4G
    command: redis-server --maxmemory 4gb --maxmemory-policy allkeys-lru
    ports:
      - "6379:6379"
```

#### Deployment Commands

```bash
# Deploy the stack
docker stack deploy -c docker-swarm-stack.yml ai_ecosystem

# Scale training job
docker service scale ai_ecosystem_nemo_training=1

# View service status
docker service ls
docker service ps ai_ecosystem_nim_inference

# Update service (e.g., new NIM version)
docker service update --image nvcr.io/nim/meta/llama-3.1-70b-instruct:latest ai_ecosystem_nim_inference
```

---

## 2. AI Workflow Performance & Tuning

### 2.1 End-to-End Optimized Workflow

#### Concrete Project Example: Fine-Tuning Domain-Specific LLM

**Phase 1: Data Ingestion & Preprocessing (XPS 15)**

```bash
# Scale preprocessing service
docker service scale ai_ecosystem_data_preprocessing=1

# On XPS 15 container (automated via volume mount)
# Script: /scripts/preprocess.py
import pandas as pd
from datasets import load_dataset, Dataset
import multiprocessing as mp

def preprocess_pipeline():
    # Leverage XPS 15's 64GB RAM + i9 cores
    num_workers = mp.cpu_count()
    
    # Load raw data from NAS
    raw_data = pd.read_parquet('/data/raw/*.parquet')
    
    # Parallel tokenization
    dataset = Dataset.from_pandas(raw_data)
    tokenized = dataset.map(
        tokenize_function,
        batched=True,
        num_proc=num_workers,
        remove_columns=dataset.column_names
    )
    
    # Save to shared volume (NAS)
    tokenized.save_to_disk('/data/processed/train_dataset')
    
    # Trigger next phase via webhook
    requests.post('http://n8n:5678/webhook/data-ready', 
                  json={'dataset': 'train_dataset', 'samples': len(tokenized)})

if __name__ == '__main__':
    preprocess_pipeline()
```

**Phase 2: Model Fine-Tuning (Desktop GPU)**

```bash
# Triggered by n8n webhook → scales NeMo service
docker service scale ai_ecosystem_nemo_training=1

# NeMo training script (auto-executed in container)
# Optimized for RTX 5070 Ti (16GB VRAM)
python -m nemo.collections.nlp.scripts.language_modeling.megatron_gpt_finetuning \
  --config-path=/workspace/configs \
  --config-name=megatron_llama_tuning \
  trainer.devices=1 \
  trainer.max_epochs=3 \
  trainer.precision=bf16 \
  trainer.gradient_clip_val=1.0 \
  model.restore_from_path=/models/llama-3.1-8b.nemo \
  model.data.train_ds.file_names=[/data/processed/train_dataset] \
  model.data.train_ds.global_batch_size=32 \
  model.data.train_ds.micro_batch_size=2 \
  model.tensor_model_parallel_size=1 \
  model.pipeline_model_parallel_size=1 \
  model.optim.lr=1e-5 \
  model.optim.sched.warmup_steps=100 \
  exp_manager.checkpoint_callback_params.save_top_k=3 \
  exp_manager.create_wandb_logger=false
```

**Key Optimizations:**
- **Memory Management:** `micro_batch_size=2` with gradient accumulation to fit 16GB VRAM
- **Precision:** BF16 for 2x speed vs FP32, maintaining stability
- **Data Loading:** Pinned memory via NVMe staging leverages Gen5 15GB/s reads
- **DDR5 Utilization:** 128GB hosts full dataset in RAM cache, eliminating I/O waits

**Phase 3: TensorRT Optimization (Desktop GPU)**

```bash
# After training completes, n8n triggers optimization
docker service scale ai_ecosystem_tensorrt_optimizer=1

# TensorRT-LLM conversion script
python /workspace/tensorrt_llm/examples/llama/convert_checkpoint.py \
  --model_dir=/workspace/checkpoints/llama-3.1-8b-finetuned \
  --output_dir=/workspace/trt_engines/llama-finetuned \
  --dtype=float16

# Build optimized engine
trtllm-build \
  --checkpoint_dir=/workspace/trt_engines/llama-finetuned \
  --output_dir=/workspace/trt_engines/llama-finetuned-engine \
  --gemm_plugin=float16 \
  --max_batch_size=128 \
  --max_input_len=2048 \
  --max_output_len=512 \
  --use_paged_kv_cache=enable \
  --paged_kv_cache_max_tokens=8192 \
  --use_fp8_context_fmha=enable \  # Ada/Hopper feature for RTX 5070 Ti
  --use_fp8_gemm=enable \
  --strongly_typed=enable
```

**TensorRT Configuration Deep Dive:**

| Parameter | Value | Rationale | Impact |
|-----------|-------|-----------|--------|
| `dtype` | `float16` | Balance accuracy/speed on Ada Lovelace | 2x throughput vs FP32 |
| `use_fp8_context_fmha` | `enable` | Leverage Tensor Cores 4th gen | 1.5x attention speed |
| `use_fp8_gemm` | `enable` | FP8 matrix ops for linear layers | 30-40% latency reduction |
| `paged_kv_cache` | `enable` | vLLM-style memory management | 2-3x concurrent requests |
| `gemm_plugin` | `float16` | Optimized CUDA kernels | 20% improvement over cuBLAS |
| `max_batch_size` | `128` | Saturate GPU SM count (80 SMs) | Maximize throughput |

**Expected Performance:**
- **Before TensorRT:** ~15 tokens/sec/user (PyTorch)
- **After TensorRT:** ~50-70 tokens/sec/user (FP16) or ~80-100 (FP8)
- **Latency:** First token ~50ms, subsequent ~10-12ms

**Phase 4: NIM Deployment (Desktop GPU)**

```bash
# Update NIM service with custom model
docker service update \
  --image nvcr.io/nim/nvidia/llama-3.1-8b-instruct:latest \
  --mount-add type=bind,source=/workspace/trt_engines/llama-finetuned-engine,target=/models/custom \
  --env-add NIM_MODEL_PATH=/models/custom \
  ai_ecosystem_nim_inference

# Verify deployment
curl http://<DESKTOP_IP>:8000/v1/models
```

**NIM/Triton Inference Server Advanced Configuration:**

Create `/mnt/models/config.pbtxt` for Triton:

```protobuf
name: "llama_finetuned"
backend: "tensorrtllm"
max_batch_size: 128

instance_group [
  {
    count: 1
    kind: KIND_GPU
    gpus: [0]
  }
]

dynamic_batching {
  preferred_batch_size: [8, 16, 32, 64]
  max_queue_delay_microseconds: 1000
  preserve_ordering: true
}

parameters: {
  key: "gpt_model_type"
  value: { string_value: "llama" }
}
parameters: {
  key: "enable_kv_cache_reuse"
  value: { string_value: "true" }
}
```

**DDR5 & NVMe Utilization:**
- **Model Staging:** Pre-load 3-5 model variants in RAM (128GB allows ~40GB models × 3)
- **KV Cache:** Allocate 32GB DDR5 for dynamic KV cache overflow from VRAM
- **Request Queuing:** Redis cache (4GB) on Desktop for sub-ms prompt caching
- **NVMe Tiering:** Log aggregation and checkpoint storage (2TB capacity)

### 2.2 Performance Monitoring & Iteration

```bash
# Add NVIDIA DCGM exporter to stack
docker service create \
  --name dcgm-exporter \
  --mode global \
  --constraint node.labels.gpu==true \
  --mount type=bind,source=/run/prometheus,target=/run/prometheus \
  nvcr.io/nvidia/k8s/dcgm-exporter:3.3.5-3.4.0-ubuntu22.04

# Prometheus scrape config (prometheus.yml)
scrape_configs:
  - job_name: 'gpu_metrics'
    static_configs:
      - targets: ['<DESKTOP_IP>:9400']
```

**Key Metrics to Track:**
- GPU Utilization (target: >85% during inference)
- VRAM Usage (should fit within 14GB with 2GB buffer)
- Tensor Core Activity (verify FP8 usage)
- NVMe Read Throughput (should approach 10-12 GB/s under load)
- P2P Latency (Desktop ↔ XPS 15, target: <2ms)

---

## 3. Knowledge Management & AI Synergy Implementation

### 3.1 "T-Rex" Taxonomy Model Implementation

#### Architecture Decision

**Model Selection:** Fine-tune `bert-base-uncased` (110M params) for multi-label classification
- **Rationale:** Low latency (<10ms), fits entirely in VRAM (1GB), high accuracy for taxonomy
- **Alternative:** Distilled LLAMA (1.5B) if contextual understanding needed

**Deployment Location:** NIM on Desktop (co-located with main inference)
- **Serving Method:** Separate Triton model or dedicated Flask API
- **Latency Target:** <50ms round-trip from Obsidian webhook

#### Fine-Tuning Pipeline

**Step 1: Dataset Preparation**

```python
# Generate training data from existing Obsidian vault
import os
import yaml
from pathlib import Path

def extract_taxonomy_dataset(vault_path='/obsidian'):
    """
    Extract (note_content, tags) pairs from existing vault.
    Assumes YAML frontmatter with 'tags' and 'kind' properties.
    """
    dataset = []
    
    for md_file in Path(vault_path).rglob('*.md'):
        with open(md_file, 'r') as f:
            content = f.read()
            
        # Parse frontmatter
        if content.startswith('---'):
            _, frontmatter, body = content.split('---', 2)
            metadata = yaml.safe_load(frontmatter)
            
            # Extract features
            tags = metadata.get('tags', [])
            kind = metadata.get('kind', 'unknown')
            para_folder = str(md_file.parent.name)  # Projects/Areas/Resources
            
            # Combine for multi-label target
            labels = tags + [f"kind:{kind}", f"para:{para_folder}"]
            
            dataset.append({
                'text': body.strip()[:512],  # BERT max seq
                'labels': labels
            })
    
    return dataset

# Prepare for NeMo
from nemo.collections.nlp.data import TextClassificationDataset

train_data = extract_taxonomy_dataset()
# Save as JSON for NeMo ingestion
```

**Step 2: NeMo Fine-Tuning**

```bash
# On Desktop GPU via nemo_training service
docker service scale ai_ecosystem_nemo_training=1

# Inside container
python -m nemo.collections.nlp.scripts.text_classification.text_classification_with_bert \
  model.language_model.pretrained_model_name=bert-base-uncased \
  model.dataset.num_classes=50 \  # Adjust to unique tag count
  model.dataset.multi_label=true \
  model.train_ds.file_path=/data/obsidian/train.json \
  model.validation_ds.file_path=/data/obsidian/val.json \
  trainer.max_epochs=5 \
  trainer.devices=1 \
  trainer.precision=16 \
  model.optim.lr=2e-5
```

**Step 3: Export & Deploy**

```python
# Convert to ONNX for Triton
import nemo.collections.nlp as nemo_nlp

model = nemo_nlp.models.TextClassificationModel.restore_from('/workspace/trex_model.nemo')
model.export('/workspace/trex.onnx', export_format='onnx')

# Create Triton config
# /mnt/models/trex/config.pbtxt
"""
name: "trex_taxonomy"
platform: "onnxruntime_onnx"
max_batch_size: 32
input [
  { name: "input_ids", data_type: TYPE_INT64, dims: [512] },
  { name: "attention_mask", data_type: TYPE_INT64, dims: [512] }
]
output [
  { name: "logits", data_type: TYPE_FP32, dims: [50] }
]
"""
```

**Serving API Wrapper:**

```python
# Flask API on Desktop (or integrate into NIM)
from flask import Flask, request, jsonify
import tritonclient.http as httpclient
from transformers import AutoTokenizer

app = Flask(__name__)
triton_client = httpclient.InferenceServerClient(url='localhost:8001')
tokenizer = AutoTokenizer.from_pretrained('bert-base-uncased')

@app.route('/classify', methods=['POST'])
def classify_note():
    text = request.json['text']
    
    # Tokenize
    inputs = tokenizer(text, max_length=512, truncation=True, 
                      padding='max_length', return_tensors='np')
    
    # Triton inference
    triton_inputs = [
        httpclient.InferInput('input_ids', inputs['input_ids'].shape, 'INT64'),
        httpclient.InferInput('attention_mask', inputs['attention_mask'].shape, 'INT64')
    ]
    triton_inputs[0].set_data_from_numpy(inputs['input_ids'])
    triton_inputs[1].set_data_from_numpy(inputs['attention_mask'])
    
    response = triton_client.infer('trex_taxonomy', triton_inputs)
    logits = response.as_numpy('logits')
    
    # Get top-k tags (threshold > 0.5)
    predictions = (logits > 0.5).nonzero()[1]
    tags = [id_to_label[i] for i in predictions]
    
    return jsonify({'suggested_tags': tags})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
```

### 3.2 n8n Automation Bridge

#### Workflow 1: Git Commit → Obsidian Note Generation

**n8n Workflow Design:**

```json
{
  "name": "Git Commit to Obsidian",
  "nodes": [
    {
      "type": "n8n-nodes-base.webhook",
      "name": "GitHub Webhook",
      "parameters": {
        "path": "github-commit",
        "method": "POST"
      }
    },
    {
      "type": "n8n-nodes-base.httpRequest",
      "name": "Fetch Commit Details",
      "parameters": {
        "url": "={{ $json.repository.commits_url }}",
        "authentication": "predefinedCredentialType",
        "nodeCredentialType": "githubApi"
      }
    },
    {
      "type": "n8n-nodes-base.code",
      "name": "Parse Code Changes",
      "parameters": {
        "jsCode": "const commit = $input.item.json;\nconst files = commit.files.map(f => ({\n  filename: f.filename,\n  additions: f.additions,\n  deletions: f.deletions\n}));\n\nreturn {\n  json: {\n    sha: commit.sha,\n    message: commit.commit.message,\n    author: commit.commit.author.name,\n    timestamp: commit.commit.author.date,\n    files: files,\n    diff_url: commit.html_url\n  }\n};"
      }
    },
    {
      "type": "n8n-nodes-base.httpRequest",
      "name": "T-Rex Classification",
      "parameters": {
        "url": "http://<DESKTOP_IP>:5000/classify",
        "method": "POST",
        "jsonParameters": true,
        "options": {
          "bodyParametersJson": "={ \"text\": \"{{ $json.message }} Files: {{ $json.files.map(f => f.filename).join(', ') }}\" }"
        }
      }
    },
    {
      "type": "n8n-nodes-base.code",
      "name": "Generate Markdown",
      "parameters": {
        "jsCode": "const commit = $input.first().json;\nconst tags = $input.last().json.suggested_tags;\n\nconst frontmatter = `---\nkind: code_commit\ncontent_type: development\ntags: ${JSON.stringify(tags)}\ndate: ${commit.timestamp}\nauthor: ${commit.author}\nrepo: ${commit.repo}\n---`;\n\nconst body = `# Commit: ${commit.sha.substring(0,7)}\n\n## Message\n${commit.message}\n\n## Changes\n${commit.files.map(f => `- **${f.filename}**: +${f.additions}/-${f.deletions}`).join('\\n')}\n\n## Links\n- [View Diff](${commit.diff_url})\n- [Repository](${commit.repo})\n\n## AI Suggestions\nSuggested PARA placement: ${tags.find(t => t.startsWith('para:'))}\nRelated topics: ${tags.filter(t => !t.startsWith('para:')).join(', ')}`;\n\nreturn {\n  json: {\n    filename: `${commit.timestamp.split('T')[0]}-${commit.sha.substring(0,7)}.md`,\n    content: frontmatter + '\\n\\n' + body\n  }\n};"
      }
    },
    {
      "type": "n8n-nodes-base.writeBinaryFile",
      "name": "Save to Obsidian",
      "parameters": {
        "fileName": "={{ $json.filename }}",
        "dataPropertyName": "content",
        "options": {
          "path": "/obsidian/100-Distilary/"
        }
      }
    },
    {
      "type": "n8n-nodes-base.telegram",
      "name": "Notify User",
      "parameters": {
        "text": "✅ New commit captured in Obsidian: {{ $json.filename }}"
      }
    }
  ],
  "connections": {
    "GitHub Webhook": { "main": [[{ "node": "Fetch Commit Details" }]] },
    "Fetch Commit Details": { "main": [[{ "node": "Parse Code Changes" }]] },
    "Parse Code Changes": { "main": [[{ "node": "T-Rex Classification" }]] },
    "T-Rex Classification": { "main": [[{ "node": "Generate Markdown" }]] },
    "Generate Markdown": { "main": [[{ "node": "Save to Obsidian" }, { "node": "Notify User" }]] }
  }
}
```

#### Workflow 2: Model Training Completion → Experiment Tracking

**Trigger:** NeMo training script posts to webhook upon completion

```python
# In NeMo training script (add at end)
import requests

def log_experiment_to_obsidian(config, metrics, checkpoint_path):
    payload = {
        'experiment_name': config.exp_manager.name,
        'model': config.model.name,
        'hyperparameters': {
            'lr': config.model.optim.lr,
            'batch_size': config.model.data.train_ds.global_batch_size,
            'epochs': config.trainer.max_epochs
        },
        'metrics': {
            'train_loss': metrics['train_loss_epoch'],
            'val_loss': metrics['val_loss'],
            'val_accuracy': metrics['val_accuracy']
        },
        'artifacts': {
            'checkpoint': checkpoint_path,
            'tensorboard': config.exp_manager.exp_dir
        }
    }
    
    requests.post('http://n8n:5678/webhook/training-complete', json=payload)

# Call after training
log_experiment_to_obsidian(cfg, trainer.logged_metrics, best_checkpoint)
```

**n8n Processing:**

1. **Receive webhook** → Parse experiment data
2. **Query T-Rex** → Classify experiment type (e.g., "fine-tuning", "pretraining")
3. **Generate template** → Populate experiment note with:
   - Frontmatter: `kind: ml_experiment`, `status: completed`, `tags: [nemo, llama, fine-tune]`
   - Metrics table
   - Links to checkpoints & TensorBoard
   - Suggested PARA placement (likely `Projects/Active/`)
4. **Cross-reference** → Link to related experiments using semantic search
5. **Save & notify** → Write to Obsidian, ping Telegram

**Advanced Integration: MLflow Bridge**

```yaml
# Add to docker-swarm-stack.yml
mlflow_server:
  image: ghcr.io/mlflow/mlflow:v2.10.0
  networks:
    - cpu_net
  volumes:
    - /mnt/mlflow:/mlflow
    - postgres_mlops:/db  # Use Postgres backend
  deploy:
    placement:
      constraints:
        - node.labels.cpu==true
    resources:
      limits:
        cpus: '1.0'
        memory: 2G
  command: mlflow server --backend-store-uri postgresql://${DB_USER}:${DB_PASSWORD}@postgres_mlops:5432/mlops --default-artifact-root /mlflow --host 0.0.0.0
  ports:
    - "5001:5000"
```

**n8n → MLflow → Obsidian Pipeline:**
1. MLflow logs experiments automatically
2. n8n polls MLflow API every 5 minutes
3. New experiments trigger Obsidian note generation
4. Notes include MLflow UI links for interactive exploration

---

## 4. Strategic Vision & Future-Proofing

### 4.1 Critical Plan Evaluation

#### Missing Components (Prioritized)

| Component | Criticality | Impact | Implementation Timeline |
|-----------|-------------|--------|------------------------|
| **Experiment Tracking (MLflow)** | High | Prevents duplication, enables reproducibility | Week 1-2 |
| **Backup & Disaster Recovery** | High | Protects 128GB model cache, Obsidian vault | Week 1 |
| **Network Monitoring (Grafana)** | Medium | Identifies 2.5G bottlenecks proactively | Week 2-3 |
| **Secret Management (Vault)** | Medium | Secures NGC API keys, DB credentials | Week 3-4 |
| **CI/CD Pipeline (GitLab Runner)** | Low | Automates container builds | Month 2 |

#### Over-Engineered Aspects

1. **Docker Swarm for 2 Nodes**
   - **Assessment:** Borderline—worth it for future scalability, but could start with docker-compose
   - **Recommendation:** Keep Swarm; enables zero-downtime updates & easy XPS 13 integration
   
2. **Separate Triton + NIM Services**
   - **Assessment:** Redundant if only serving 1-2 models
   - **Recommendation:** Consolidate to NIM with custom model mounts initially; split when >3 models

3. **Full RAPIDS Stack**
   - **Assessment:** Overkill without multi-GPU or massive datasets (>100GB)
   - **Recommendation:** Defer until hitting Pandas/Dask bottlenecks; focus on PyTorch optimizations first

#### "Should Have" ROI Analysis

| Feature | Setup Effort | Performance Gain | Knowledge Mgmt Benefit | Priority Score |
|---------|--------------|------------------|------------------------|----------------|
| **Magnum IO** | High (requires RDMA NAS) | 30-50% I/O improvement | Low | 4/10 (future) |
| **RAPIDS** | Medium | 5-10x preprocessing | Low | 6/10 (if data-heavy) |
| **Nsight Tools** | Low | 20-30% kernel optimization | Low | 7/10 (profiling) |
| **PyTorch Geometric** | Low | Enables graph ML | High (knowledge graphs) | **9/10** ⭐ |
| **TensorFlow** | Low | Framework diversity | Low | 3/10 (stick to PyTorch) |

**Recommendation:** Prioritize **PyTorch Geometric** for Obsidian graph embeddings (e.g., link prediction, topic clustering).

### 4.2 Scalability Strategy

#### Phase 1: Current State (2-Node Swarm)
```
Desktop (Manager) → RTX 5070 Ti (GPU workloads)
XPS 15 (Worker)   → CPU offload, automation
XPS 13            → Portable client (no Swarm role)
```

#### Phase 2: Horizontal Scaling (6-12 months)

**Scenario A: Second GPU Node**
```yaml
# Add XPS 13 with eGPU or new desktop
docker swarm join --token <WORKER_TOKEN> <MANAGER_IP>:2377
docker node update --label-add gpu=true --label-add tier=secondary <NEW_NODE>

# Update placement constraints
services:
  nim_inference:
    deploy:
      replicas: 2  # Load balance across GPUs
      placement:
        constraints:
          - node.labels.gpu==true
```

**Scenario B: Specialized Nodes**
```
Desktop      → LLM inference (NIM)
New Node 1   → Vision models (Triton + TensorRT)
New Node 2   → Aerial/Sionna wireless simulation
XPS 15       → CPU orchestration hub
```

**Key Enabler: Service Templates**

Create reusable configs in `/swarm-templates/`:

```yaml
# aerial_service.yml
version: '3.8'
services:
  aerial_ran:
    image: nvcr.io/nvidia/aerial/aerial-ran:25.2
    networks:
      - gpu_net
    deploy:
      placement:
        constraints:
          - node.labels.domain==wireless
          - node.labels.gpu==true
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    ports:
      - "8080:8080"
```

Deploy with: `docker stack deploy -c aerial_service.yml wireless_sim`

#### Phase 3: Edge Integration (12-24 months)

**Use Case:** XPS 13 + 5G modem for mobile AI testing

```yaml
# Edge-optimized inference (INT8 quantized models)
edge_inference:
  image: nvcr.io/nim/meta/llama-3.1-8b-instruct:edge
  deploy:
    placement:
      constraints:
        - node.labels.type==edge
    resources:
      limits:
        cpus: '8.0'
        memory: 16G  # No GPU, use XPS 13's CPU
  environment:
    - NIM_TENSOR_PARALLEL_SIZE=1
    - NIM_QUANTIZATION=int8
```

**Obsidian Integration:** Sync via Git (NAS as origin) + conflict resolution via n8n

#### Phase 4: Hybrid Cloud (24+ months)

**Burst Scenario:** Offload heavy training to cloud while keeping inference local

```yaml
# Use Docker Context for multi-cloud Swarm
docker context create cloud --docker host=ssh://user@cloud-vm
docker context use cloud
docker stack deploy -c training_job.yml cloud_burst
```

**Data Flow:**
1. Local preprocessing (XPS 15)
2. Upload to cloud storage (encrypted)
3. Cloud training (spot instances)
4. Download checkpoints to Desktop NVMe
5. Local TensorRT optimization & deployment

**Cost Optimization:** Only use cloud for >24hr training jobs; keep all inference local

### 4.3 Technology Refresh Roadmap

| Timeline | Hardware Upgrade | Software Evolution | Workload Shift |
|----------|------------------|-------------------|----------------|
| **Now** | RTX 5070 Ti (16GB) | CUDA 13.0, NeMo 24.12 | 8B models, single-GPU |
| **12 months** | +Second GPU or RTX 6000 Ada | CUDA 13.5, Multi-modal NIM | 70B models (multi-GPU), vision |
| **24 months** | NAS upgrade (10G NIC + RDMA) | GPUDirect Storage, Grace Hopper support | Distributed training, RAG at scale |
| **36 months** | Replace XPS 15 with ARM server | Aerial 6G, Quantum ML (Pennylane) | Edge AI, research prototyping |

---

## 5. Implementation Checklist

### Week 1: Foundation (Critical Path)

- [ ] **Hardwire XPS 15 to Flex Mini switch** (highest ROI bottleneck fix)
  ```bash
  # Test throughput after connection
  iperf3 -s  # On Desktop
  iperf3 -c <DESKTOP_IP> -t 30  # On XPS 15, expect >2.3 Gbps
  ```

- [ ] **Initialize Docker Swarm cluster**
  ```bash
  # Desktop
  docker swarm init --advertise-addr <DESKTOP_IP>
  docker node update --label-add gpu=true $(hostname)
  
  # XPS 15
  docker swarm join --token <TOKEN> <DESKTOP_IP>:2377
  ```

- [ ] **Deploy core services (NIM + PostgreSQL)**
  ```bash
  docker stack deploy -c docker-swarm-stack.yml ai_ecosystem
  docker service ls  # Verify running
  ```

- [ ] **Configure NAS mounts on both nodes**
  ```bash
  # /etc/fstab on Desktop & XPS 15
  <NAS_IP>:/models /mnt/models nfs4 defaults,_netdev 0 0
  <NAS_IP>:/data /mnt/data nfs4 defaults,_netdev 0 0
  ```

- [ ] **Set up Obsidian vault structure**
  ```
  /obsidian/
  ├── 000-System/
  │   ├── templates/
  │   └── scripts/
  ├── 100-Distilary/  # Inbox for automation
  ├── Projects/
  ├── Areas/
  ├── Resources/
  └── 900-PKM/
  ```

### Week 2: AI Workflow Pipeline

- [ ] **Create preprocessing script for XPS 15**
- [ ] **Test NeMo fine-tuning on sample dataset** (verify GPU utilization >80%)
- [ ] **Build first TensorRT engine** (measure latency improvement)
- [ ] **Deploy custom model via NIM**
- [ ] **Set up monitoring (Prometheus + DCGM)**

### Week 3: T-Rex & Automation

- [ ] **Extract Obsidian training dataset** (aim for 500+ labeled notes)
- [ ] **Fine-tune BERT taxonomy model**
- [ ] **Deploy T-Rex API on Desktop**
- [ ] **Install n8n and create first workflow** (Git commit → Obsidian)
- [ ] **Test end-to-end: Make commit → Verify note appears**

### Week 4: Optimization & Documentation

- [ ] **Profile NVMe → GPU data path** (GPUDirect Storage if supported)
- [ ] **Tune TensorRT FP8 settings** (compare vs FP16 accuracy)
- [ ] **Set up MLflow experiment tracking**
- [ ] **Create runbook documentation**
- [ ] **Backup strategy implementation** (3-2-1 rule: 3 copies, 2 media, 1 offsite)

### Month 2: Advanced Features

- [ ] **PyTorch Geometric for knowledge graph embeddings**
- [ ] **Implement link prediction in Obsidian** (suggest connections)
- [ ] **n8n workflow: Auto-summarize meeting notes with LLM**
- [ ] **Grafana dashboards for system health**
- [ ] **Load testing: Simulate 50 concurrent NIM requests**

---

## 6. Risk Mitigation

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| **VRAM exhaustion (16GB limit)** | High | High | Implement gradient checkpointing; use INT8/FP8; model quantization |
| **Network congestion (2.5G)** | Medium | High | QoS on Flex Mini; separate VLANs for AI traffic; hardwire XPS 15 |
| **NAS failure (single point)** | Low | Critical | Daily snapshots to external drive; critical models cached on Desktop NVMe |
| **Docker Swarm split-brain** | Low | Medium | Use odd number of managers (add XPS 13 as manager if scaling) |
| **Obsidian vault corruption** | Low | High | Git version control + hourly commits; immutable backups |
| **Model staleness in T-Rex** | Medium | Low | Monthly retraining pipeline; A/B testing via separate Triton versions |

---

## 7. Success Metrics (30-Day)

### Performance Targets

| Metric | Baseline | Target | Measurement |
|--------|----------|--------|-------------|
| **NIM Inference Latency** | 200ms (PyTorch) | <50ms (TensorRT FP8) | `curl` benchmark |
| **Model Fine-Tuning Time** | N/A | <4 hours (8B, 10K samples) | NeMo logs |
| **Data Preprocessing Throughput** | N/A | >1M samples/hour | XPS 15 logs |
| **Git → Obsidian Latency** | N/A | <30 seconds | n8n execution time |
| **T-Rex Classification Accuracy** | N/A | >85% F1-score | Validation set |
| **Network Utilization** | Unknown | <70% peak | Prometheus |

### Knowledge Management KPIs

- **Notes Auto-Generated:** Target 50+ (commits, experiments, meetings)
- **Tag Suggestion Accuracy:** >80% user acceptance rate
- **Vault Growth:** 100-200 new atomic notes/month
- **Cross-Links Created:** 10+ per note (via AI suggestions)
- **Search Efficiency:** <5 seconds to find relevant note

### System Reliability

- **Uptime:** 99%+ for NIM service
- **Backup Success Rate:** 100%
- **Swarm Health Checks:** 0 failed services
- **Security Incidents:** 0

---

## 8. Learning Resources & Next Steps

### Immediate Study Materials

1. **NVIDIA NIM Documentation:** https://docs.nvidia.com/nim/
2. **TensorRT-LLM Guide:** https://github.com/NVIDIA/TensorRT-LLM
3. **NeMo Tutorials:** https://docs.nvidia.com/nemo-framework/
4. **Docker Swarm Best Practices:** https://docs.docker.com/engine/swarm/
5. **Obsidian Dataview:** https://blacksmithgu.github.io/obsidian-dataview/

### Community Engagement

- **NVIDIA Developer Forums:** Post optimization questions
- **r/LocalLLaMA:** Share TensorRT benchmarks
- **Obsidian Discord:** Knowledge management patterns
- **MLOps Community Slack:** Automation workflows

### Quarterly Review Agenda

1. **Workload Analysis:** Which services underutilized? Over-provisioned?
2. **Cost-Benefit:** Did T-Rex save time? Quantify hours.
3. **Technology Radar:** New NGC containers, CUDA features
4. **Vault Health:** Dead links, unused tags, growth rate
5. **Scalability Triggers:** When to add third node?

---

## Conclusion

This roadmap provides a structured path from your current 2-node setup to a fully optimized AI development and knowledge management ecosystem. The architecture balances performance (GPU-exclusive Desktop, CPU-offload XPS 15), privacy (local-first), and intelligence (AI-driven Obsidian integration).

**Immediate Next Steps:**
1. Hardwire XPS 15 (highest ROI)
2. Deploy Docker Swarm + core services
3. Test first NeMo → TensorRT → NIM pipeline
4. Create initial n8n workflow

**Success Criteria (90 Days):**
- <50ms inference latency (3-4x improvement)
- 100+ auto-generated Obsidian notes
- Zero manual experiment tracking (full MLflow integration)
- Scalable architecture proven with test wireless simulation workload

The system is designed for incremental enhancement—each phase delivers immediate value while building toward the vision of a truly unified, intelligent knowledge forge.
