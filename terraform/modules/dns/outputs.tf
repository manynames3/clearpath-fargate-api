output "certificate_arn" {
  description = "ACM certificate ARN. Uses validation ARN when Route53 validation records are enabled."
  value       = try(aws_acm_certificate_validation.api[0].certificate_arn, try(aws_acm_certificate.api[0].arn, ""))
}

output "api_record_fqdn" {
  description = "FQDN of the API alias record, when created."
  value       = try(aws_route53_record.api[0].fqdn, "")
}

output "origin_record_fqdn" {
  description = "FQDN of the ALB origin alias record, when created."
  value       = try(aws_route53_record.origin[0].fqdn, "")
}
