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
  s3_use_path_style           = true

  endpoints {
    s3 = "http://localhost:4566"
  }
}

resource "aws_s3_bucket" "data" {
  bucket = "minicloud-example-bucket"
}

resource "aws_s3_object" "hello" {
  bucket       = aws_s3_bucket.data.id
  key          = "hello.txt"
  content      = "Hello from MiniCloud S3!"
  content_type = "text/plain"
}

output "bucket_name" {
  value = aws_s3_bucket.data.bucket
}

output "object_key" {
  value = aws_s3_object.hello.key
}
