"""
CloudTester - Pytest Configuration & Shared Fixtures
Global test setup, database initialization, and reusable fixtures
"""

import pytest
import os
import sys
import json
import requests
import time
import subprocess
from pathlib import Path
from typing import Dict, Any, Generator
from datetime import datetime
from dataclasses import dataclass

# Add minimal-backend to path so we can import it
sys.path.insert(0, str(Path(__file__).parent.parent / "minimal-backend"))

# Test configuration
TEST_API_URL = os.getenv("TEST_API_URL", "http://localhost:8080")
TEST_PROJECT = os.getenv("TEST_PROJECT", "test-project")
TEST_REGION = os.getenv("TEST_REGION", "us-central1")
TEST_ZONE = os.getenv("TEST_ZONE", "us-central1-a")
TEST_DB_PATH = os.getenv("TEST_DB_PATH", "/tmp/gcs-stimulator-test.db")
TEST_TIMEOUT = int(os.getenv("TEST_TIMEOUT", "30"))
ENABLE_GCLOUD_TESTS = os.getenv("ENABLE_GCLOUD_TESTS", "true").lower() == "true"

# Markers for test categorization
pytest.mark.unit = pytest.mark.unit
pytest.mark.integration = pytest.mark.integration
pytest.mark.e2e = pytest.mark.e2e
pytest.mark.api = pytest.mark.api
pytest.mark.gcloud = pytest.mark.gcloud


@dataclass
class GCloudResult:
    """Result of gcloud command execution"""
    exit_code: int
    stdout: str
    stderr: str
    
    def is_success(self) -> bool:
        """Check if command succeeded"""
        return self.exit_code == 0
    
    def json(self) -> Dict[str, Any]:
        """Parse stdout as JSON"""
        try:
            return json.loads(self.stdout)
        except json.JSONDecodeError:
            raise ValueError(f"Failed to parse gcloud output as JSON: {self.stdout}")


class APIClient:
    """Helper class for making API requests"""
    
    def __init__(self, base_url: str = TEST_API_URL):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json"
        })
    
    def get(self, path: str, **kwargs) -> requests.Response:
        """GET request"""
        url = self._build_url(path)
        return self.session.get(url, timeout=TEST_TIMEOUT, **kwargs)
    
    def post(self, path: str, data: Dict = None, **kwargs) -> requests.Response:
        """POST request"""
        url = self._build_url(path)
        # Handle binary data vs JSON data
        if isinstance(data, bytes):
            return self.session.post(url, data=data, timeout=TEST_TIMEOUT, **kwargs)
        return self.session.post(url, json=data, timeout=TEST_TIMEOUT, **kwargs)
    
    def patch(self, path: str, data: Dict = None, **kwargs) -> requests.Response:
        """PATCH request"""
        url = self._build_url(path)
        return self.session.patch(url, json=data, timeout=TEST_TIMEOUT, **kwargs)
    
    def put(self, path: str, data: Dict = None, **kwargs) -> requests.Response:
        """PUT request"""
        url = self._build_url(path)
        return self.session.put(url, json=data, timeout=TEST_TIMEOUT, **kwargs)
    
    def delete(self, path: str, **kwargs) -> requests.Response:
        """DELETE request"""
        url = self._build_url(path)
        return self.session.delete(url, timeout=TEST_TIMEOUT, **kwargs)
    
    def _build_url(self, path: str) -> str:
        """Build full URL from path"""
        if path.startswith("http"):
            return path
        if not path.startswith("/"):
            path = "/" + path
        return f"{self.base_url}{path}"
    
    def wait_for_status(self, path: str, expected_status: str, max_attempts: int = 30, interval: float = 1.0) -> bool:
        """Wait for resource status to change (useful for async operations)"""
        for attempt in range(max_attempts):
            resp = self.get(path)
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, dict) and data.get("status") == expected_status:
                    return True
            time.sleep(interval)
        return False
    
    def close(self):
        """Close the session"""
        self.session.close()


class GCloudRunner:
    """Helper class for running gcloud commands"""
    
    # Class-level cache for gcloud availability (check once per test session)
    _availability_checked = False
    _gcloud_available = False
    
    def __init__(self, project: str = TEST_PROJECT, zone: str = TEST_ZONE):
        self.project = project
        self.zone = zone
        self.region = zone.rsplit("-", 1)[0] if zone else "us-central1"
        self._check_available()
    
    def _check_available(self):
        """Check if gcloud is available with retry logic and caching"""
        # Use cached result if already checked
        if GCloudRunner._availability_checked:
            self.available = GCloudRunner._gcloud_available
            return
        
        # Perform the check
        max_retries = 3
        for attempt in range(max_retries):
            try:
                result = subprocess.run(
                    ["gcloud", "--version"], 
                    capture_output=True, 
                    timeout=10,
                    env=os.environ.copy()
                )
                if result.returncode == 0:
                    self.available = True
                    GCloudRunner._gcloud_available = True
                    GCloudRunner._availability_checked = True
                    return
            except FileNotFoundError:
                self.available = False
                GCloudRunner._gcloud_available = False
                GCloudRunner._availability_checked = True
                return
            except subprocess.TimeoutExpired:
                if attempt < max_retries - 1:
                    time.sleep(0.5)
                    continue
                else:
                    self.available = False
                    GCloudRunner._gcloud_available = False
                    GCloudRunner._availability_checked = True
                    return
        self.available = False
        GCloudRunner._gcloud_available = False
        GCloudRunner._availability_checked = True
    
    def run(self, command: str, format: str = "json") -> GCloudResult:
        """Run gcloud command"""
        if not self.available:
            return GCloudResult(exit_code=127, stdout="", stderr="gcloud not available")
        
        full_command = f"gcloud {command}"
        
        # Add format unless specified
        if format and "--format" not in command:
            full_command += f" --format={format}"
        
        # Add project
        if "--project" not in command:
            full_command += f" --project={self.project}"
        
        try:
            result = subprocess.run(
                full_command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=60
            )
            return GCloudResult(
                exit_code=result.returncode,
                stdout=result.stdout.strip(),
                stderr=result.stderr.strip()
            )
        except subprocess.TimeoutExpired:
            return GCloudResult(exit_code=1, stdout="", stderr="Timeout")
        except Exception as e:
            return GCloudResult(exit_code=1, stdout="", stderr=str(e))
    
    def set_project(self, project: str):
        """Set active project"""
        self.project = project
    
    def set_zone(self, zone: str):
        """Set active zone"""
        self.zone = zone
        self.region = zone.rsplit("-", 1)[0]


@pytest.fixture(scope="session")
def api_client() -> APIClient:
    """Global API client for all tests"""
    client = APIClient(TEST_API_URL)
    
    # Verify API is reachable
    max_retries = 5
    for attempt in range(max_retries):
        try:
            resp = client.get("/health")
            if resp.status_code == 200:
                print(f"\n✓ API is healthy at {TEST_API_URL}")
                return client
        except requests.ConnectionError:
            if attempt < max_retries - 1:
                print(f"⏳ Waiting for API to be ready... (attempt {attempt + 1}/{max_retries})")
                time.sleep(2)
            else:
                raise Exception(f"API not reachable at {TEST_API_URL}")
    
    return client


@pytest.fixture
def test_project() -> str:
    """Test project ID"""
    return TEST_PROJECT


@pytest.fixture
def test_zone() -> str:
    """Test zone"""
    return TEST_ZONE


@pytest.fixture
def test_region() -> str:
    """Test region"""
    return TEST_REGION


@pytest.fixture
def base_url() -> str:
    """Base API URL"""
    return TEST_API_URL


@pytest.fixture
def cleanup_resources():
    """Fixture for cleaning up resources after tests"""
    resources_to_delete = {
        "instances": [],
        "networks": [],
        "buckets": [],
        "clusters": [],
    }
    
    yield resources_to_delete
    
    # Cleanup logic would go here
    # For now, just log what would be deleted
    if any(resources_to_delete.values()):
        print(f"\n🧹 Would delete: {resources_to_delete}")


@pytest.fixture
def sample_instance_payload() -> Dict[str, Any]:
    """Sample VM instance creation payload"""
    return {
        "name": f"test-instance-{int(datetime.now().timestamp())}",
        "machineType": "e2-medium",
        "zone": TEST_ZONE,
        "networkInterfaces": [
            {
                "network": "default",
                "subnetwork": "default"
            }
        ]
    }


@pytest.fixture
def sample_network_payload() -> Dict[str, Any]:
    """Sample VPC network creation payload"""
    return {
        "name": f"test-vpc-{int(datetime.now().timestamp())}",
        "autoCreateSubnetworks": True,
        "description": "Test VPC network"
    }


@pytest.fixture
def sample_bucket_payload() -> Dict[str, Any]:
    """Sample Cloud Storage bucket creation payload"""
    return {
        "name": f"test-bucket-{int(datetime.now().timestamp())}",
        "location": TEST_REGION,
        "storageClass": "STANDARD"
    }


@pytest.fixture
def sample_firewall_payload() -> Dict[str, Any]:
    """Sample firewall rule creation payload"""
    return {
        "name": f"test-rule-{int(datetime.now().timestamp())}",
        "network": "default",
        "priority": 1000,
        "direction": "INGRESS",
        "allowed": [
            {
                "IPProtocol": "tcp",
                "ports": ["22"]
            }
        ],
        "sourceRanges": ["0.0.0.0/0"]
    }


@pytest.fixture
def sample_cluster_payload() -> Dict[str, Any]:
    """Sample GKE cluster creation payload"""
    return {
        "cluster": {
            "name": f"test-cluster-{int(datetime.now().timestamp())}",
            "initialNodeCount": 3,
            "description": "Test GKE cluster",
            "nodeConfig": {
                "machineType": "e2-medium"
            }
        }
    }


def pytest_configure(config):
    """Configure pytest with custom markers"""
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "e2e: mark test as an end-to-end test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )


def pytest_collection_modifyitems(config, items):
    """Categorize tests by markers"""
    for item in items:
        # If test file is in suites/, mark as integration by default
        if "suites" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        # If test file is in wrappers/, mark as unit
        elif "wrappers" in str(item.fspath):
            item.add_marker(pytest.mark.unit)


@pytest.fixture(scope="session")
def gcloud_runner() -> GCloudRunner:
    """Global gcloud runner for all tests"""
    runner = GCloudRunner(TEST_PROJECT, TEST_ZONE)
    if not runner.available and ENABLE_GCLOUD_TESTS:
        print(f"\n⚠️  Warning: gcloud CLI not available. gcloud tests will be skipped.")
    return runner


# Test session info
@pytest.fixture(scope="session", autouse=True)
def test_session_info():
    """Print test session information"""
    # Check gcloud availability
    gcloud_runner = GCloudRunner(TEST_PROJECT, TEST_ZONE)
    gcloud_status = "✓ Available" if gcloud_runner.available else "✗ Not available"
    
    print(f"\n\n{'='*70}")
    print(f"  CloudTester Session Started")
    print(f"{'='*70}")
    print(f"  API URL:         {TEST_API_URL}")
    print(f"  Test Project:    {TEST_PROJECT}")
    print(f"  Test Zone:       {TEST_ZONE}")
    print(f"  Test Region:     {TEST_REGION}")
    print(f"  DB Path:         {TEST_DB_PATH}")
    print(f"  Timeout:         {TEST_TIMEOUT}s")
    print(f"  GCloud:          {gcloud_status}")
    print(f"  GCloud Tests:    {'Enabled ☁️ ' if ENABLE_GCLOUD_TESTS else 'Disabled'}")
    print(f"{'='*70}\n")

