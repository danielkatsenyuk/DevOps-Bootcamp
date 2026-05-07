# registering the domain in Route53
# NOTE: To register a real domain, AWS requires contact information. 
# You will need to replace the placeholder values below with your real information.
resource "aws_route53domains_domain" "bootcamp_domain" {
  domain_name = var.domain_name

  admin_contact {
    first_name     = "Daniel"
    last_name      = "Katsenyuk"
    contact_type   = "PERSON"
    email          = "daniel.katsenyuk@midlink.co.il"
    phone_number   = "+972.543251585"
    address_line_1 = "Hamapilim 11"
    city           = "Ashdod"
    zip_code       = "7732506"
    country_code   = "IL"
  }

  registrant_contact {
    first_name     = "Daniel"
    last_name      = "Katsenyuk"
    contact_type   = "PERSON"
    email          = "daniel.katsenyuk@midlink.co.il"
    phone_number   = "+972.543251585"
    address_line_1 = "Hamapilim 11"
    city           = "Ashdod"
    zip_code       = "7732506"
    country_code   = "IL"
  }

  tech_contact {
    first_name     = "Daniel"
    last_name      = "Katsenyuk"
    contact_type   = "PERSON"
    email          = "daniel.katsenyuk@midlink.co.il"
    phone_number   = "+972.543251585"
    address_line_1 = "Hamapilim 11"
    city           = "Ashdod"
    zip_code       = "7732506"
    country_code   = "IL"
  }

  tags = {
    Environment = "dev"
    Bootcamp    = "true"
  }
}

# The hosted zone is automatically created by the domain registration.
# We fetch its details using a data block so we can use its ID for the ACM validation records.
data "aws_route53_zone" "bootcamp_zone" {
  name       = var.domain_name
  depends_on = [aws_route53domains_domain.bootcamp_domain]
}

data "kubernetes_service_v1" "ingress_nginx" {
  metadata {
    name      = "my-nginx-ingress-nginx-controller"
    namespace = "nginx"
  }
}

# Requesting a TLS certificate in ACM for the domain and subdomains
resource "aws_acm_certificate" "cert" {
  domain_name               = var.domain_name
  subject_alternative_names = ["*.${var.domain_name}"]
  validation_method         = "DNS"

  tags = {
    Name = "${var.domain_name}-cert"
  }

  lifecycle {
    create_before_destroy = true
  }
}

# Creating Route 53 validation records to prove domain ownership
resource "aws_route53_record" "cert_validation" {
  for_each = {
    for dvo in aws_acm_certificate.cert.domain_validation_options : dvo.domain_name => {
      name   = dvo.resource_record_name
      record = dvo.resource_record_value
      type   = dvo.resource_record_type
    }
  }

  allow_overwrite = true
  name            = each.value.name
  records         = [each.value.record]
  ttl             = 60
  type            = each.value.type
  zone_id         = data.aws_route53_zone.bootcamp_zone.zone_id
}

# Wait for the certificate to be validated by AWS
resource "aws_acm_certificate_validation" "cert_validation_waiter" {
  certificate_arn         = aws_acm_certificate.cert.arn
  validation_record_fqdns = [for record in aws_route53_record.cert_validation : record.fqdn]
}

# Final DNS Records for the subdomains
resource "aws_route53_record" "app_record" {
  zone_id = data.aws_route53_zone.bootcamp_zone.zone_id
  name    = "app.${var.domain_name}"
  type    = "CNAME"
  ttl     = 300
  records = [data.kubernetes_service_v1.ingress_nginx.status[0].load_balancer[0].ingress[0].hostname]
}

resource "aws_route53_record" "argocd_record" {
  zone_id = data.aws_route53_zone.bootcamp_zone.zone_id
  name    = "argocd.${var.domain_name}"
  type    = "CNAME"
  ttl     = 300
  records = [data.kubernetes_service_v1.ingress_nginx.status[0].load_balancer[0].ingress[0].hostname]
}
