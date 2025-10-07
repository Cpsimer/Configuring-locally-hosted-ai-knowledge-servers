# Docker Swarm Quick Start Guide

This guide walks through the complete setup of your AI ecosystem using Docker Swarm.

## Prerequisites

- Desktop: Ubuntu 25.10, CUDA 13.0.1, Driver 580.95.05, Docker Engine installed
- XPS 15: Ubuntu (or Windows with WSL2), Docker Engine installed
- Both machines on 2.5G network
- NAS accessible from both machines

## Step 1: Prepare Environment Variables

Create `.env` file in the project root:

```bash
# Network
DESKTOP_IP=192.168.1.100  # Replace with your Desktop IP
XPS15_IP=192.168.1.101     # Replace with your XPS 15 IP
NAS_IP=192.168.1.50        # Replace with your NAS IP

# Credentials
NGC_API_KEY=your_ngc_api_key_here
DB_USER=mlops_admin
DB_PASSWORD=secure_password_here
N8N_USER=admin
N8N_PASSWORD=secure_password_here
GRAFANA_USER=admin
GRAFANA_PASSWORD=secure_password_here
```

## Step 2: Initialize Docker Swarm

### On Desktop (Manager Node)

```bash
# Initialize Swarm
docker swarm init --advertise-addr $DESKTOP_IP

# Save the join token for workers
docker swarm join-token worker

# Label this node for GPU workloads
docker node update --label-add gpu=true --label-add type=manager $(docker node ls -q -f "role=manager")
```

### On XPS 15 (Worker Node)

```bash
# Join the swarm (use token from Desktop)
docker swarm join --token SWMTKN-1-... $DESKTOP_IP:2377

# Back on Desktop, label the XPS 15
docker node update --label-add cpu=true --label-add type=worker <XPS15_NODE_ID>

# Verify nodes
docker node ls
```

Expected output:
```
ID                            HOSTNAME    STATUS    AVAILABILITY    MANAGER STATUS    ENGINE VERSION
abc123... *                   desktop     Ready     Active          Leader            24.0.7
def456...                     xps15       Ready     Active                            24.0.7
```

## Step 3: Create Docker Secrets

```bash
# Create secrets for sensitive data
echo "your_ngc_api_key" | docker secret create ngc_api_key -
echo "secure_db_password" | docker secret create db_password -
```

## Step 4: Prepare Storage Directories

### On Desktop

```bash
# Create mount points
sudo mkdir -p /mnt/models /mnt/data /mnt/obsidian
sudo chown -R $USER:$USER /mnt/models /mnt/data /mnt/obsidian

# Mount NAS (or add to /etc/fstab for persistence)
sudo mount -t nfs $NAS_IP:/models /mnt/models
sudo mount -t nfs $NAS_IP:/data /mnt/data
sudo mount -t nfs $NAS_IP:/obsidian /mnt/obsidian

# For persistent mounting, add to /etc/fstab:
echo "$NAS_IP:/models /mnt/models nfs4 defaults,_netdev 0 0" | sudo tee -a /etc/fstab
echo "$NAS_IP:/data /mnt/data nfs4 defaults,_netdev 0 0" | sudo tee -a /etc/fstab
echo "$NAS_IP:/obsidian /mnt/obsidian nfs4 defaults,_netdev 0 0" | sudo tee -a /etc/fstab

# Create local directories
mkdir -p triton_configs trex_api preprocessing_scripts nemo_scripts trt_scripts
mkdir -p n8n_workflows grafana_dashboards postgres_init
```

### On XPS 15

```bash
# Same NAS mounts
sudo mkdir -p /mnt/data /mnt/obsidian
sudo mount -t nfs $NAS_IP:/data /mnt/data
sudo mount -t nfs $NAS_IP:/obsidian /mnt/obsidian

# Local directories for services
sudo mkdir -p /mnt/n8n /mnt/postgres /mnt/prometheus /mnt/grafana
sudo chown -R $USER:$USER /mnt/n8n /mnt/postgres /mnt/prometheus /mnt/grafana
```

## Step 5: Deploy Supporting Services

### Install Node Exporter (both nodes)

```bash
# On Desktop and XPS 15
docker run -d \
  --name node-exporter \
  --restart always \
  --net host \
  --pid host \
  -v "/:/host:ro,rslave" \
  prom/node-exporter:latest \
  --path.rootfs=/host
```

### Install cAdvisor (both nodes)

```bash
# On Desktop and XPS 15
docker run -d \
  --name cadvisor \
  --restart always \
  --volume=/:/rootfs:ro \
  --volume=/var/run:/var/run:ro \
  --volume=/sys:/sys:ro \
  --volume=/var/lib/docker/:/var/lib/docker:ro \
  --volume=/dev/disk/:/dev/disk:ro \
  --publish=8080:8080 \
  --privileged \
  --device=/dev/kmsg \
  gcr.io/cadvisor/cadvisor:latest
```

## Step 6: Deploy the AI Ecosystem Stack

```bash
# From project root on Desktop
docker stack deploy -c docker-swarm-stack.yml ai_ecosystem

# Wait for services to start (this may take 5-10 minutes)
watch docker service ls
```

Expected output after deployment:
```
ID             NAME                             MODE         REPLICAS   IMAGE
abc123...      ai_ecosystem_nim_inference       replicated   1/1        nvcr.io/nim/...
def456...      ai_ecosystem_triton_server       replicated   1/1        nvcr.io/nvidia/tritonserver:...
ghi789...      ai_ecosystem_n8n_automation      replicated   1/1        n8nio/n8n:latest
jkl012...      ai_ecosystem_postgres_mlops      replicated   1/1        postgres:16-alpine
...
```

## Step 7: Verify Deployment

### Check Service Health

```bash
# View all services
docker service ls

# Check specific service
docker service ps ai_ecosystem_nim_inference

# View logs
docker service logs -f ai_ecosystem_nim_inference
```

### Test GPU Access

```bash
# Exec into NIM container
docker exec -it $(docker ps -q -f name=nim_inference) nvidia-smi

# Should show RTX 5070 Ti
```

### Test NIM Inference

```bash
curl -X POST http://$DESKTOP_IP:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama-3.1-8b-instruct",
    "messages": [{"role": "user", "content": "Hello!"}],
    "max_tokens": 100
  }'
```

### Access Web Interfaces

- **n8n:** http://$DESKTOP_IP:5678 (admin / your_password)
- **Grafana:** http://$DESKTOP_IP:3000 (admin / your_password)
- **Prometheus:** http://$DESKTOP_IP:9090
- **MLflow:** http://$DESKTOP_IP:5001

## Step 8: Scale Services

### Scale Training Job

```bash
# Start NeMo training
docker service scale ai_ecosystem_nemo_training=1

# Scale down when complete
docker service scale ai_ecosystem_nemo_training=0
```

### Scale Preprocessing

```bash
# Start preprocessing on XPS 15
docker service scale ai_ecosystem_data_preprocessing=1

# Run preprocessing
docker exec -it $(docker ps -q -f name=data_preprocessing) \
  python /scripts/preprocess.py \
  --mode training \
  --input /data/raw/dataset.csv \
  --output /data/processed/train
```

## Step 9: Deploy T-Rex Model

After training the T-Rex model:

```bash
# Copy model to shared storage
cp -r trex_model.nemo /mnt/models/trex/

# Export to ONNX (in nemo container)
docker exec -it $(docker ps -q -f name=nemo_training) bash
python -c "
from nemo.collections.nlp.models import TextClassificationModel
model = TextClassificationModel.restore_from('/models/trex/trex_model.nemo')
model.export('/models/trex/trex.onnx', export_format='onnx')
"

# Update Triton model repository
# Create /mnt/models/trex/config.pbtxt (see triton_configs/)

# Restart Triton to load new model
docker service update --force ai_ecosystem_triton_server
```

## Step 10: Configure n8n Workflows

1. Access n8n at http://$DESKTOP_IP:5678
2. Import workflows from `n8n_workflows/` directory
3. Configure credentials:
   - GitHub (for webhook)
   - T-Rex API endpoint: http://trex_classifier:5000
   - Obsidian vault path: /obsidian

## Troubleshooting

### Service Won't Start

```bash
# Check placement constraints
docker service ps ai_ecosystem_SERVICE_NAME --no-trunc

# Check node availability
docker node ls

# Inspect service
docker service inspect ai_ecosystem_SERVICE_NAME
```

### GPU Not Accessible

```bash
# Verify NVIDIA Container Toolkit
docker run --rm --gpus all nvidia/cuda:12.0-base nvidia-smi

# Check Docker daemon.json
cat /etc/docker/daemon.json
```

Should contain:
```json
{
  "runtimes": {
    "nvidia": {
      "path": "nvidia-container-runtime",
      "runtimeArgs": []
    }
  },
  "default-runtime": "nvidia"
}
```

### Network Connectivity Issues

```bash
# Test inter-node communication
docker exec $(docker ps -q -f name=nim_inference) ping n8n_automation

# Check overlay network
docker network inspect ai_ecosystem_gpu_net
```

### NAS Mount Issues

```bash
# Test NAS connectivity
ping $NAS_IP

# Check mount
df -h | grep mnt

# Remount if needed
sudo umount /mnt/models
sudo mount -t nfs $NAS_IP:/models /mnt/models
```

## Performance Tuning

### Optimize NIM Settings

Edit docker-swarm-stack.yml:

```yaml
# Increase batch size for higher throughput
- NIM_MAX_BATCH_SIZE=256  # Default: 128

# Enable FP8 (if model supports)
- NIM_QUANTIZATION=fp8

# Adjust tensor parallelism
- NIM_TENSOR_PARALLEL_SIZE=1  # 1 for single GPU
```

### Optimize Triton

```bash
# Increase instance count
# Edit triton_configs/config.pbtxt:
instance_group [
  {
    count: 2  # Run 2 concurrent instances
    kind: KIND_GPU
  }
]
```

### Network Optimization

```bash
# Enable jumbo frames on 2.5G switch
# Configure MTU=9000 on both nodes
sudo ip link set eth0 mtu 9000
```

## Monitoring

### Check GPU Utilization

```bash
# Via DCGM exporter
curl http://$DESKTOP_IP:9400/metrics | grep gpu_utilization

# Via Grafana dashboard
# Import dashboard from grafana_dashboards/gpu_monitoring.json
```

### Check System Resources

Access Grafana → Prometheus dashboard → Explore:

```promql
# GPU memory usage
DCGM_FI_DEV_FB_USED / DCGM_FI_DEV_FB_FREE * 100

# Container CPU usage
rate(container_cpu_usage_seconds_total[5m])

# Network throughput
rate(node_network_receive_bytes_total[5m])
```

## Backup & Recovery

### Backup Critical Data

```bash
# Create backup script
cat > /usr/local/bin/ai_backup.sh << 'EOF'
#!/bin/bash
BACKUP_DIR=/mnt/backup/$(date +%Y%m%d)
mkdir -p $BACKUP_DIR

# Backup models
rsync -av /mnt/models/ $BACKUP_DIR/models/

# Backup Obsidian vault
rsync -av /mnt/obsidian/ $BACKUP_DIR/obsidian/

# Backup databases
docker exec $(docker ps -q -f name=postgres_mlops) \
  pg_dump -U mlops_admin mlops > $BACKUP_DIR/mlops.sql

# Backup n8n workflows
rsync -av /mnt/n8n/ $BACKUP_DIR/n8n/
EOF

chmod +x /usr/local/bin/ai_backup.sh

# Schedule daily backups
echo "0 2 * * * /usr/local/bin/ai_backup.sh" | crontab -
```

## Next Steps

1. **Train T-Rex Model:** Follow Strategic-Roadmap.md Section 3.1
2. **Create n8n Workflows:** Implement Git → Obsidian automation
3. **Fine-tune LLM:** Use NeMo on Desktop for domain-specific models
4. **Optimize TensorRT:** Convert trained models for faster inference
5. **Scale Infrastructure:** Add third node when workloads increase

## Additional Resources

- [NVIDIA NIM Documentation](https://docs.nvidia.com/nim/)
- [Docker Swarm Docs](https://docs.docker.com/engine/swarm/)
- [n8n Documentation](https://docs.n8n.io/)
- [Strategic Roadmap](./Strategic-Roadmap.md)
