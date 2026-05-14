variable "argocd_github_client_id" {
  description = "GitHub OAuth App Client ID for ArgoCD Dex authentication"
  type        = string
  default     = "Ov23liI4cVXHRptCnPCD"
}

variable "argocd_github_client_secret" {
  description = "GitHub OAuth App Client Secret for ArgoCD Dex. Pass via TF_VAR_argocd_github_client_secret env var or GitHub Actions Secret."
  type        = string
  sensitive   = true
}

variable "eks_cluster_name" {
  description = "Name of the existing EKS cluster (created in Module2)"
  type        = string
  default     = "task1-dev-us-east-1-daniel-katsenyuk-cluster"
}

variable "argocd_domain" {
  description = "Domain for ArgoCD ingress"
  type        = string
  default     = "argocd.dkats-bootcamp.com"
}
