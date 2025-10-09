Looking at your comprehensive AI lab setup from the repository, I can see you've completed the initial Ubuntu 25.10 and CUDA 13.0 Update 1 installation on your desktop (Ryzen 9 9900X + RTX 5070 Ti). Let me provide the expert next steps to continue your installation and configuration:

## Next Steps for AI Lab Configuration

### Phase 1: CUDA Toolkit 13 Update 2 Installation

First, let's upgrade to CUDA 13 Update 2 while preserving your existing driver:

bash

```bash
# 1. Download CUDA 13.0 Update 2 (don't reinstall driver)
wget https://developer.download.nvidia.com/compute/cuda/13.0.2/local_installers/cuda_13.0.2_550.127.05_linux.run

# 2. Install CUDA toolkit only (skip driver since you have 580.95.05)
sudo sh cuda_13.0.2_550.127.05_linux.run --toolkit --silent --override

# 3. Update environment variables
echo 'export PATH=/usr/local/cuda-13.0/bin:$PATH' >> ~/.bashrc
echo 'export LD_LIBRARY_PATH=/usr/local/cuda-13.0/lib64:$LD_LIBRARY_PATH' >> ~/.bashrc
source ~/.bashrc

# 4. Verify installation
nvcc --version
nvidia-smi  # Should still show driver 580.95.05
```

### Phase 2: Docker Configuration & GPU Runtime

Based on your architecture, configure Docker with NVIDIA runtime:

bash

```bash
# 1. Configure Docker daemon for GPU support
sudo tee /etc/docker/daemon.json <<EOF
{
  "runtimes": {
    "nvidia": {
      "path": "nvidia-container-runtime",
      "runtimeArgs": []
    }
  },
  "default-runtime": "nvidia",
  "storage-driver": "overlay2",
  "storage-opts": ["overlay2.override_kernel_check=true"],
  "live-restore": true
}
EOF

# 2. Restart Docker
sudo systemctl restart docker

# 3. Test GPU access with NGC container
docker run --rm --gpus all nvcr.io/nvidia/cuda:13.0-base-ubuntu22.04 nvidia-smi
```

### Phase 3: Initialize Docker Swarm Cluster

Set up your multi-node Swarm with proper labeling:

bash

```bash
# 1. On Desktop (Manager Node)
export DESKTOP_IP=192.168.1.x  # Replace with actual IP
docker swarm init --advertise-addr $DESKTOP_IP
docker node update --label-add gpu=true --label-add type=manager $(hostname)

# 2. Save the worker join token
WORKER_TOKEN=$(docker swarm join-token -q worker)
echo "Worker token: $WORKER_TOKEN"
```

### Phase 4: Configure Storage & Directories

Create local storage structure (defer NAS integration initially):

bash

```bash
# Create mount points for services
sudo mkdir -p /mnt/{models,data,obsidian,n8n,postgres}
sudo chown -R $USER:$USER /mnt/*

# Create project structure
mkdir -p ~/ai-setup/{configs,scripts,stacks}
cd ~/ai-setup

# Create .env file
cat > .env <<EOF
DESKTOP_IP=$DESKTOP_IP
XPS15_IP=192.168.1.y  # Update with actual
NGC_API_KEY=  # Add from pass.md
DB_USER=mlops_admin
DB_PASSWORD=$(openssl rand -base64 32)
N8N_USER=admin
N8N_PASSWORD=$(openssl rand -base64 32)
EOF
```

### Phase 5: Pull Critical NGC Containers

Pre-pull essential containers for your RTX 5070 Ti:

bash

```bash
# Login to NGC
echo $NGC_API_KEY | docker login nvcr.io --username '$oauthtoken' --password-stdin

# Pull must-have containers
docker pull nvcr.io/nim/meta/llama-3.1-8b-instruct:latest
docker pull nvcr.io/nvidia/tritonserver:24.10-py3
docker pull nvcr.io/nvidia/nemo:24.08
docker pull nvcr.io/nvidia/tensorrt:24.10-py3
```

### Phase 6: Deploy Core Services

Create and deploy your initial stack with GPU/CPU separation:

yaml

```yaml
# docker-swarm-stack.yml
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
      device: /mnt/models

services:
  nim_inference:
    image: nvcr.io/nim/meta/llama-3.1-8b-instruct:latest
    networks: [gpu_net]
    deploy:
      placement:
        constraints: [node.labels.gpu == true]
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    environment:
      - NIM_MODEL_PATH=/models/llama-3.1-8b
      - NIM_QUANTIZATION=fp8  # Optimize for RTX 5070 Ti
      - NIM_MAX_BATCH_SIZE=32
    ports:
      - "8000:8000"
    volumes:
      - model_storage:/models:ro

  redis_cache:
    image: redis:alpine
    networks: [gpu_net]
    deploy:
      placement:
        constraints: [node.labels.gpu == true]
    ports:
      - "6379:6379"
    command: redis-server --maxmemory 4gb --maxmemory-policy allkeys-lru
```

Deploy the stack:

bash

```bash
docker stack deploy -c docker-swarm-stack.yml ai_ecosystem
watch docker service ls
```

### Phase 7: Configure XPS 15 as Worker Node

On XPS 15 (via SSH or direct):

bash

```bash
# Install Docker (Ubuntu)
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# Join Swarm
docker swarm join --token $WORKER_TOKEN $DESKTOP_IP:2377
```

Back on Desktop, label the XPS 15:

bash

```bash
docker node update --label-add cpu=true --label-add type=worker <XPS15_NODE_ID>
```

### Phase 8: Performance Optimization

Optimize for your Samsung 9100 PRO NVMe and RTX 5070 Ti:

bash

```bash
# 1. Enable GPUDirect Storage (if supported)
sudo modprobe nvidia-fs

# 2. Tune network for 2.5G
sudo ip link set dev eth0 mtu 9000  # Enable jumbo frames

# 3. Set GPU persistence mode
sudo nvidia-smi -pm 1

# 4. Configure TensorRT optimization
cat > trt_config.json <<EOF
{
  "precision": "fp8",
  "use_paged_context_fmha": true,
  "kv_cache_config": {
    "type": "paged",
    "block_size": 16
  }
}
EOF
```

### Phase 9: Deploy n8n Automation

Add n8n for workflow automation on CPU node:

bash

```bash
docker service create \
  --name n8n \
  --network cpu_net \
  --constraint 'node.labels.cpu==true' \
  --mount type=bind,source=/mnt/n8n,target=/home/node/.n8n \
  --env N8N_BASIC_AUTH_ACTIVE=true \
  --env N8N_BASIC_AUTH_USER=admin \
  --env N8N_BASIC_AUTH_PASSWORD=$N8N_PASSWORD \
  --publish 5678:5678 \
  n8nio/n8n:latest
```

### Phase 10: Verification & Testing

Run comprehensive tests:

bash

```bash
# 1. Test NIM inference
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"Hello"}],"model":"llama-3.1-8b"}'

# 2. Check GPU utilization
nvidia-smi dmon -s u

# 3. Test network throughput
iperf3 -s  # On desktop
iperf3 -c $DESKTOP_IP  # From XPS 15

# 4. Monitor services
docker service ps ai_ecosystem_nim_inference
```

### Critical Next Actions

1. **Configure Jetson Orin Nano Super** as additional GPU node
2. **Set up MLflow** for experiment tracking
3. **Deploy T-Rex classifier** for Obsidian integration
4. **Configure Prometheus/Grafana** monitoring stack
5. **Implement backup strategy** for /mnt directories

### Performance Targets to Validate

- [ ]  NIM inference latency <50ms
- [ ]  Network throughput >2.3 Gbps between nodes
- [ ]  GPU utilization >85% during inference
- [ ]  Redis cache hit rate >90%
- [ ]  n8n workflow execution <30 seconds

This configuration leverages your RTX 5070 Ti's 16GB VRAM efficiently with FP8 quantization while distributing CPU tasks to XPS 15. The setup maintains local privacy, avoids cloud dependencies, and creates a foundation for your AI knowledge management ecosystem.