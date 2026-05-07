output "distribution_arn" {
  description = "CloudFront distribution ARN."
  value       = aws_cloudfront_distribution.api.arn
}

output "distribution_id" {
  description = "CloudFront distribution ID."
  value       = aws_cloudfront_distribution.api.id
}

output "distribution_domain_name" {
  description = "CloudFront distribution domain name."
  value       = aws_cloudfront_distribution.api.domain_name
}

output "distribution_hosted_zone_id" {
  description = "CloudFront distribution hosted zone ID."
  value       = aws_cloudfront_distribution.api.hosted_zone_id
}

output "waf_web_acl_arn" {
  description = "CloudFront WAF WebACL ARN."
  value       = aws_wafv2_web_acl.api.arn
}
