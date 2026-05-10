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

variable "origin_header_name" {
  description = "Optional custom header name CloudFront sends to the ALB origin."
  type        = string
  default     = "X-Clearpath-Origin-Token"
}

variable "origin_header_value" {
  description = "Optional custom header value CloudFront sends to the ALB origin. Set out-of-band for deployment; do not commit real values."
  type        = string
  default     = null
  sensitive   = true
  nullable    = true
}
