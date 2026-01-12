	# Stationary Workhorse (XPS 15 7590)
## Hardware Specs
- **CPU**: Intel Core i9-9980HK (Model 158, ~2.4GHz base)
- **GPU0**: Intel(R) UHD graphics 630
- **GPU1**: Nvidia GeForce 1650
- **RAM**: 64GB
- **Storage**: 1TB NVMe KXG60ZNV1T02 NVMe KIOXIA 1024gb
- **OS**: ProxMox VE 9.1.2
- **Network**: USB-C to 2.5GbE adapter
## Operating System Specs
### Proxmox VE 9.1.4

#### **[[LXC 1 (Sclimers-Gateway)]]** 

##### NGINX
	nginx-proxy-manager:latest
##### Portainer 
	portainer/portainer-ce:its
##### Uptime Kuma 
	louislam/uptime-kuma:1

#### **[[LXC 2 (Sclimers-Core-Operations)]]**

##### N8N 
	n8nio/n8n:stable

#### **[[LXC 3 (Sclimers-Verification-Operations)]]**

##### Vault
	hashicorp/vault:1.21

###### Authentik
	beryju/authentik:latest

###### Redis
	redis:latest

#### **[[LXC 4 (Sclimers-Data-Operations)]]**

##### PostgreSQL
	postgres:latest

##### Dockage
	louislam/dockge

#### **[[LXC 5 (Sclimers-Observation)]]**

##### Prometheus 
	prom/prometheus:latest

##### Grafana
	grafana/grafana:latest

##### Loki
	grafana/loki:latest


#### **[[LXC 6 (Schlimers-Runner)]]**

###### Jenkins 
	jenkins/jenkins:its

###### Gitea
	gitea:gitea:latest


[[../Microservices/Resources]]  