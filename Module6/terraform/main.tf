resource "kubernetes_namespace" "argocd" {
  metadata {
    name = "argocd"
  }
}

resource "helm_release" "argocd" {
  name       = "my-argo"
  repository = "https://argoproj.github.io/argo-helm"
  chart      = "argo-cd"
  namespace  = kubernetes_namespace.argocd.metadata[0].name

  # Using set blocks to configure ArgoCD parameters
  set {
    name  = "server.extraArgs"
    value = "{--insecure}"
  }

  set {
    name  = "server.service.type"
    value = "ClusterIP"
  }
  
  # Ensure the namespace exists first
  depends_on = [kubernetes_namespace.argocd]
}

resource "kubernetes_ingress_v1" "argocd_ingress" {
  metadata {
    name      = "argocd-server-ingress"
    namespace = kubernetes_namespace.argocd.metadata[0].name
    annotations = {
      "nginx.ingress.kubernetes.io/backend-protocol" = "HTTP"
    }
  }

  spec {
    ingress_class_name = "nginx"
    rule {
      host = "argocd.dkats-bootcamp.com"
      http {
        path {
          path      = "/"
          path_type = "Prefix"
          backend {
            service {
              name = "my-argo-argocd-server"
              port {
                number = 80
              }
            }
          }
        }
      }
    }
  }
}

# Output the ArgoCD server URL (based on your Route53 domain)
output "argocd_url" {
  value = "https://argocd.dkats-bootcamp.com"
}
