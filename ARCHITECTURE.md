# System Architecture Diagram

## High-Level Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        AI ECOSYSTEM ARCHITECTURE                     │
│                    Privacy-Focused Local Infrastructure              │
└─────────────────────────────────────────────────────────────────────┘

                              INTERNET
                                 │
                        [Fiber ONT/Modem]
                                 │
                          [EdgeRouter X]
                                 │
              ┌──────────────────┼──────────────────┐
              │                  │                  │
       [UniFi Express 7]   [AC Pro WiFi]    [USG Gateway]
              │                  │                  │
       [Flex Mini 2.5G]          │            [WD NAS]
              │                  │            (Storage)
     ┌────────┼────────┐         │
     │        │        │         │
  [XPS13] [Desktop] [USB-C]   [XPS15]
  Portable  Primary  Adapter  CPU Node
  Client   GPU Node          (Wi-Fi)
```

## Docker Swarm Cluster Topology

```
┌──────────────────────────────────────────────────────────────────────┐
│                         DOCKER SWARM CLUSTER                         │
└──────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────┐    ┌─────────────────────────────┐
│      DESKTOP (Manager Node)     │    │    XPS 15 (Worker Node)     │
│  ─────────────────────────────  │    │  ─────────────────────────  │
│  Hardware:                      │    │  Hardware:                  │
│  • Ryzen 9 9900X (12C/24T)     │    │  • Intel i9 (8C/16T)        │
│  • RTX 5070 Ti (16GB VRAM)     │    │  • 64GB DDR4 RAM            │
│  • 128GB DDR5-6400 RAM         │    │  • No GPU                   │
│  • 2TB Gen5 NVMe (15GB/s)      │    │  • 1TB NVMe                 │
│  ─────────────────────────────  │    │  ─────────────────────────  │
│                                 │    │                             │
│  GPU Services:                  │    │  CPU Services:              │
│  ┌────────────────────────┐    │    │  ┌────────────────────┐    │
│  │ NIM Inference          │    │    │  │ n8n Automation     │    │
│  │ Port: 8000             │    │    │  │ Port: 5678         │    │
│  │ GPU: RTX 5070 Ti       │    │    │  │ Cores: 4           │    │
│  │ Memory: 32GB           │    │    │  │ Memory: 8GB        │    │
│  └────────────────────────┘    │    │  └────────────────────┘    │
│                                 │    │                             │
│  ┌────────────────────────┐    │    │  ┌────────────────────┐    │
│  │ Triton Server          │    │    │  │ PostgreSQL         │    │
│  │ Ports: 8001-8003       │    │    │  │ Port: 5432         │    │
│  │ GPU: RTX 5070 Ti       │    │    │  │ Cores: 2           │    │
│  │ Memory: 20GB           │    │    │  │ Memory: 4GB        │    │
│  └────────────────────────┘    │    │  └────────────────────┘    │
│                                 │    │                             │
│  ┌────────────────────────┐    │    │  ┌────────────────────┐    │
│  │ NeMo Training          │    │    │  │ MLflow Server      │    │
│  │ (On-Demand)            │    │    │  │ Port: 5001         │    │
│  │ GPU: RTX 5070 Ti       │    │    │  │ Cores: 2           │    │
│  │ Memory: 80GB           │    │    │  │ Memory: 4GB        │    │
│  └────────────────────────┘    │    │  └────────────────────┘    │
│                                 │    │                             │
│  ┌────────────────────────┐    │    │  ┌────────────────────┐    │
│  │ TensorRT Optimizer     │    │    │  │ Data Preprocessing │    │
│  │ (On-Demand)            │    │    │  │ (On-Demand)        │    │
│  │ GPU: RTX 5070 Ti       │    │    │  │ Cores: 12          │    │
│  │ Memory: 40GB           │    │    │  │ Memory: 48GB       │    │
│  └────────────────────────┘    │    │  └────────────────────┘    │
│                                 │    │                             │
│  ┌────────────────────────┐    │    │  ┌────────────────────┐    │
│  │ T-Rex Classifier       │    │    │  │ Prometheus         │    │
│  │ Port: 5000             │    │    │  │ Port: 9090         │    │
│  │ Triton Backend         │    │    │  │ Cores: 1           │    │
│  │ Memory: 4GB            │    │    │  │ Memory: 2GB        │    │
│  └────────────────────────┘    │    │  └────────────────────┘    │
│                                 │    │                             │
│  ┌────────────────────────┐    │    │  ┌────────────────────┐    │
│  │ Redis Cache            │    │    │  │ Grafana            │    │
│  │ Port: 6379             │    │    │  │ Port: 3000         │    │
│  │ Shared across networks │    │    │  │ Cores: 1           │    │
│  │ Memory: 4GB            │    │    │  │ Memory: 1GB        │    │
│  └────────────────────────┘    │    │  └────────────────────┘    │
│                                 │    │                             │
│  ┌────────────────────────┐    │    │                             │
│  │ DCGM Exporter          │    │    │                             │
│  │ Port: 9400             │    │    │                             │
│  │ GPU Metrics            │    │    │                             │
│  └────────────────────────┘    │    │                             │
│                                 │    │                             │
│  Label: gpu=true               │    │  Label: cpu=true            │
└─────────────────────────────────┘    └─────────────────────────────┘
           │                                      │
           └──────────────┬───────────────────────┘
                          │
                   2.5G Network
                   Overlay Networks:
                   • gpu_net (GPU services)
                   • cpu_net (CPU services)
```

## Data Flow Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                      END-TO-END AI WORKFLOW                          │
└─────────────────────────────────────────────────────────────────────┘

1. DATA INGESTION
   ┌────────────┐
   │ Raw Data   │ ──→ NAS Storage (/data/raw)
   └────────────┘

2. PREPROCESSING (XPS 15)
   ┌────────────────┐
   │ Data Prep      │ ──→ Tokenization, Cleaning
   │ Container      │     Multi-core Processing
   └────────────────┘     (12 cores, 48GB RAM)
          │
          ↓
   ┌────────────┐
   │ Processed  │ ──→ NAS Storage (/data/processed)
   │ Dataset    │
   └────────────┘

3. MODEL TRAINING (Desktop GPU)
   ┌────────────────┐
   │ NeMo Training  │ ──→ RTX 5070 Ti (16GB VRAM)
   │ Container      │     BF16 Precision
   └────────────────┘     Gradient Accumulation
          │
          ↓
   ┌────────────┐
   │ Trained    │ ──→ NAS Storage (/models)
   │ Model      │     .nemo format
   └────────────┘

4. MODEL OPTIMIZATION (Desktop GPU)
   ┌────────────────┐
   │ TensorRT       │ ──→ FP16/FP8 Quantization
   │ Optimizer      │     Engine Building
   └────────────────┘     Paged KV Cache
          │
          ↓
   ┌────────────┐
   │ Optimized  │ ──→ Local NVMe (Desktop)
   │ Engine     │     /mnt/models/trt_engines
   └────────────┘

5. DEPLOYMENT (Desktop GPU)
   ┌────────────────┐
   │ NIM Inference  │ ──→ OpenAI-Compatible API
   │ Server         │     Port 8000
   └────────────────┘     <50ms Latency
          │
          ↓
   ┌────────────────┐
   │ Redis Cache    │ ──→ Prompt Caching
   └────────────────┘     Sub-ms Retrieval

6. KNOWLEDGE CAPTURE (n8n on XPS 15)
   ┌────────────────┐
   │ Git Webhook    │ ──→ n8n Workflow
   │ Trigger        │
   └────────────────┘
          │
          ↓
   ┌────────────────┐
   │ T-Rex          │ ──→ Classify & Tag
   │ Classifier     │     (Desktop GPU)
   └────────────────┘
          │
          ↓
   ┌────────────────┐
   │ Generate       │ ──→ Structured Markdown
   │ Obsidian Note  │     with Frontmatter
   └────────────────┘
          │
          ↓
   ┌────────────────┐
   │ Save to Vault  │ ──→ NAS (/obsidian)
   └────────────────┘     Auto-linked
```

## Storage Hierarchy

```
┌─────────────────────────────────────────────────────────────────────┐
│                         STORAGE ARCHITECTURE                         │
└─────────────────────────────────────────────────────────────────────┘

Desktop NVMe (Tier 1 - Fastest)
┌────────────────────────────────────────┐
│ Samsung 990 PRO 2TB Gen5               │
│ Read: 15 GB/s, Write: 13 GB/s         │
│ ────────────────────────────────────── │
│ • Active model cache                   │
│ • TensorRT engines                     │
│ • Training checkpoints                 │
│ • OS and applications                  │
│                                        │
│ GPUDirect Storage → VRAM               │
│ (Bypasses CPU/DDR5)                    │
└────────────────────────────────────────┘
          ↕ Hot data promotion
          ↓ 2.5G Network

NAS Storage (Tier 2 - Shared)
┌────────────────────────────────────────┐
│ WD NAS (Connected via USG)             │
│ Transfer: ~280 MB/s over 2.5G          │
│ ────────────────────────────────────── │
│ /models/                               │
│ • Base models (LLAMA, BERT)            │
│ • Model variants                       │
│ • ONNX exports                         │
│                                        │
│ /data/                                 │
│ • Raw datasets                         │
│ • Processed datasets                   │
│ • Batch inference inputs               │
│                                        │
│ /obsidian/                             │
│ • Markdown notes                       │
│ • Attachments                          │
│ • Templates                            │
│                                        │
│ NFS v4.2 mounts on both nodes          │
└────────────────────────────────────────┘
          ↕ Backup
          ↓

External Backup (Tier 3 - Archive)
┌────────────────────────────────────────┐
│ External USB Drive                     │
│ ────────────────────────────────────── │
│ • Daily snapshots (7 days)             │
│ • Weekly backups (4 weeks)             │
│ • Monthly archives (12 months)         │
│                                        │
│ 3-2-1 Backup Strategy                  │
└────────────────────────────────────────┘
```

## Network Data Paths

```
┌─────────────────────────────────────────────────────────────────────┐
│                       NETWORK OPTIMIZATION                           │
└─────────────────────────────────────────────────────────────────────┘

Critical Path (Training):
┌─────────────┐
│ NAS Storage │
│ (Dataset)   │
└──────┬──────┘
       │ 2.5G Network
       │ ~280 MB/s
       ↓
┌─────────────────┐
│ Desktop         │
│ DDR5 RAM Cache  │ ←── 128GB buffer
│ (Hot dataset)   │     51,200 MB/s
└────────┬────────┘
         │ PCIe Gen5
         │ 15,000 MB/s (NVMe)
         ↓
┌─────────────────┐
│ Samsung 990 PRO │
│ (Staged models) │
└────────┬────────┘
         │ GPUDirect Storage
         │ (Future: Direct path)
         ↓
┌─────────────────┐
│ RTX 5070 Ti     │
│ VRAM (16GB)     │ ←── Model weights
└─────────────────┘     896 GB/s bandwidth


Critical Path (Inference):
┌──────────────────┐
│ User Request     │ (HTTP/REST)
└────────┬─────────┘
         │ <2ms latency
         ↓
┌──────────────────┐
│ Redis Cache      │ (Prompt cache hit?)
│ (Desktop)        │
└────────┬─────────┘
         │ Cache miss
         ↓
┌──────────────────┐
│ NIM Inference    │ (GPU processing)
│ (Desktop)        │
└────────┬─────────┘
         │ <50ms
         ↓
┌──────────────────┐
│ Response         │ (Streamed tokens)
└──────────────────┘


Automation Path (Git → Obsidian):
┌──────────────────┐
│ GitHub Webhook   │ (Push event)
└────────┬─────────┘
         │ Internet
         ↓
┌──────────────────┐
│ n8n Workflow     │ (XPS 15)
│ (Receives)       │
└────────┬─────────┘
         │ Parse commit data
         ↓
┌──────────────────┐
│ T-Rex API        │ (Desktop GPU)
│ Classification   │
└────────┬─────────┘
         │ <50ms
         ↓
┌──────────────────┐
│ Generate Note    │ (n8n - XPS 15)
│ (Markdown)       │
└────────┬─────────┘
         │ 2.5G Network
         ↓
┌──────────────────┐
│ Obsidian Vault   │ (NAS Storage)
│ (Saved)          │
└──────────────────┘
Total: <30 seconds end-to-end
```

## Monitoring & Observability

```
┌─────────────────────────────────────────────────────────────────────┐
│                      MONITORING ARCHITECTURE                         │
└─────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────┐
│                           Grafana (XPS 15)                           │
│                         Visualization Layer                          │
│                            Port 3000                                 │
└────────────────────────────────┬─────────────────────────────────────┘
                                 │ Queries
                                 ↓
┌──────────────────────────────────────────────────────────────────────┐
│                        Prometheus (XPS 15)                           │
│                         Metrics Aggregation                          │
│                            Port 9090                                 │
└──────────────┬───────────────────────────────────────┬───────────────┘
               │ Scrapes (15s interval)                │
               ↓                                       ↓
    ┌──────────────────────┐              ┌──────────────────────┐
    │ Desktop Metrics      │              │ XPS 15 Metrics       │
    ├──────────────────────┤              ├──────────────────────┤
    │ • DCGM Exporter      │              │ • Node Exporter      │
    │   (GPU metrics)      │              │   (CPU, RAM, disk)   │
    │ • Node Exporter      │              │ • cAdvisor           │
    │   (System metrics)   │              │   (Container stats)  │
    │ • cAdvisor           │              │ • Service endpoints  │
    │   (Container stats)  │              │   (n8n, MLflow)      │
    │ • NIM metrics        │              │                      │
    │ • Triton metrics     │              │                      │
    └──────────────────────┘              └──────────────────────┘

Key Metrics Tracked:
┌────────────────────────┬──────────────────┬───────────────────┐
│ GPU (Desktop)          │ CPU (XPS 15)     │ Network           │
├────────────────────────┼──────────────────┼───────────────────┤
│ • Utilization (%)      │ • Utilization    │ • Throughput      │
│ • VRAM usage (GB)      │ • Memory usage   │ • Latency (ms)    │
│ • Temperature (°C)     │ • Disk I/O       │ • Packet loss     │
│ • Power draw (W)       │ • Process count  │ • Bandwidth       │
│ • Tensor Core activity │ • Load average   │ • Connections     │
│ • SM occupancy         │ • Context switch │                   │
└────────────────────────┴──────────────────┴───────────────────┘

Alerting Rules:
• GPU utilization < 50% during training (underutilization)
• VRAM usage > 90% (risk of OOM)
• Inference latency > 100ms (performance degradation)
• Network throughput < 1 Gbps (bottleneck)
• Container restarts > 3 in 5 minutes (stability issue)
```

## Security Layers

```
┌─────────────────────────────────────────────────────────────────────┐
│                        SECURITY ARCHITECTURE                         │
└─────────────────────────────────────────────────────────────────────┘

Network Security:
┌────────────────────────────────────────────────────────────────────┐
│ Internet → EdgeRouter → UniFi Security Gateway (Firewall)          │
│                                                                    │
│ Rules:                                                             │
│ • Block all incoming except SSH (key-based)                       │
│ • Allow outbound for NGC registry, GitHub                         │
│ • Internal network: 192.168.1.0/24                                │
│ • DMZ for external services (if needed)                           │
└────────────────────────────────────────────────────────────────────┘

Docker Swarm Security:
┌────────────────────────────────────────────────────────────────────┐
│ • TLS encryption for swarm communication                           │
│ • Mutual authentication between nodes                              │
│ • Overlay network isolation (gpu_net ≠ cpu_net)                   │
│ • Secrets management (NGC keys, DB passwords)                      │
│ • No privileged containers (except DCGM)                           │
└────────────────────────────────────────────────────────────────────┘

Data Security:
┌────────────────────────────────────────────────────────────────────┐
│ • NAS: NFSv4 with IP-based ACLs                                    │
│ • Encryption at rest (LUKS on NVMe)                                │
│ • Backup encryption (GPG)                                          │
│ • No data leaves local network (privacy-first)                     │
│ • Obsidian vault: local-only, no sync services                     │
└────────────────────────────────────────────────────────────────────┘

Application Security:
┌────────────────────────────────────────────────────────────────────┐
│ • n8n: Basic auth, HTTPS (if exposed)                              │
│ • Grafana: Strong password, read-only viewers                      │
│ • PostgreSQL: Non-default port, strong password                    │
│ • NIM API: Internal network only                                   │
│ • Regular updates: weekly security patches                         │
└────────────────────────────────────────────────────────────────────┘
```

## Scalability Roadmap

```
┌─────────────────────────────────────────────────────────────────────┐
│                      SCALABILITY EVOLUTION                           │
└─────────────────────────────────────────────────────────────────────┘

Phase 1: Current (Q4 2025)
┌──────────────┐    ┌──────────────┐
│   Desktop    │────│   XPS 15     │
│ (GPU Manager)│    │ (CPU Worker) │
└──────────────┘    └──────────────┘
       ↕                   ↕
   [WD NAS] ────────────────
Workload: 8B models, single-user, batch inference


Phase 2: Horizontal Scale (Q2 2026)
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│   Desktop    │────│   XPS 15     │────│  GPU Node 2  │
│ (GPU Manager)│    │ (CPU Worker) │    │ (GPU Worker) │
└──────────────┘    └──────────────┘    └──────────────┘
       ↕                   ↕                   ↕
   [WD NAS] ─────────────────────────────────────
Workload: 70B models, multi-GPU, parallel inference


Phase 3: Specialized Nodes (Q4 2026)
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│   Desktop    │────│   XPS 15     │────│   Vision     │
│  (LLM Inf.)  │    │ (CPU Coord.) │    │  (CV Models) │
└──────────────┘    └──────────────┘    └──────────────┘
       │                   │                   │
       ├───────────────────┼───────────────────┤
       │                                       │
┌──────────────┐                      ┌──────────────┐
│   Wireless   │                      │  [10G NAS]   │
│ (Aerial/5G)  │                      │   (RDMA)     │
└──────────────┘                      └──────────────┘
Workload: Multi-modal, research domains, 10G backbone


Phase 4: Edge + Cloud (Q2 2027)
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│   Desktop    │────│   XPS 15     │────│  GPU Cluster │
│  (Local Inf.)│    │ (Coordinator)│    │  (Training)  │
└──────────────┘    └──────────────┘    └──────────────┘
       │                   │                   │
       │                   │                   │
   ┌───────┐          [10G NAS]          [Cloud VMs]
   │ XPS 13│          (Primary)          (Burst Compute)
   │ (Edge)│
   └───────┘
   Mobile Client
Workload: Edge inference, cloud training, hybrid deployment
```

---

**Legend:**
- `[ ]` = Hardware device
- `( )` = Role/function
- `→` = Data flow
- `↔` = Bidirectional communication
- `┌─┐` = Service/container boundary
- `═══` = High-bandwidth connection
- `───` = Standard connection

**Performance Expectations:**
- Desktop → XPS 15: 2.5 Gbps (hardwired)
- Desktop → NAS: ~280 MB/s (via 2.5G, through USG)
- NVMe → VRAM: 15 GB/s (PCIe Gen5)
- DDR5 Bandwidth: 51.2 GB/s (dual-channel)
- GPU Memory: 896 GB/s (GDDR6X)

**Next Steps:**
1. Review this architecture against your actual network
2. Adjust IP addresses and hardware specs as needed
3. Follow deployment guide in QUICK_START.md
4. Monitor actual vs. expected performance
