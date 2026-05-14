# Module 2 – Terraform: AWS Infrastructure

## Overview
Provisions a complete AWS environment for the bootcamp using Terraform. All resources follow a consistent naming convention and are tagged for cost allocation and ownership tracking.

## Naming Convention
All resources use the pattern: `<prefix>-<environment>-<region>-<creator-name>-<resource-type>`

**Example:** `task1-dev-us-east-1-daniel-katsenyuk-cluster`

## Resources Created

### Networking
| Resource | Description |
|----------|-------------|
| VPC | 10.0.0.0/16 CIDR with DNS hostnames enabled |
| Public Subnets (x2) | Spread across 2 AZs, `map_public_ip_on_launch = true` |
| Private Subnets (x2) | Spread across 2 AZs (EKS nodes run here) |
| Internet Gateway | Outbound internet for public subnets |
| NAT Gateway + EIP | Outbound internet for private subnets |
| Route Tables | Separate public and private route tables |

### EKS Cluster
| Resource | Description |
|----------|-------------|
| EKS Cluster | Control plane with OIDC provider |
| Managed Node Group | SPOT instances: `t3.medium`, `t3a.medium`, `t2.medium` |
| IAM Cluster Role | `AmazonEKSClusterPolicy` |
| IAM Node Role | Worker node policies + ECR read access |

### Security & Storage
| Resource | Description |
|----------|-------------|
| Secrets Manager Secret | Stores the generated application token |
| SSM Parameter | `/dev/config/app_mode = production` |
| ECR Repositories | `mysql`, `application`, `nginx` (tagged with semver `1.0.x`) |
| OIDC Provider | For IRSA (IAM Roles for Service Accounts) |
| IAM App Roles (x3) | One per app, scoped to trust Kubernetes service accounts |
| IAM App Policy | Least-privilege access to the specific secret + SSM prefix |
| EFS CSI Driver Role | IAM role for the EFS CSI driver |

## Required Tags (applied via `default_tags` in provider)

```hcl
Terraform   = "True"
Environment = "<environment>"
CreatedBy   = "<your-name>"
```

## Usage

```bash
cd Module2
terraform init
terraform plan
terraform apply
```

### Connect to the cluster after apply

```bash
aws eks --region us-east-1 update-kubeconfig --name task1-dev-us-east-1-daniel-katsenyuk-cluster
kubectl get all -A
```

## Security Notes
- The IAM policy for app roles is scoped to specific secret ARNs (not wildcard `*`)
- OIDC trust policy uses `StringLike` to allow any service account – tighten per-app in production
- Terraform state is stored locally (not committed). Use S3 backend + DynamoDB locking for production.
