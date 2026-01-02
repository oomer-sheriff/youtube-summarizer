# Deployment Guide

This project supports multiple deployment targets.

## 1. Local Development (Docker Compose)
Best for testing changes with **GPU acceleration** on Windows/WSL2.

### Prerequisites
- Docker Desktop (Windows/Mac/Linux)
- NVIDIA GPU (Optional, but recommended)

### Run
```bash
docker-compose up --build
```
This starts all services:
- **Backend**: http://localhost:8001/docs
- **RabbitMQ**: http://localhost:15672 (guest/guest)
- **Workers**: Auto-connected to GPU.

---

## 2. Local Kubernetes (Docker Desktop / Minikube)
Best for verifying production manifests.
*Note: GPU support on Docker Desktop (Windows) is often unstable. It is recommended to use CPU-only mode for local K8s verification.*

### Prerequisites
- `kubectl` installed.
- Kubernetes enabled in Docker Desktop.

### Deploy
```bash
# 1. Apply Manifests
kubectl apply -f k8s/

# 2. Check Status
kubectl get pods
```

### Access Services
- **Backend**: http://localhost:30001/docs (NodePort)
- **RabbitMQ**: http://localhost:30072 (NodePort)

---

## 3. Production (AWS EKS)
Best for scalable, GPU-accelerated production workloads.

### Prerequisites
- **AWS CLI**: Configured.
- **eksctl**: Installed.
- **kubectl**: Installed.

### Step 1: Create Cluster
Create a cluster with GPU-enabled nodes (`g4dn` instances recommendation):
```bash
eksctl create cluster \
  --name youtube-summarizer-cluster \
  --region us-east-1 \
  --nodegroup-name gpu-nodes \
  --node-type g4dn.xlarge \
  --nodes 2 \
  --managed
```
*Tip: EKS automatically installs NVIDIA drivers on GPU nodes.*

### Step 2: Connect kubectl
```bash
aws eks update-kubeconfig --region us-east-1 --name youtube-summarizer-cluster
```

### Step 3: Configure Storage
The default manifests use `hostPath` which works locally but not on empty cloud nodes. 
**Recommended**: Update `worker-chat.yaml` and `worker-transcript.yaml` to use ephemeral storage:

```yaml
      volumes:
      - name: hf-cache
        emptyDir: {}
```

### Step 4: Deploy
```bash
kubectl apply -f k8s/
```

### Step 5: Expose Publicly
To get a public URL (ALB), edit `k8s/backend.yaml`:
```yaml
spec:
  type: LoadBalancer
```
Run `kubectl get svc backend` to see your external IP/DNS.
