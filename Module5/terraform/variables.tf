variable "aws_region" {
  description = "The AWS region to deploy resources in"
  type        = string
  default     = "us-east-1"
}

variable "domain_name" {
  description = "The root domain name"
  type        = string
  default     = "dkats-bootcamp.com"
}
