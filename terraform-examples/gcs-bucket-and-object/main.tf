terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project      = "test-project"
  region       = "us-central1"
  access_token = "dummy-access-token"

  storage_custom_endpoint = "http://localhost:8090/storage/v1/"
}

resource "google_storage_bucket" "data" {
  name     = "gcp-stimulator-example-bucket"
  location = "US"
}

resource "google_storage_bucket_object" "hello" {
  name    = "hello.txt"
  bucket  = google_storage_bucket.data.name
  content = "Hello from gcp-cloud-simulator, proxied to real fake-gcs-server\n"
}

output "bucket_name" {
  value = google_storage_bucket.data.name
}

output "object_name" {
  value = google_storage_bucket_object.hello.name
}
