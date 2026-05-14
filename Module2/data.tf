# Data Source: 
data "aws_availability_zones" "available" {
  state = "available"
}

# --- IAM Trust Policies (Data Sources) ---

# creates the trust policy for the EKS cluster
data "aws_iam_policy_document" "eks_cluster_assume_role" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["eks.amazonaws.com"]
    }
  }
}

# creates the trust policy for the EKS worker nodes
data "aws_iam_policy_document" "eks_nodes_assume_role" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ec2.amazonaws.com"]
    }
  }
}

# policy that allows reading and writing only to the specific secret we created (and SSM parameters)
data "aws_iam_policy_document" "app_secret_access" {
  statement {
    sid = "AllowSpecificSecretAccess"
    actions = [
      "secretsmanager:GetSecretValue",
      "secretsmanager:PutSecretValue",
      "secretsmanager:DescribeSecret"
    ]
    resources = [aws_secretsmanager_secret.app_token.arn]
  }

  statement {
    sid = "AllowSSMParameterAccess"
    actions = [
      "ssm:GetParameter",
      "ssm:GetParameters",
      "ssm:GetParametersByPath"
    ]
    # Scope to parameters under /dev/myapp/ prefix
    resources = ["arn:aws:ssm:${var.aws_region}:*:parameter/${var.environment}/myapp/*",
                 "arn:aws:ssm:${var.aws_region}:*:parameter/${var.environment}/config/*"]
  }
}


# Trust Policy that allows Kubernetes to take this role (Service Accounts)
data "aws_iam_policy_document" "app_assume_role" {
  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]
    effect  = "Allow"

    condition {
      test     = "StringLike" # חשוב מאוד: StringLike כדי שהכוכבית תעבוד
      variable = "${replace(aws_iam_openid_connect_provider.eks.url, "https://", "")}:sub"
      values   = ["system:serviceaccount:*:*"]
    }

    principals {
      identifiers = [aws_iam_openid_connect_provider.eks.arn]
      type        = "Federated"
    }
  }
}

data "aws_partition" "current" {}

data "tls_certificate" "eks" {
  url = aws_eks_cluster.main.identity[0].oidc[0].issuer
}
