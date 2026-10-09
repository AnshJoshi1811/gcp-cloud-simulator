terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region                      = "us-east-1"
  access_key                  = "test"
  secret_key                  = "test"
  skip_credentials_validation = true
  skip_requesting_account_id  = true
  skip_metadata_api_check     = true

  endpoints {
    ec2 = "http://localhost:4566"
  }
}

resource "aws_instance" "web" {
  ami           = "ami-ubuntu-2204"
  instance_type = "t2.micro"

  user_data = <<-EOF
    #!/bin/sh
    echo "Hello from MiniCloud user_data" > /tmp/hello.txt
  EOF

  tags = {
    Name = "minicloud-example-instance"
  }
}

output "instance_id" {
  value = aws_instance.web.id
}

output "private_ip" {
  value = aws_instance.web.private_ip
}
