locals {
  clean_creator_name = replace(lower(var.created_by), " ", "-")
  name_prefix        = "${var.prefix}-${var.environment}-${var.aws_region}-${local.clean_creator_name}"

  apps = ["mysql", "application", "nginx"]
}

# vpc creation
resource "aws_vpc" "main" {
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name = "${local.name_prefix}-vpc"
  }
}

# igw creation
resource "aws_internet_gateway" "igw" {
  vpc_id = aws_vpc.main.id

  tags = {
    Name = "${local.name_prefix}-igw"
  }
}

# public subnets creation
resource "aws_subnet" "public" {
  count  = 2
  vpc_id = aws_vpc.main.id

  cidr_block = cidrsubnet(var.vpc_cidr, 8, count.index)

  availability_zone = data.aws_availability_zones.available.names[count.index]

  map_public_ip_on_launch = true

  tags = {
    Name = "${local.name_prefix}-public-subnet-${count.index + 1}"
  }
}

# private subnets creation
resource "aws_subnet" "private" {
  count             = 2
  vpc_id            = aws_vpc.main.id
  cidr_block        = cidrsubnet(var.vpc_cidr, 8, count.index + 2)
  availability_zone = data.aws_availability_zones.available.names[count.index]

  tags = {
    Name = "${local.name_prefix}-private-subnet-${count.index + 1}"
  }
}

#elastic ip creation
resource "aws_eip" "nat" {
  domain = "vpc"

  tags = {
    Name = "${local.name_prefix}-nat-eip"
  }
}

#nat gateway creation
resource "aws_nat_gateway" "nat" {
  allocation_id = aws_eip.nat.id

  subnet_id = aws_subnet.public[0].id

  tags = {
    Name = "${local.name_prefix}-nat"
  }

  depends_on = [aws_internet_gateway.igw]
}

#route table public
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.igw.id
  }

  tags = {
    Name = "${local.name_prefix}-public-rt"
  }
}

#route table association public
resource "aws_route_table_association" "public" {
  count          = 2
  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

#route table private
resource "aws_route_table" "private" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.nat.id
  }

  tags = {
    Name = "${local.name_prefix}-private-rt"
  }
}

#route table association private
resource "aws_route_table_association" "private" {
  count          = 2
  subnet_id      = aws_subnet.private[count.index].id
  route_table_id = aws_route_table.private.id
}

# ==========================================
# 11. EKS IAM Role for Control Plane
# ==========================================
resource "aws_iam_role" "eks_cluster" {
  name = "${local.name_prefix}-eks-cluster-role"

  assume_role_policy = data.aws_iam_policy_document.eks_cluster_assume_role.json
}

# attaching the required policy for the EKS cluster
resource "aws_iam_role_policy_attachment" "eks_cluster_policy" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSClusterPolicy"
  role       = aws_iam_role.eks_cluster.name
}

# ==========================================
# 12. IAM Role for Worker Nodes
# ==========================================
resource "aws_iam_role" "eks_nodes" {
  name = "${local.name_prefix}-eks-node-role"

  assume_role_policy = data.aws_iam_policy_document.eks_nodes_assume_role.json
}

# attaching the required policies for the EKS worker nodes
resource "aws_iam_role_policy_attachment" "eks_worker_node_policy" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy"
  role       = aws_iam_role.eks_nodes.name
}

resource "aws_iam_role_policy_attachment" "eks_cni_policy" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy"
  role       = aws_iam_role.eks_nodes.name
}

resource "aws_iam_role_policy_attachment" "ecr_read_only" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"
  role       = aws_iam_role.eks_nodes.name
}

# ==========================================
# 13. EKS Cluster creation
# ==========================================
resource "aws_eks_cluster" "main" {
  name     = "${local.name_prefix}-cluster"
  role_arn = aws_iam_role.eks_cluster.arn

  vpc_config {
    # we give it all the IDs of the subnets we created (public and private)
    subnet_ids = concat(aws_subnet.public[*].id, aws_subnet.private[*].id)
  }

  access_config {
    authentication_mode                         = "API_AND_CONFIG_MAP"
    bootstrap_cluster_creator_admin_permissions = true
  }

  # ensures that the IAM policies are created before the cluster tries to use them
  depends_on = [
    aws_iam_role_policy_attachment.eks_cluster_policy
  ]
}

# ==========================================
# 14. EKS Managed Node Group creation
# ==========================================
resource "aws_eks_node_group" "main" {
  cluster_name    = aws_eks_cluster.main.name
  node_group_name = "${local.name_prefix}-node-group"
  node_role_arn   = aws_iam_role.eks_nodes.arn

  subnet_ids = aws_subnet.private[*].id

  capacity_type  = "SPOT"
  instance_types = ["t3.medium", "t3a.medium", "t2.medium"]

  scaling_config {
    desired_size = 3
    max_size     = 4
    min_size     = 1
  }

  # using depends_on to prevent permission errors during creation
  depends_on = [
    aws_iam_role_policy_attachment.eks_worker_node_policy,
    aws_iam_role_policy_attachment.eks_cni_policy,
    aws_iam_role_policy_attachment.ecr_read_only,
  ]
}
# 15. creating Secret in AWS Secrets Manager (for the token)
resource "aws_secretsmanager_secret" "app_token" {
  name        = "${local.name_prefix}-generated-token"
  description = "Secure token for the application"

  tags = {
    Name = "${local.name_prefix}-secret"
  }
}

# 16. creating parameter in AWS Systems Manager (SSM) Parameter Store
resource "aws_ssm_parameter" "app_config" {
  name  = "/${var.environment}/config/app_mode"
  type  = "String"
  value = "production"

  tags = {
    Name = "${local.name_prefix}-ssm-param"
  }
}

# ==========================================
# 17. creating ECR repositories for applications 
# ==========================================
resource "aws_ecr_repository" "repos" {
  for_each             = toset(local.apps) # loop that runs 3 times
  name                 = "${local.name_prefix}-${each.key}-repo"
  image_tag_mutability = "MUTABLE"
  force_delete         = true
  tags = {
    Name = "${local.name_prefix}-${each.key}-repo"
  }
}

# ==========================================
# 18. creating IAM Roles for applications 
# ==========================================

# creating the policy itself in AWS 
resource "aws_iam_policy" "secret_policy" {
  name   = "${local.name_prefix}-app-secret-policy"
  policy = data.aws_iam_policy_document.app_secret_access.json
}

# creating 3 roles, one for each application
resource "aws_iam_role" "app_roles" {
  for_each           = toset(local.apps)
  name               = "${local.name_prefix}-${each.key}-role"
  assume_role_policy = data.aws_iam_policy_document.app_assume_role.json
}

# attaching the policy we created to each of the 3 roles
resource "aws_iam_role_policy_attachment" "app_roles_secret_attach" {
  for_each   = toset(local.apps)
  role       = aws_iam_role.app_roles[each.key].name
  policy_arn = aws_iam_policy.secret_policy.arn
}

# ==========================================
# 19. Attach EFS CSI Driver Policy to Worker Nodes
# ==========================================
resource "aws_iam_role_policy_attachment" "eks_nodes_efs_policy" {
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonEFSCSIDriverPolicy"
  role       = aws_iam_role.eks_nodes.name
}

resource "aws_iam_openid_connect_provider" "eks" {
  client_id_list  = ["sts.amazonaws.com"]
  thumbprint_list = [data.tls_certificate.eks.certificates[0].sha1_fingerprint]
  url             = aws_eks_cluster.main.identity[0].oidc[0].issuer
}

resource "aws_iam_role" "efs_csi_driver" {
  name               = "${local.name_prefix}-efs-csi-driver-role"
  assume_role_policy = data.aws_iam_policy_document.app_assume_role.json
}

resource "aws_iam_role_policy_attachment" "efs_csi_driver_attach" {
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonEFSCSIDriverPolicy"
  role       = aws_iam_role.efs_csi_driver.name
}

output "efs_csi_role_arn" {
  value = aws_iam_role.efs_csi_driver.arn
}
