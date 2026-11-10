# Intentionally insecure Terraform, added after a baseline: checkov should block it.
# Do not copy this into real infrastructure.

resource "aws_security_group" "rdp_open" {
  name        = "rdp-open"
  description = "RDP open to the world"

  ingress {
    description = "rdp"
    from_port   = 3389
    to_port     = 3389
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
}
