# Complete Deployment Journey: Docker Compose → Kubernetes (microk8s)

## Summary

Successfully deployed the YouTube summarizer application from failing Docker Compose setup to a fully functional Kubernetes deployment on microk8s with GPU support.

---

## Phase 1: Fixing Docker Compose GPU Access

### Problem
Running `sudo docker-compose up --build` failed with:
```
nvidia-container-cli: initialization error: load library failed: 
libnvidia-ml.so.1: cannot open shared object file
```

### Root Cause
Docker was installed via **Snap**, which uses strict confinement that prevents containers from accessing host NVIDIA drivers.

### Solution Steps

1. **Uninstalled Snap Docker**
   ```bash
   sudo snap remove docker
   ```

2. **Installed Official Docker CE**
   ```bash
   sudo apt-get update
   sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
   ```

3. **Added User to Docker Group**
   ```bash
   sudo usermod -aG docker $USER
   ```

4. **Configured NVIDIA Container Runtime**
   ```bash
   sudo nvidia-ctk runtime configure --runtime=docker
   sudo systemctl restart docker
   ```

5. **Verified GPU Access**
   ```bash
   sudo docker run --rm --gpus all python:3.11-slim nvidia-smi
   ```
   ✅ Successfully showed GPU: NVIDIA GeForce RTX 3050 Laptop GPU

### Result
Docker Compose now works with GPU support. Use `docker compose` (v2) instead of `docker-compose` (deprecated).

---

## Phase 2: Attempting kind Deployment (Failed)

### Attempt
Created `kind-config.yaml` with GPU device mounts and tried deploying Kubernetes configs.

### Problem
kind runs K8s nodes as Docker containers. While we could mount `/dev` for GPU devices, the NVIDIA device plugin also needs NVIDIA libraries (`libnvidia-ml.so.1`) which exist on host but not inside the kind container.

### Why It Failed
- Mounting entire `/usr/lib/x86_64-linux-gnu` caused cluster creation to fail (library conflicts)
- GPU devices were visible but unusable without libraries
- This is a **known limitation** of kind for GPU workloads

### Decision
Switched to **microk8s** which has native GPU support.

---

## Phase 3: microk8s Deployment (Success)

### Step 1: Install microk8s

```bash
sudo snap install microk8s --classic
sudo usermod -a -G microk8s $USER
sudo microk8s status --wait-ready
```

**Result**: microk8s v1.32.9 installed

---

### Step 2: Enable Required Addons

```bash
sudo microk8s enable dns storage
sudo microk8s enable gpu
```

**What Happened**:
- DNS: CoreDNS for service discovery
- Storage: hostpath-storage for persistent volumes
- GPU: Deployed **NVIDIA GPU Operator** automatically
  - Installed device plugin, container toolkit, CUDA validator
  - Detected: NVIDIA GeForce RTX 3050 Laptop GPU
  - Compute capability: 8.6
  - Driver version: 580.95.05

---

### Step 3: Build and Import Docker Image

```bash
# Build image
sudo docker build -t oomersheriff12/ytsummarizer:latest -f backend/Dockerfile backend/

# Export to tar
sudo docker save oomersheriff12/ytsummarizer:latest > /tmp/ytsummarizer.tar

# Import to microk8s
sudo microk8s ctr image import /tmp/ytsummarizer.tar
```

**Result**: 11.2 GB image loaded into microk8s containerd

---

### Step 4: Deploy Infrastructure

```bash
sudo microk8s kubectl apply -f k8s/configmap.yaml -f k8s/secret.yaml -f k8s/redis.yaml -f k8s/rabbitmq.yaml
```

**Deployed**:
- ConfigMap: Environment configuration
- Secret: RabbitMQ credentials
- Redis: Result backend
- RabbitMQ: Message broker

---

### Step 5: Deploy Application Services

```bash
sudo microk8s kubectl apply -f k8s/backend.yaml -f k8s/mcp-server.yaml
```

**Deployed**:
- Backend API (FastAPI on port 8001)
- MCP Server (port 8000)

---

### Step 6: Deploy Workers (Initial Attempt)

```bash
sudo microk8s kubectl apply -f k8s/worker-chat.yaml -f k8s/worker-transcript.yaml
```

**Problem**: Both workers requested 1 GPU each, but only 1 GPU available
- `worker-chat`: Pending (Insufficient nvidia.com/gpu)
- `worker-transcript`: Pending (Insufficient nvidia.com/gpu)

---

### Step 7: Fix GPU Allocation

**Decision**: Run transcript worker on CPU, give GPU to chat worker

Modified `k8s/worker-transcript.yaml`:
```diff
- resources:
-   limits:
-     nvidia.com/gpu: 1
```

**Applied Changes**:
```bash
sudo microk8s kubectl apply -f k8s/worker-transcript.yaml
```

---

### Step 8: Wait for GPU Operator Initialization

Initially, GPU showed:
- Capacity: 1
- Allocatable: 0

After ~2-3 minutes, GPU operator completed initialization:
- Capacity: 1
- Allocatable: 1

**Final Status**: All pods running ✅

---

## Final Deployment Status

### Running Pods

```
NAME                      STATUS    GPU
backend                   Running   -
mcp-server                Running   -
redis                     Running   -
rabbitmq                  Running   -
worker-chat               Running   ✅ GPU
worker-transcript         Running   CPU
```

### Services

- **Backend API**: http://localhost:30001 (NodePort)
- **MCP Server**: http://10.152.183.114:8000 (ClusterIP)
- **RabbitMQ**: Management UI on port 30072
- **Redis**: 10.152.183.34:6379

### Worker Status

**worker-chat** (GPU):
- Connected to RabbitMQ ✅
- Listening on `chat_queue`
- GPU allocated
- Ready to process chat requests

**worker-transcript** (CPU):
- Connected to RabbitMQ ✅
- Listening on `transcript_queue`
- Synced with worker-chat
- Ready to process transcription tasks

---

## Key Learnings

1. **Snap Docker doesn't support GPUs** - Use official Docker CE instead
2. **kind has GPU limitations** - Use microk8s/k3s/kubeadm for GPU workloads
3. **GPU operator needs initialization time** - Wait 2-3 minutes after enabling
4. **Single GPU = Choose wisely** - Allocate to most compute-intensive worker
5. **microk8s commands** - Always prefix with `sudo microk8s kubectl`

---

## Next Steps

To use the deployment:
1. Test backend API: `curl http://localhost:30001/docs`
2. Monitor workers: `sudo microk8s kubectl logs -f -l app=worker-chat`
3. Check GPU usage: `nvidia-smi`
4. View all pods: `sudo microk8s kubectl get pods`

To stop the deployment:
```bash
sudo microk8s kubectl delete -f k8s/
```

To completely remove microk8s:
```bash
sudo microk8s reset
sudo snap remove microk8s
```
