# Module 3 – Kubernetes: Deploy to EKS

## Overview
Deploys the three-tier application (MySQL, Python App, Nginx) to the EKS cluster created in Module 2. Uses the **Secrets Store CSI Driver** for secret injection, **EFS** for persistent MySQL storage, and **KEDA** for custom autoscaling.

## Architecture

```
Internet → NLB → Nginx (nginx ns, 2 replicas)
                    ↓  auth_request /validate_token
           Application (application ns)
                    ↓
              MySQL (mysql ns) → EFS volume
```

## Namespace Layout

| Namespace | Workloads |
|-----------|-----------|
| `mysql` | MySQL Deployment, Service, EFS PVC |
| `application` | Python Flask App Deployment, Service |
| `nginx` | Nginx Deployment, Service (NLB) |
| `prometheus` | Prometheus scrape target for KEDA metrics |

## Secret Management (Secrets Store CSI Driver)

Secrets are **never stored in Kubernetes Secrets directly**. They are injected at runtime from:

- **AWS Secrets Manager** → App token (`task1-dev-us-east-1-daniel-katsenyuk-generated-token`)
- **AWS SSM Parameter Store** → MySQL credentials (`/dev/myapp/mysql/*`)

The CSI driver creates a Kubernetes Secret (`app-secret` / `mysql-secret`) as a side-effect of mounting.

## MySQL Persistence (EFS)

```yaml
# StorageClass uses EFS CSI provisioner
provisioner: efs.csi.aws.com
fileSystemId: fs-0b9ebcb800eec5bc9
```

The EFS filesystem ID must exist before applying. The PVC uses `ReadWriteMany` access mode, allowing future migration to StatefulSet.

## KEDA Auto-scaling (Bonus Task)

- **Metric source**: Prometheus `app_requests_total` gauge
- **Threshold**: `10` (scale up 1 replica per 10 requests, rounded up)
- **Min replicas**: 1 | **Max replicas**: 10

## Deployment Order

```bash
# 1. Create namespaces
kubectl create ns mysql application nginx prometheus

# 2. Deploy CSI secret providers
kubectl apply -f k8s-manifests/mysql-secret-provider.yaml
kubectl apply -f k8s-manifests/app-secret-provider.yaml

# 3. Deploy storage
kubectl apply -f k8s-manifests/mysql-efs.yaml

# 4. Deploy workloads
kubectl apply -f k8s-manifests/mysql-deployment.yaml
kubectl apply -f k8s-manifests/app-deployment.yaml
kubectl apply -f k8s-manifests/nginx-config.yaml
kubectl apply -f k8s-manifests/nginx-deployment.yaml

# 5. Deploy Prometheus + KEDA scaler
kubectl apply -f k8s-manifests/prometheus.yaml
kubectl apply -f k8s-manifests/keda-scaler.yaml
```

## Verification

```bash
# Check all pods are Running
kubectl get pods -A

# Get the NLB hostname
kubectl get svc nginx-service -n nginx

# Test the app via NLB
curl http://<nlb-hostname>/token
curl -H "Authorization: <token>" http://<nlb-hostname>/track
curl -H "Authorization: <token>" http://<nlb-hostname>/count
```

## Security Notes
- All containers run as non-root (`runAsNonRoot: true`, `allowPrivilegeEscalation: false`)
- Resource `requests` and `limits` are defined on all containers
- `readinessProbe` and `livenessProbe` are configured on all containers
