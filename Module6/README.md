# Module 6 – CI/CD: ArgoCD, GitOps & GitHub Actions

## Overview
Implements a full GitOps pipeline using **ArgoCD** (App-of-Apps + ApplicationSet) and **GitHub Actions** (OIDC-based workflows). All infrastructure tools are managed declaratively.

## Architecture

```
GitHub Repo (source of truth)
      │
      │  push / workflow_dispatch
      ▼
GitHub Actions (OIDC → AWS Role)
      │
      ├── terraform-plan.yaml    → terraform plan for any module
      ├── build-push-semver.yaml → build + tag ECR image + update Helm values
      └── deploy.yaml            → build + push on python-app changes
            │
            ▼
       ArgoCD (sync loop)
            │
            ├── root-app.yaml           → App-of-Apps (points to gitops/)
            │       └── argo-gitops.yaml → ApplicationSets
            │               ├── bootcamp-applications  → all Helm charts in Module5/helm-charts/*
            │               └── bootcamp-operators     → ingress-nginx
            │
            └── infrastructure-tools/apps.yaml (applied manually once)
                    ├── keda
                    ├── secrets-csi
                    ├── prometheus
                    ├── ingress-nginx
                    └── argo-workflows
```

---

## Task 1 & 2: ArgoCD Deployment

### Helm (Task 1)
ArgoCD is deployed via `helm_release` in `terraform/` with:
- GitHub OAuth via Dex (`clientID` / `clientSecret` from Terraform variables)
- RBAC: `danielkatsenyuk` gets `role:admin`
- Ingress on `argocd.dkats-bootcamp.com`

```bash
cd Module6/terraform
# Pass the secret via environment variable – NEVER hardcode it
export TF_VAR_argocd_github_client_secret="<your-oauth-secret>"
terraform init && terraform apply
```

### Terraform (Task 2)
The same `terraform/` directory handles:
- GitHub OIDC provider (`aws_iam_openid_connect_provider.github`)
- IAM Role for GitHub Actions with `AdministratorAccess`
- EKS access entry for the GitHub Actions role

---

## Task 3: ArgoCD Application Structure

### App-of-Apps
`root-app.yaml` is the single bootstrap object. Apply it once:
```bash
kubectl apply -f Module6/root-app.yaml
```
It points ArgoCD at `Module6/gitops/` which contains the ApplicationSets.

### ApplicationSet vs Application
| | Application | ApplicationSet |
|--|--|--|
| Scope | Single app | Generates N Applications |
| Use case | One-off deployment | Templated multi-app deployments |
| Example here | `root-app.yaml` | `argo-gitops.yaml` |

**`bootcamp-applications`** – Git directory generator: auto-creates an ArgoCD Application for every folder inside `Module5/helm-charts/`

**`bootcamp-operators`** – List generator: deploys Helm-based operators (ingress-nginx) from public chart repos

---

## Task 4: GitHub Actions Workflows

All workflows use **OIDC** (no static AWS keys stored in GitHub).

| Workflow | Trigger | What it does |
|----------|---------|-------------|
| `terraform-plan.yaml` | `workflow_dispatch` | Assumes IAM role, runs `terraform plan` for the selected module |
| `build-push-semver.yaml` | `workflow_dispatch` | Bumps semver tag, builds & pushes ECR image, updates `values.yaml` |
| `deploy.yaml` | push to `Module1/python-app/**` or `workflow_dispatch` | Builds & pushes ECR image, updates `values.yaml` with commit SHA |
| `deploy-infra.yaml` | `workflow_dispatch` | Applies `infrastructure-tools/apps.yaml` to the cluster |

### Required GitHub Secrets / Variables
| Secret | Description |
|--------|-------------|
| _(none)_ | All auth uses OIDC – no static keys needed |

### Required GitHub Actions Permissions
```yaml
permissions:
  id-token: write   # OIDC token
  contents: write   # commit Helm values update
```

---

## Infrastructure Tools (`infrastructure-tools/apps.yaml`)

Applied once with `kubectl apply` or via the `deploy-infra.yaml` workflow:

| Tool | Chart | Version | Namespace |
|------|-------|---------|-----------|
| KEDA | `keda/keda` | 2.15.0 | `keda` |
| Secrets Store CSI | `secrets-store-csi-driver` | 1.4.4 | `kube-system` |
| Prometheus Stack | `kube-prometheus-stack` | 67.x | `monitoring` |
| Ingress-NGINX | `ingress-nginx` | 4.11.x | `nginx` |
| Argo Workflows | `argo-workflows` | 0.33.0 | `argo-workflows` |

---

## Security Notes
- `clientSecret` for GitHub OAuth is **never** stored in source code – it is injected via `TF_VAR_argocd_github_client_secret`
- GitHub Actions uses OIDC federation with AWS — no long-lived credentials
- ArgoCD runs with `--insecure` because TLS terminates at ingress-nginx (safe pattern)
