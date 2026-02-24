#!/usr/bin/env bash
# minikube-deploy.sh — Full local Kubernetes deployment for demo
# Usage: bash k8s/minikube-deploy.sh
# Run from project root

set -e

echo "=========================================="
echo "  CloudSync Pro FTE — Minikube Deploy"
echo "=========================================="

# 1. Start minikube
echo ""
echo "[1/6] Starting minikube..."
minikube start --driver=docker --memory=4096 --cpus=2 2>/dev/null || \
  minikube start --memory=4096 --cpus=2

# Enable addons
echo "      Enabling ingress addon..."
minikube addons enable ingress 2>/dev/null || true
minikube addons enable metrics-server 2>/dev/null || true

# 2. Point Docker to minikube's daemon
echo ""
echo "[2/6] Configuring Docker to use minikube's registry..."
eval $(minikube docker-env)

# 3. Build Docker image inside minikube
echo ""
echo "[3/6] Building Docker image: customer-success-fte:latest"
docker build -t customer-success-fte:latest .
echo "      Image built successfully!"

# 4. Create namespace & secrets
echo ""
echo "[4/6] Creating namespace and secrets..."
bash k8s/create-secrets.sh

# 5. Apply all manifests
echo ""
echo "[5/6] Applying Kubernetes manifests..."
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/deployment-api.yaml
kubectl apply -f k8s/deployment-worker.yaml
kubectl apply -f k8s/service.yaml
kubectl apply -f k8s/hpa.yaml
# Skip ingress for local (uses NodePort instead)

echo "      Waiting for pods to be ready (up to 120s)..."
kubectl rollout status deployment/fte-api -n customer-success-fte --timeout=120s || true
kubectl rollout status deployment/fte-message-processor -n customer-success-fte --timeout=120s || true

# 6. Show access URL
echo ""
echo "[6/6] Getting service URL..."
MINIKUBE_IP=$(minikube ip)
NODE_PORT=$(kubectl get svc fte-api-service -n customer-success-fte -o jsonpath='{.spec.ports[0].nodePort}' 2>/dev/null || echo "")

echo ""
echo "=========================================="
echo "  DEPLOYMENT COMPLETE!"
echo "=========================================="
echo ""
echo "  Minikube IP: $MINIKUBE_IP"
echo ""
echo "  To access the API:"
echo "  kubectl port-forward svc/fte-api-service 8080:80 -n customer-success-fte &"
echo "  curl http://localhost:8080/health"
echo ""
echo "  Quick health check:"
kubectl get pods -n customer-success-fte
echo ""
echo "  View logs:"
echo "  kubectl logs -f deployment/fte-api -n customer-success-fte"
echo "=========================================="
