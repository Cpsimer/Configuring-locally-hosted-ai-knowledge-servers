## [[Prompts Used]] 

This guide consolidates all discussions, constraints, and updates from the conversation and repository. It walks you through configuring your **Dell XPS 13** (Windows 11 Home, Intel Core Ultra 7 258V, 32 GB RAM, Intel Arc with ~18 GB VRAM, 512 GB SSD) and your **Ubuntu desktop workstation** (Ubuntu 25.10, AMD Ryzen 9 9900X, 128 GB RAM, NVIDIA RTX 5070 Ti with CUDA 13.0 Update 1, driver 580.95.05, NVIDIA Container Toolkit 1.17.8, Obsidian 1.9.14). The plan prioritizes **Must‑Have** items first, integrates impactful **Should‑Have** software for extra performance, and maintains privacy by running everything locally.

---

## 1. Hardware & Network Verification

1. **Check Desktop Workstation**
    
    - Ensure Ubuntu 25.10 is updated (`sudo apt update && sudo apt upgrade`).
        
    - Verify NVIDIA driver and CUDA versions:
        
        `nvidia-smi  # should show driver 580.95.05 and compute capability nvcc --version  # confirm CUDA 13.0`
        
    - Confirm `nvidia-container-toolkit` v1.17.8 is installed (`dpkg -l | grep nvidia-container-toolkit`).
        
    - Make sure the desktop is wired directly to the UniFi Flex Mini switch (2.5 G) using Cat6.
        
2. **Check Dell XPS 13**
    
    - [[Special xps13 configuration before ubuntu25.10 release]] 
        
    - Enable virtualization (Hyper‑V and WSL2) in Windows Features.
        
    - Connect the 2.5 G USB‑C adapter to the Flex Mini switch and verify >2 Gbps throughput using `iperf3`.
        
3. **General Network Prep**
    
    - Defer WD NAS integration. Instead, create local directories on each host for models (`/mnt/models`), data (`/mnt/data`), and the Obsidian vault (`/mnt/obsidian`).
        
    - Ensure both machines can ping each other (e.g., `ping 192.168.1.10`).
        
    - Record IP addresses for use in environment variables (`$DESKTOP_IP`, `$XPS13_IP`).
        

**✔️ Confirm the hardware and network are functioning before moving forward.**

---

## 2. Environment Preparation

1. **Create Local Storage (both hosts)**
    
    `sudo mkdir -p /mnt/models /mnt/data /mnt/obsidian /mnt/n8n /mnt/postgres sudo chown $USER:$USER /mnt/models /mnt/data /mnt/obsidian /mnt/n8n /mnt/postgres`
    
2. **Clone Repository**
    
    `git clone https://github.com/yourusername/Configuring-locally-hosted-ai-knowledge-servers.git ~/ai-setup cd ~/ai-setup`
    
3. **Prepare `.env` File**  
    In the project root, create `.env`:
    
    `DESKTOP_IP=192.168.1.x XPS13_IP=192.168.1.y NGC_API_KEY= # retrieve from pass.md DB_USER=mlops_admin DB_PASSWORD=your_db_password N8N_USER=admin N8N_PASSWORD=your_n8n_password`
    
4. **Create Docker Secrets** (on desktop)
    
    `echo "$NGC_API_KEY" | docker secret create ngc_api_key - echo "$DB_PASSWORD" | docker secret create db_password -`
    

---

## 3. Docker Installation & Configuration

### Desktop (Ubuntu 25.10)

1. **Install Docker Engine**
    
    `sudo apt-get update sudo apt-get install -y ca-certificates curl gnupg curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg echo \   "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] \   https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | \   sudo tee /etc/apt/sources.list.d/docker.list > /dev/null sudo apt-get update sudo apt-get install -y docker-ce docker-ce-cli containerd.io`
    
2. **Configure NVIDIA Runtime**  
    Create or edit `/etc/docker/daemon.json`:
    
    `{   "runtimes": {     "nvidia": {       "path": "nvidia-container-runtime",       "runtimeArgs": []     }   },   "default-runtime": "nvidia" }`
    
    Restart Docker:
    
    `sudo systemctl restart docker`
    
3. **Test GPU Access**
    
    `docker run --rm --gpus all nvidia/cuda:12.0-base nvidia-smi`
    

### XPS 13 (Windows 11)

1. **Install Docker Desktop**
    
    - Download and install Docker Desktop for Windows.
        
    - Enable WSL2 and the integrated Intel GPU support in Docker Desktop settings.
        
2. **Install Ubuntu (WSL2)**
    
    - From Microsoft Store, install Ubuntu LTS.
        
    - Set resource limits in Docker Desktop (e.g., 16 GB RAM, 6 cores).
        
3. **Pull Base Images** (optional test)
    
    `docker run hello-world`
    

---

## 4. Swarm Initialization & Node Labeling

1. **Initialize Swarm on Desktop**
    
    `docker swarm init --advertise-addr $DESKTOP_IP docker node update --label-add gpu=true --label-add type=manager $(hostname)`
    
    Save the worker join token.
    
2. **Join Swarm from XPS 13 (WSL2)**
    
    `docker swarm join --token <TOKEN> $DESKTOP_IP:2377`
    
3. **Label XPS 13 Node**
    
    `docker node update --label-add cpu=true --label-add gpu_light=true <XPS13_NODE_ID>`
    
4. **Verify Nodes**
    
    `docker node ls`
    

**✔️ Confirm both nodes show `Ready` status before proceeding.**

---

## 5. Build the Docker Swarm Stack

Use `docker-swarm-stack.yml` as a template. Adjust it for local storage (no NAS) and include Must‑Have services with appropriate placement constraints.

### 5.1 Define Networks & Volumes

`version: '3.8'  networks:   gpu_net:     driver: overlay     attachable: true   cpu_net:     driver: overlay     attachable: true  volumes:   model_storage:     driver: local     driver_opts:       type: none       o: bind       device: /mnt/models   data_storage:     driver: local     driver_opts:       type: none       o: bind       device: /mnt/data   obsidian_vault:     driver: local     driver_opts:       type: none       o: bind       device: /mnt/obsidian   n8n_data:     driver: local     driver_opts:       type: none       o: bind       device: /mnt/n8n   postgres_data:     driver: local     driver_opts:       type: none       o: bind       device: /mnt/postgres`

### 5.2 Must‑Have Services

- **NIM Inference** (GPU, desktop only)
    
- **Triton Inference Server** (GPU)
    
- **NeMo Training** (on‑demand GPU)
    
- **TensorRT Optimizer** (on‑demand GPU)
    
- **n8n Automation** (CPU/GPU‑light on XPS 13)
    
- **PostgreSQL** (for MLflow or n8n; CPU)
    
- **Redis Cache** (GPU node for low latency)
    

Example snippet:

`services:   nim_inference:     image: nvcr.io/nim/meta/llama-3.1-8b-instruct:latest     networks: [gpu_net]     volumes: [model_storage:/models:ro]     deploy:       placement:         constraints:           - node.labels.gpu == true       resources:         reservations:           devices:             - driver: nvidia               count: 1               capabilities: [gpu]     environment:       - NIM_MODEL_PATH=/models/llama-3.1-8b     ports:       - "8000:8000"    n8n_automation:     image: n8nio/n8n:latest     networks: [cpu_net]     volumes:       - n8n_data:/home/node/.n8n       - obsidian_vault:/obsidian     deploy:       placement:         constraints:           - node.labels.cpu == true     environment:       - N8N_BASIC_AUTH_ACTIVE=true       - N8N_BASIC_AUTH_USER=${N8N_USER}       - N8N_BASIC_AUTH_PASSWORD=${N8N_PASSWORD}       - N8N_HOST=0.0.0.0       - N8N_PORT=5678     ports:       - "5678:5678"`

Add similar definitions for other Must‑Have services, referencing the strategic roadmap.

---

## 6. Should‑Have Enhancements

### 6.1 RAPIDS Service (GPU Preprocessing)

  `rapids_preprocessing:     image: rapidsai/rapidsai-core:24.06-cuda13.0-runtime-ubuntu22.04     networks: [gpu_net]     volumes:       - data_storage:/data       - model_storage:/models     deploy:       placement:         constraints:           - node.labels.gpu == true     command: >       bash -c "python /scripts/rapids_preprocess.py"`

- **rapids_preprocess.py**: Use cuDF and Dask to accelerate ETL; write outputs to `/data/processed`.
    

### 6.2 PyTorch Geometric Service (Graph ML)

  `graph_ml:     image: pytorch/pytorch:2.3.0-cuda13.0-cudnn8-runtime     networks: [gpu_net]     volumes:       - obsidian_vault:/obsidian     deploy:       placement:         constraints:           - node.labels.gpu == true     command: >       bash -c "python /scripts/build_graph.py && python /scripts/link_predict.py"`

- **build_graph.py**: Extract a graph from Obsidian notes (tags, links).
    
- **link_predict.py**: Use PyG to generate node embeddings; integrate results into T‑Rex suggestions.
    

### 6.3 Nsight Tools

- Install Nsight Compute and Nsight Systems on the **desktop host** (not in containers):
    
    `sudo apt-get install -y nvidia-nsight nvidia-nsight-compute`
    
- Use them to profile GPU kernels and optimize model tuning and TensorRT settings.
    

---

## 7. Deploy & Verify

1. **Deploy the stack** (desktop):
    
    `source .env docker stack deploy -c docker-swarm-stack.yml ai_ecosystem`
    
2. **Monitor service startup**:
    
    `watch docker service ls`
    
    Wait for all replicas to reach 1/1.
    
3. **Test key services**:
    
    - **NIM API**: Send a sample chat request to confirm inference.
        
    - **n8n**: Open `http://$DESKTOP_IP:5678` and log in.
        
    - **RAPIDS**: Trigger a preprocessing task and compare runtime against the old CPU pipeline.
        
    - **Graph ML**: Run the graph extraction and verify that embeddings file appears in `/obsidian`.
        
4. **Set up monitoring** (optional but recommended):
    
    - Deploy node and DCGM exporters.
        
    - Add Prometheus and Grafana services for metrics visualization.
        

---

## 8. Obsidian Vault & T‑Rex Integration

1. **Prepare Obsidian Vault**
    
    - On both hosts, mount `/mnt/obsidian` and set up folders (`000‑System`, `100‑Distilary`, `Projects`, `Areas`, `Resources`, `900‑PKM`).
        
    - Use Obsidian 1.9.14 on the desktop, install Dataview, Templater, and (optionally) Smart Connections.
        
2. **T‑Rex Training**
    
    - Use the `preprocessing_scripts/preprocess.py` (mode `obsidian`) to extract notes and tags into a dataset for classification.
        
    - Train a BERT‑based classifier via the `nemo_training` service; export to ONNX; deploy via Triton.
        
3. **n8n Workflows**
    
    - Import the provided workflow JSONs (Git commit → Obsidian note, Training completion → Experiment note).
        
    - Configure credentials (GitHub API, T‑Rex endpoint, Obsidian path).
        
    - Trigger test commits and training runs to verify automated note creation.
        

---

## 9. Safety, Backups & Best Practices

- **Backups:** Implement a backup script for `/mnt/models`, `/mnt/data`, `/mnt/obsidian`, `/mnt/n8n`, and your Postgres database. Schedule it via cron to run nightly.
    
- **Driver Conflicts:** Only update NVIDIA/Intel drivers when corresponding CUDA/TensorRT containers support them. Test upgrades in a separate branch.
    
- **Data Persistence:** Avoid storing critical data inside containers. Always mount volumes from the host.
    
- **Security:** Keep NGC API keys and DB passwords in Docker secrets; never hard‑code them in YAML.
    
- **User Confirmations:** Pause after each major section (hardware check, Docker installation, Swarm initialization, stack deployment) to confirm success before proceeding.
    

---

## 10. Final Testing & Iteration

1. **Run an end‑to‑end workflow**:
    
    - Ingest a sample dataset via RAPIDS.
        
    - Fine‑tune a model with NeMo.
        
    - Optimize with TensorRT.
        
    - Deploy via NIM.
        
    - Classify a new note using T‑Rex.
        
    - Trigger n8n to capture a Git commit into Obsidian.
        
2. **Assess performance**:
    
    - Measure inference latency (<50 ms target), preprocessing throughput (aim for 5–10× with RAPIDS), and GPU utilization (>85 %).
        
    - Evaluate graph‑based suggestions and verify increased relevance.
        
3. **Iterate**:
    
    - Adjust batch sizes, precision modes, or service replicas based on Nsight profiling.
        
    - Consider adding other Should‑Have features (e.g., Magnum IO) once hardware supports RDMA and the NAS is reintegrated.
        
    - Explore Could‑Have items (Jupyter, Omniverse) only after core stability is achieved.
        

---

### ✅ Once you have followed all these steps and confirmed each service works as expected, your local AI‑accelerated environment will be fully operational, privacy‑respecting, and ready for rapid experimentation.

[[Coding sprint]]  

[[Expanded sprint]]  