# AI Ecosystem Documentation Index

## Overview

This repository contains the complete strategic roadmap and implementation files for building a high-performance, privacy-focused AI development and knowledge management ecosystem.

**System Architecture:**
- **Desktop:** RTX 5070 Ti GPU workstation (primary compute)
- **XPS 15:** CPU offload server (i9, 64GB RAM)
- **XPS 13:** Portable client
- **Network:** 2.5G topology via UniFi infrastructure
- **Orchestration:** Docker k8 ubuntu nvidia
- **Knowledge Management:** Obsidian vault with AI integration

## Quick Navigation


### 📋 Planning Documents

- **[MoSCoW Prioritization](./MoSCoW%20prioritization%20for%20software%20to%20include.md)** - Software stack priorities


### 🔧 Configuration Files

- **[Network Topology](./Network%20topology.md)** - Network infrastructure details
- **[Personal Hardware Specs]** - Hardware inventory




## Key Features

### System Architecture ()

- **Bottleneck Analysis:** Network optimization for 2.5G topology
- **Docker Swarm Strategy:** GPU/CPU workload distribution
- **GPUDirect Storage:** NVMe-to-VRAM optimization path

### AI Workflow ()

- **End-to-End Pipeline:** Data ingestion → Training → Optimization → Deployment
- **TensorRT Tuning:** FP8/FP16 precision modes, paged KV cache
- **Performance Targets:** <1ms inference latency, >98% GPU utilization

### Knowledge Management ()

- **T-Rex Model:** BERT-based taxonomy classifier for Obsidian
- **n8n Automation:** Git commits → Obsidian notes with AI tagging
- **MLflow Integration:** Experiment tracking → knowledge base

### Scalability (Strategic-Roadmap.md § 4)

- **Current:** 4-node Swarm (Desktop + XPS 15 + jetson nano super + xps 13)
- **Phase 2:** Add GPU node or specialized workers
- **Phase 3:** Edge deployment with XPS 13
- **Phase 4:** Hybrid cloud for burst compute


## Service Inventory

### GPU Services (Desktop)
- **nim_inference:** LLAMA-3.1-8B inference server (port 8000)
- **triton_server:** Multi-model serving (ports 8001-8003)
- **nemo_training:** On-demand training jobs
- **tensorrt_optimizer:** Model optimization
- **trex_classifier:** Taxonomy classification API (port 5000)
- **redis_cache:** Low-latency caching (port 6379)

### CPU Services (XPS 15)
- **n8n_automation:** Workflow automation (port 5678)
- **postgres_mlops:** Database backend (port 5432)
- **mlflow_server:** Experiment tracking (port 5001)
- **data_preprocessing:** Multi-core data processing
- **prometheus:** Metrics collection (port 9090)
- **grafana:** Visualization dashboards (port 3000)


## Critical Success Factors

1. ✅ **Desktop GPU exclusively for inference/training** (placement constraints)
2. ✅ **Desktop hardware maximized for total usage** (placement constraints)
3. ✅ **NAS accessible from  nodes** (unified storage)
4. ✅ **Obsidian vault on shared NFS** (n8n automation target)
5. ✅ **T-Rex model <50ms latency** (real-time classification)
6. ✅ **Automated Git or n8n → Obsidian pipeline** (knowledge capture)

## Security Considerations

- **NGC API Keys and other external api keys** 
- **Database Credentials:** Environment variables + secrets 
- **Network Isolation:** accelerate computing and security
- **NAS Access:** SSL
- **Local-First:** No cloud dependencies, full data sovereignty


## Technology Stack

### NVIDIA Software
- NIM Microservices (inference)
- NeMo Framework  (training)
- TensorRT  (optimization)
- Triton Inference Server (serving)
- DCGM Exporter (monitoring)

### Infrastructure
- Docker Engine + Swarm
- Ubuntu 25.10 (Desktop)
- CUDA 13.0.2, Driver 580.95.05
- UniFi networking (2.5G)

### Data & ML
- PyTorch (core framework)
- Transformers (model library)
- Datasets (data processing)
- MLflow (experiment tracking)

### Automation
- n8n (workflow automation)

### Knowledge Management
- Obsidian 1.9.14
- bases plugin
- Custom T-Rex classifier


### Feedback Welcome
- Performance optimization tips
- Architecture critique
- Tool recommendations
- Bug reports in configurations

## Resources

### Official Documentation
- [NVIDIA NIM](https://docs.nvidia.com/nim/)
- [NeMo Framework](https://docs.nvidia.com/nemo-framework/)
- [TensorRT-LLM](https://github.com/NVIDIA/TensorRT-LLM)
- [Docker Swarm](https://docs.docker.com/engine/swarm/)

### Community
- [r/LocalLLaMA](https://reddit.com/r/LocalLLaMA) - Self-hosted AI
- [NVIDIA Forums](https://forums.developer.nvidia.com/) - Technical support
- [n8n Community](https://community.n8n.io/) - Workflow automation
- [Obsidian Forum](https://forum.obsidian.md/) - Knowledge management



## License

Personal infrastructure configuration. 
