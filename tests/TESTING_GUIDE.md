# 🧪 CloudTester - Complete Testing Guide

## Quick Start

### Run All Tests (API + gcloud by default)
```bash
./tests/run_full_suite.sh
```

### Run Wrapper Tests for Specific Feature
```bash
./tests/run_wrapper_tests.sh firewall
```

### Run Tests Without gcloud
```bash
./tests/run_full_suite.sh --no-gcloud
./tests/run_wrapper_tests.sh firewall --no-gcloud
```

### Generate Coverage Report
```bash
./tests/run_full_suite.sh --coverage
```

---

## Architecture

### Test Structure
```
tests/CloudTester/
├── base/
│   ├── api_client.py        # HTTP API helper
│   ├── gcloud_runner.py     # gcloud CLI helper
│   └── base_tester.py       # Parent test class
│
├── suites/
│   ├── integration/         # Stable, production tests
│   │   ├── test_firewall_api.py
│   │   ├── test_firewall_gcloud.py
│   │   ├── test_compute_api.py
│   │   └── test_compute_gcloud.py
│   │
│   └── test_*.py            # Original test files (legacy)
│
├── wrappers/                # Development tests (experimental)
│   ├── test_gke_api_dev.py
│   ├── test_gke_gcloud_dev.py
│   └── ...
│
├── scripts/
│   ├── create_service_tests.sh
│   ├── promote_to_stable.sh
│   └── ...
│
└── conftest.py              # Pytest configuration + fixtures
```

### Test Patterns

**File Naming:**
- API tests: `test_<service>_api.py` or `test_<service>_api_dev.py`
- gcloud tests: `test_<service>_gcloud.py` or `test_<service>_gcloud_dev.py`

**Test Status:**
- `test_<service>_api_dev.py` → Development (can be incomplete)
- `test_<service>_api.py` → Production/Stable (must be complete)

---

## Adding a New Service

### Step 1: Generate Test Templates
```bash
./tests/CloudTester/scripts/create_service_tests.sh gke
```

Creates:
- `tests/CloudTester/wrappers/test_gke_api_dev.py` (skeleton)
- `tests/CloudTester/wrappers/test_gke_gcloud_dev.py` (skeleton)

### Step 2: Implement API Tests
Edit `test_gke_api_dev.py`:

```python
from CloudTester.base import BaseTester

class TestGKEAPI(BaseTester):
    """Test GKE API endpoints"""
    
    def test_create_cluster(self):
        """Test: Create GKE cluster"""
        response = self.api.post(
            "/container/v1/projects/test-project/zones/us-central1-a/clusters",
            json={"cluster": {"name": "test-cluster"}}
        )
        
        self.assert_success(response)
        assert response.json()["name"] == "test-cluster"
    
    def test_list_clusters(self):
        """Test: List GKE clusters"""
        response = self.api.get(
            "/container/v1/projects/test-project/zones/us-central1-a/clusters"
        )
        
        self.assert_success(response)
        clusters = response.json().get("clusters", [])
        assert isinstance(clusters, list)
```

### Step 3: Implement gcloud Tests
Edit `test_gke_gcloud_dev.py`:

```python
from CloudTester.base import BaseTester

class TestGKEGcloud(BaseTester):
    """Test GKE via gcloud CLI"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.skip_if_no_gcloud()
        self.gcloud.set_project("test-project")
        yield
    
    def test_create_via_gcloud(self):
        """Test: gcloud container clusters create"""
        result = self.gcloud.run(
            "container clusters create test-cluster "
            "--zone=us-central1-a --num-nodes=3"
        )
        
        assert result.is_success()
        assert "test-cluster" in result.stdout
    
    def test_cross_validation(self):
        """Cross-check: Create via API, list via gcloud"""
        # Create via API
        self.api.post("/container/v1/...", json={...})
        
        # List via gcloud
        result = self.gcloud.run("container clusters list")
        assert result.is_success()
        # Verify cluster appears in gcloud list
```

### Step 4: Run Wrapper Tests
```bash
./tests/run_wrapper_tests.sh gke
# Output: htmlcov/wrapper-gke-20260225_143022.html
```

Fix any failures until all tests pass.

### Step 5: Promote to Stable
```bash
./tests/CloudTester/scripts/promote_to_stable.sh gke
```

This:
1. Copies tests from `wrappers/` to `suites/integration/`
2. Marks tests as "Stable" (not "Development")
3. Runs full regression suite
4. Confirms no regressions

### Step 6: Commit
```bash
git add .
git commit -m "feat: add GKE service with full test coverage"
```

Pre-commit hook validates:
- ✅ All stable API tests pass
- ✅ All stable gcloud tests pass
- ✅ Coverage didn't decrease

---

## Running Tests

### Basic Commands

```bash
# Run full suite (API + gcloud)
./tests/run_full_suite.sh

# Run specific feature wrapper tests
./tests/run_wrapper_tests.sh firewall

# Run API tests only
./tests/run_full_suite.sh --no-gcloud

# Run gcloud tests only
./tests/run_full_suite.sh --gcloud-only

# Run with code coverage
./tests/run_full_suite.sh --coverage

# Run in parallel
./tests/run_full_suite.sh --parallel

# Run specific marker
./tests/run_full_suite.sh --marker gke

# Run with all options
./tests/run_full_suite.sh --parallel --coverage --marker integration
```

### Output

Each test run generates:
- HTML test report: `htmlcov/wrapper-<service>-<timestamp>.html`
- Coverage report: `htmlcov/index.html` (with `--coverage`)
- JSON results: Can be parsed by CI/CD

---

## Test Fixtures (conftest.py)

### Available Fixtures

#### `api_client`
```python
def test_something(api_client):
    response = api_client.get("/path")
    assert response.status_code == 200
```

Methods:
- `get(path, **kwargs)` → requests.Response
- `post(path, json=data, **kwargs)` → requests.Response
- `put(path, json=data, **kwargs)` → requests.Response
- `patch(path, json=data, **kwargs)` → requests.Response
- `delete(path, **kwargs)` → requests.Response
- `wait_for_status(path, status, max_attempts=30)`
- `close()`

#### `gcloud_runner`
```python
def test_something(gcloud_runner):
    result = gcloud_runner.run("compute instances list")
    if result.is_success():
        data = result.json()
```

Methods:
- `run(command, format="json")` → GCloudResult
- `set_project(project_id)`
- `set_zone(zone)`
- `set_region(region)`

#### `test_project`, `test_zone`, `test_region`
```python
def test_something(test_project, test_zone):
    assert test_project == "test-project"
    assert test_zone == "us-central1-a"
```

---

## BaseTester Class

All test classes should inherit from `BaseTester`:

```python
from CloudTester.base import BaseTester

class TestMyService(BaseTester):
    def test_something(self):
        # self.api - APIClient instance
        # self.gcloud - GCloudRunner instance
        pass
```

### Assertion Helpers

```python
self.assert_success(response)           # Assert 200 OK
self.assert_success(response, 201)      # Assert 201 Created
self.assert_not_found(response)         # Assert 404
self.assert_bad_request(response)       # Assert 400
self.assert_conflict(response)          # Assert 409
```

### Skip Methods

```python
self.skip_if_no_gcloud()    # Skip if gcloud not available
self.skip_if_no_api()       # Skip if API not available
```

### Cleanup

```python
def test_something(self):
    resource_id = "my-resource"
    
    # ... test code ...
    
    # Cleanup (automatic in fixtures)
    self.cleanup_resource(resource_id, "/compute/v1/path")
    self.cleanup_project("test-project")
```

---

## Environment Configuration

Set in `tests/.env-test`:

```bash
TEST_API_URL=http://localhost:8080
TEST_PROJECT=test-project
TEST_ZONE=us-central1-a
TEST_REGION=us-central1
TEST_DB_PATH=/tmp/gcs-stimulator-test.db
TEST_TIMEOUT=30
ENABLE_GCLOUD_TESTS=true
```

Or via environment variables:
```bash
export TEST_API_URL=http://localhost:8080
export ENABLE_GCLOUD_TESTS=true
./tests/run_full_suite.sh
```

---

## CI/CD Integration

This now runs for real on every push/PR — see
[`.github/workflows/backend-ci.yml`](../.github/workflows/backend-ci.yml),
which installs the backend package (`pip install -e ".[test]"`, from
`backend/pyproject.toml`), starts the server, and runs
`pytest tests/integration`.

---

## Best Practices

### ✅ DO:

1. **Always implement cross-validation tests**
   - Create via API, verify via gcloud
   - Create via gcloud, verify via API

2. **Use descriptive test names**
   - ❌ `test_1`
   - ✅ `test_create_cluster_returns_200`

3. **Clean up after tests**
   - Use fixtures for automatic cleanup
   - Handle exceptions in cleanup code

4. **Test error cases**
   - Invalid input (400)
   - Not found (404)
   - Conflict (409)

5. **Group related tests in classes**
   ```python
   class TestFirewallCreate:
       def test_creates_resource(self): ...
       def test_validates_name(self): ...
   
   class TestFirewallDelete:
       def test_deletes_resource(self): ...
       def test_returns_404_for_missing(self): ...
   ```

### ❌ DON'T:

1. **Don't hardcode values**
   - ❌ `"test-project-hardcoded"`
   - ✅ Use `test_project` fixture

2. **Don't skip without reason**
   - ❌ `pytest.skip("not ready")`
   - ✅ `pytest.skip("API endpoint not yet implemented")`

3. **Don't mix API and gcloud tests**
   - Keep them in separate files

4. **Don't assume resource existence**
   - Create resources in test setup

5. **Don't ignore failures**
   - Debug and fix, don't skip

---

## Markers

Use pytest markers to categorize tests:

```python
@pytest.mark.api
def test_api_endpoint():
    pass

@pytest.mark.gcloud
def test_gcloud_command():
    pass

@pytest.mark.integration
def test_api_and_gcloud_together():
    pass
```

Run specific markers:
```bash
./tests/run_full_suite.sh --marker gcloud
./tests/run_full_suite.sh --marker "api and firewall"
```

---

## Troubleshooting

### "API not reachable"
```bash
# Start API server
cd minimal-backend
python main.py
```

### "gcloud not available"
```bash
# Install gcloud SDK
curl https://sdk.cloud.google.com | bash
exec -l $SHELL
```

### "Test times out"
```bash
# Increase timeout
export TEST_TIMEOUT=60
./tests/run_full_suite.sh
```

### "Tests fail with 404"
```bash
# Check if resource was created correctly
# Verify test setup fixture
# Check API endpoints
```

---

## Contributing

When adding new services:

1. ✅ Create both API and gcloud tests
2. ✅ All tests pass in wrapper mode
3. ✅ Promote to stable (no regressions)
4. ✅ Update this documentation
5. ✅ Commit with clear message

---

## Additional Resources

- [pytest documentation](https://docs.pytest.org/)
- [gcloud CLI reference](https://cloud.google.com/sdk/gcloud)
- [requests library](https://requests.readthedocs.io/)
- CloudTester code: `tests/CloudTester/base/`

