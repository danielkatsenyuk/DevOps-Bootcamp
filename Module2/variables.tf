variable "aws_region" {
  description = "The AWS region to deploy to"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name (e.g., dev, prod)"
  type        = string
  default     = "dev"
}

variable "prefix" {
  description = "Prefix for all resources"
  type        = string
  default     = "task1"
}

variable "created_by" {
  description = "name for tagging resources"
  type        = string
  default     = "Daniel Katsenyuk"
}

variable "vpc_cidr" {
  description = "The CIDR block for the VPC"
  type        = string
  default     = "10.0.0.0/16"
}
