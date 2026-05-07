variable "project" {
  description = "Project tag value applied to all resources."
  type        = string
}

variable "env" {
  description = "Deployment environment name."
  type        = string
}

variable "api_domain_name" {
  description = "Public API domain name served by CloudFront."
  type        = string
}

variable "origin_domain_name" {
  description = "Origin domain name pointing to the ALB."
  type        = string
}

variable "acm_cert_arn" {
  description = "ACM certificate ARN in us-east-1 for the CloudFront alias."
  type        = string
}
