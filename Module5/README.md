# Module 5 – Helm: Charts, DNS & Ingress

## Overview
Packages the three application workloads as Helm charts, registers a domain in Route53, issues a TLS certificate via ACM, and deploys the NGINX Ingress Controller.

## Helm Charts

| Chart | Namespace | Description |
|-------|-----------|-------------|
| `helm-charts/application` | `application` | Python Flask app + CSI secret injection |
| `helm-charts/mysql` | `mysql` | MySQL with EFS PVC + CSI secrets |
| `helm-charts/nginx` | `nginx` | Nginx reverse proxy with ConfigMap config |

Each chart has:
- `Chart.yaml` – chart metadata
- `values.yaml` – all configurable values (image, replicas, service port, CSI config, storage)
- `templates/` – Deployment, Service, ServiceAccount, SecretProviderClass (and PVC/StorageClass for MySQL)

### Deploying Charts

```bash
# Install / upgrade each chart
helm upgrade --install application ./Module5/helm-charts/application -n application --create-namespace
helm upgrade --install mysql      ./Module5/helm-charts/mysql       -n mysql       --create-namespace
helm upgrade --install nginx      ./Module5/helm-charts/nginx        -n nginx       --create-namespace
```

---

## Infrastructure Terraform (Route53, ACM, DNS Records)

Located in `terraform/`.

### Resources Created

| Resource | Description |
|----------|-------------|
| `aws_route53domains_domain` | Registers `dkats-bootcamp.com` |
| `aws_acm_certificate` | Wildcard TLS cert `*.dkats-bootcamp.com` with DNS validation |
| `aws_route53_record` (cert) | DNS validation CNAME records |
| `aws_route53_record` (app) | `app.dkats-bootcamp.com` → NLB hostname |
| `aws_route53_record` (argocd) | `argocd.dkats-bootcamp.com` → NLB hostname |

```bash
cd Module5/terraform
terraform init
terraform apply
```

> ⚠️ Domain registration can take up to 15 minutes. The ACM certificate validation waiter will block until DNS propagates.

---

## Ingress-NGINX Controller

Deployed via Helm using a custom values file (`helm-charts/ingress-nginx-values.yaml`).

```bash
helm upgrade --install ingress-nginx ingress-nginx \
  --repo https://kubernetes.github.io/ingress-nginx \
  --namespace nginx \
  --create-namespace \
  -f helm-charts/ingress-nginx-values.yaml
```

### Ingress Routes

| Host | Backend |
|------|---------|
| `app.dkats-bootcamp.com` | `application-service:5000` |
| `argocd.dkats-bootcamp.com` | `my-argo-argocd-server:80` |

---

## Semver Image Tagging

ECR images follow semantic versioning `MAJOR.MINOR.PATCH`:

```
1.0.0  → Initial release
1.0.1  → Bug fix
1.1.0  → New feature
2.0.0  → Breaking change
```

The `build-push-semver.yaml` GitHub Actions workflow bumps the version automatically.
