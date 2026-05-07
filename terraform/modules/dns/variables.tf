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
  description = "Origin domain name that points to the ALB and matches the ALB certificate."
  type        = string
}

variable "route53_zone_id" {
  description = "Route53 hosted zone ID. Empty string skips DNS records for local-only validation."
  type        = string
  default     = ""
}

variable "create_certificate" {
  description = "Whether this module instance creates the ACM certificate."
  type        = bool
  default     = true
}

variable "create_api_record" {
  description = "Whether this module instance creates the API alias record."
  type        = bool
  default     = false
}

variable "create_origin_record" {
  description = "Whether this module instance creates the ALB origin alias record."
  type        = bool
  default     = false
}

variable "cloudfront_domain_name" {
  description = "CloudFront distribution domain name for the API alias."
  type        = string
  default     = ""
}

variable "cloudfront_hosted_zone_id" {
  description = "CloudFront distribution hosted zone ID for the API alias."
  type        = string
  default     = ""
}

variable "alb_dns_name" {
  description = "ALB DNS name for the origin alias."
  type        = string
  default     = ""
}

variable "alb_zone_id" {
  description = "ALB hosted zone ID for the origin alias."
  type        = string
  default     = ""
}
