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

  storage_custom_endpoint = "http://localhost:4443/storage/v1/"
}

resource "google_storage_bucket" "probe" {
  name     = "mock-probe-bucket"
  location = "US"
}
