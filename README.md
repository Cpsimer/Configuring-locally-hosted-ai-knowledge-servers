# AI Ecosystem Documentation Index

## Overview

This repository contains the complete strategic roadmap and implementation files for building a high-performance, privacy-focused AI development and knowledge management ecosystem.

**System Architecture:**
- **Desktop:** RTX 5070 Ti GPU workstation (primary compute)
- **XPS 15:** CPU offload server (i9, 64GB RAM)
- **XPS 13:** Portable client
- **Network:** 2.5G topology via UniFi infrastructure
- **Orchestration:** Docker Swarm
- **Knowledge Management:** Obsidian vault with AI integration

## Quick Navigation


### 📋 Planning Documents

- **[End Goal for Application](./End%20Goal%20for%20application.md)** - Obsidian platform vision
- **[MoSCoW Prioritization](./MoSCoW%20prioritization%20for%20software%20to%20include.md)** - Software stack priorities
- **[Using Multiple Systems](./Using%20multiple%20systems%20to%20accelerate%20computing.md)** - Multi-node strategy

### 🔧 Configuration Files

- **[Network Topology](./Network%20topology.md)** - Network infrastructure details
- **[Personal Hardware Specs](./personal%20hardware%20specs.md)** - Hardware inventory
- **[Software Configuration](./Software%20and%20Firmware%20Configuration.md)** - Installed software versions




## Key Features

### System Architecture ()

- **Bottleneck Analysis:** Network optimization for 2.5G topology
- **Docker Swarm Strategy:** GPU/CPU workload distribution
- **GPUDirect Storage:** NVMe-to-VRAM optimization path

### AI Workflow ()

- **End-to-End Pipeline:** Data ingestion → Training → Optimization → Deployment
- **TensorRT Tuning:** FP8/FP16 precision modes, paged KV cache
- **Performance Targets:** <50ms inference latency, >85% GPU utilization

### Knowledge Management ()

- **T-Rex Model:** BERT-based taxonomy classifier for Obsidian
- **n8n Automation:** Git commits → Obsidian notes with AI tagging
- **MLflow Integration:** Experiment tracking → knowledge base

### Scalability (Strategic-Roadmap.md § 4)

- **Current:** 4-node Swarm (Desktop + XPS 15 + jetson nano super + xps 13)
- **Phase 2:** Add GPU node or specialized workers
- **Phase 3:** Edge deployment with XPS 13
- **Phase 4:** Hybrid cloud for burst compute

## Implementation Timeline

|Phase | Duration | Key Deliverables |
|-------|----------|------------------|
|  | Foundation | Swarm cluster, core services deployed |
|  | AI Pipeline | Training workflow, TensorRT optimization |
| ** | Automation | T-Rex model, n8n workflows active |
|  | Optimization | Performance tuning, documentation |
| | Advanced | PyTorch Geometric, load testing |

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

## Performance Targets

| Metric | Baseline | Target | Measurement Method |
|--------|----------|--------|-------------------|
| NIM Inference Latency | 200ms (PyTorch) | <50ms (TensorRT FP8) | curl benchmark |
| Model Fine-Tuning Time | N/A | <4 hours (8B, 10K samples) | NeMo logs |
| Data Preprocessing | N/A | >1M samples/hour | XPS 15 monitoring |
| Git → Obsidian Latency | N/A | <30 seconds | n8n execution time |
| T-Rex Accuracy | N/A | >85% F1-score | Validation set |
| Network Throughput | ~300 Mbps (Wi-Fi) | >2.3 Gbps (2.5G wired) | iperf3 |

## Critical Success Factors

1. ✅ **Desktop GPU exclusively for inference/training** (placement constraints)
3. ✅ **NAS accessible from  nodes** (unified storage)
4. ✅ **Obsidian vault on shared NFS** (n8n automation target)
5. ✅ **T-Rex model <50ms latency** (real-time classification)
6. ✅ **Automated Git or n8n → Obsidian pipeline** (knowledge capture)

## Security Considerations

- **NGC API Keys:** Stored as Docker secrets using pass
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
- Ubuntu 25.10 (Desktop), Ubuntu (XPS 15)
- CUDA 13.0.2, Driver 580.95.05
- UniFi networking (2.5G)

### Data & ML
- PyTorch (core framework)
- Transformers (model library)
- Datasets (data processing)
- MLflow (experiment tracking)

### Automation & Monitoring
- n8n (workflow automation)
- PostgreSQL (data storage)
- Prometheus (metrics)
- Grafana (visualization)
- Redis (caching)

### Knowledge Management
- Obsidian 1.9.14
- Dataview plugin
- Custom T-Rex classifier

## Future Enhancements

### Short-Term (3-6 months)
- [ ] RAPIDS for GPU-accelerated data science
- [ ] PyTorch Geometric for knowledge graph embeddings
- [ ] Nsight profiling for kernel optimization
- [ ] Second GPU node for distributed training

### Long-Term (6-12 months)
- [ ] Aerial SDK for wireless simulation
- [ ] Sionna for 6G research
- [ ] NAS upgrade with RDMA support
- [ ] GPUDirect Storage implementation

### Research Directions
- [ ] Multi-modal models (text + vision)
- [ ] Reinforcement learning pipelines
- [ ] Federated learning across nodes
- [ ] Quantum ML with Pennylane

## Contributing

This is a personal infrastructure project, but lessons learned are documented for the community.

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

### Learning Paths
1. **Week 1-2:** Docker Swarm basics, NGC container registry
2. **Week 3-4:** NeMo fine-tuning, TensorRT optimization
3. **Month 2:** Advanced workflows, distributed training
4. **Month 3+:** Research extensions (Aerial, PyG, RAPIDS)

## License

Personal infrastructure configuration. 
