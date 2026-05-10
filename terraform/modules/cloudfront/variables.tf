variable "project" {
  description = "Project tag value applied to all resources."
  type        = string
}

variable "env" {
  description = "Deployment environment name."
  type        = string
}

variable "api_domain_name" {
  description = "Optional public API domain name served by CloudFront when use_custom_domain is true."
  type        = string
}

variable "origin_domain_name" {
  description = "ALB origin domain name. Defaults to the ALB generated DNS name in no-domain mode."
  type        = string
}

variable "origin_protocol" {
  description = "Protocol CloudFront uses to reach the ALB origin."
  type        = string
  default     = "http-only"

  validation {
    condition     = contains(["http-only", "https-only"], var.origin_protocol)
    error_message = "origin_protocol must be either http-only or https-only."
  }
}

variable "use_custom_domain" {
  description = "Whether CloudFront should attach api_domain_name as an alias and use the supplied ACM certificate."
  type        = bool
  default     = false
}

variable "acm_cert_arn" {
  description = "ACM certificate ARN in us-east-1 for the CloudFront alias when use_custom_domain is true."
  type        = string
  default     = ""
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
