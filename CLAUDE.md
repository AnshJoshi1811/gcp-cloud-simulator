# Project: GCS Emulator

A comprehensive **Google Cloud Platform (GCP) emulator** that simulates GCP services locally with Docker integration.

## Tech Stack

### Backend
- **Framework**: FastAPI (Python)
- **Server**: Uvicorn
- **Database**: PostgreSQL (RDS)
- **ORM**: SQLAlchemy
- **Container Runtime**: Docker API
- **API Format**: REST JSON

### Frontend
- **Framework**: React 18 + TypeScript
- **Build Tool**: Vite
- **Styling**: Tailwind CSS
- **UI Components**: Lucide Icons, Headless UI
- **State Management**: React Context API
- **HTTP Client**: Axios
- **Forms**: React Hook Form + Zod validation
- **Routing**: React Router DOM v6

### Infrastructure
- **Backend Port**: 8080
- **Frontend Port**: 3000
- **Database**: PostgreSQL (AWS RDS)
- **Container Driver**: Docker (for VM emulation)
- **Storage**: File system + Database hybrid

## Directory Map

```
gcs-emulator/
├── backend/              # FastAPI Backend
│   ├── main.py                   # App entry, routes setup
│   ├── database.py               # SQLAlchemy models + DB setup
│   ├── docker_manager.py         # Docker container lifecycle
│   ├── api/                      # Route handlers
│   │   ├── storage.py           # Cloud Storage API
│   │   ├── compute.py           # Compute Engine/VM instances
│   │   ├── vpc.py               # VPC Networks
│   │   ├── routes.py            # Route Tables
│   │   ├── iam.py               # IAM Service Accounts
│   │   ├── projects.py          # Projects
│   │   ├── firewall.py          # Firewall rules
│   │   ├── autoscaling.py       # Autoscaling groups
│   │   ├── gke.py               # GKE clusters
│   │   └── [more services]      # Additional GCP services
│   ├── services/                # Business logic & domain services
│   │   ├── storage/
│   │   ├── compute/
│   │   ├── vpc/
│   │   ├── iam/
│   │   ├── monitoring/
│   │   ├── autoscaling/
│   │   ├── gke/
│   │   └── [others]
│   ├── core/                    # Shared utilities
│   │   └── database.py          # DB connection helpers
│   └── requirements.txt
│
├── frontend/            # React Frontend (Vite)
│   ├── src/
│   │   ├── pages/               # Page components (Storage, Compute, VPC, IAM, etc.)
│   │   ├── components/          # Reusable UI components
│   │   ├── api/                 # API client functions (axios calls)
│   │   ├── contexts/            # React Context providers
│   │   ├── hooks/               # Custom React hooks
│   │   ├── layouts/             # Layout wrappers
│   │   ├── types/               # TypeScript interfaces
│   │   ├── utils/               # Helper functions
│   │   ├── config/              # Config (API base URL, etc.)
│   │   ├── App.tsx              # Main app component
│   │   └── main.tsx             # React entry point
│   ├── vite.config.ts           # Vite build config
│   ├── tailwind.config.js       # Tailwind CSS config
│   ├── tsconfig.json            # TypeScript config
│   ├── package.json             # Dependencies & scripts
│   └── nginx.conf               # Nginx proxy (for Docker deployment)
│
├── tests/                       # Test suites
│   ├── CloudTester/             # Main test framework
│   │   ├── suites/              # Test suites by service
│   │   ├── wrappers/            # gcloud CLI wrappers
│   │   ├── scripts/             # Test automation scripts
│   │   └── base/                # Base test classes
│   └── legacy/                  # Legacy test files
│
├── docs/                        # Documentation
│   └── archived/                # Old docs and research
├── patches/                     # Git patches for external libraries
│
├── CLAUDE.md                    # This file (project context)
├── README.md                    # Main project README
├── CONTEXT_CHECKPOINT.md        # Context history
├── IMPLEMENTATION_TRACKER.md    # Feature tracking
├── pytest.ini                   # Pytest configuration
└── .env-gcloud                  # gcloud CLI environment config
```

## Architecture

### Backend Architecture
```
Request → uvicorn/FastAPI
         → FastAPI Router (/api/v1/...)
         → Handler (api/storage.py, etc)
         → Service Layer (services/storage/...)
         → Database (SQLAlchemy ORM)
         → Response (JSON)

Side effects:
  - Docker Manager: Container lifecycle (docker-py API)
  - Database: Persistent state in PostgreSQL
  - File System: Object storage in /tmp/gcs-storage/
```

### Frontend Architecture
```
Browser → Vite dev server / Nginx (prod)
        → React App (React Router)
        → Page Component
        → API Client (axios)
        → (HTTP) → Backend
        → Response handling
        → Component State/Context
        → DOM rendering
```

### Database Schema
**Key Tables:**
- `instances` — VM instances with zone, state, machine_type
- `networks` — VPC networks with CIDR blocks
- `subnets` — Network subnets with CIDR ranges
- `route_tables` — Routes with destination CIDR and priority
- `routes` — Individual routes (destination, target, priority)
- `buckets` — Cloud Storage buckets
- `objects` — Bucket objects with metadata (size, hash)
- `service_accounts` — IAM service accounts with email & unique ID
- `projects` — GCP projects
- `zones` — Availability zones (us-central1-a, etc)
- `machine_types` — VM machine types (e2-micro, n1-standard-8, etc)

### Design Patterns
- **Service Layer**: Business logic in `services/` (isolated from routes)
- **Docker Container Mapping**: Each VM instance = Docker container (ubuntu:22.04)
- **Network Mapping**: Each VPC = Docker network
- **Hybrid Storage**: Metadata in DB, actual objects on filesystem
- **REST API**: Standard HTTP verbs (GET, POST, DELETE, PATCH)
- **Status Propagation**: Node state → Database → Frontend polling

## Commands

### Backend Setup & Run
```bash
cd backend

# Install dependencies
pip install -r requirements.txt

# Run FastAPI dev server (hot-reload on :8080)
uvicorn main:app --reload --host 0.0.0.0 --port 8080

# Or: gunicorn for production
gunicorn -w 4 -k uvicorn.workers.UvicornWorker main:app
```

### Frontend Setup & Run
```bash
cd frontend

# Install dependencies
npm install

# Dev server (hot-reload on :3000)
npm run dev

# Build for production
npm run build

# Lint
npm run lint

# Preview production build
npm run preview
```

### Testing
```bash
cd tests

# Run full test suite
bash run_full_suite.sh

# Run specific test suite
cd CloudTester && python -m pytest suites/storage/ -v

# Run with coverage
pytest --cov=../backend --cov-report=html
```

### Utilities
```bash
# Check database connectivity
bash test-connectivity.sh

# Generate project context (for LLMs)
python generate_context.py
```

## Workflows

### Local Development
1. **Terminal 1 - Backend**:
   ```bash
   cd backend && uvicorn main:app --reload --host 0.0.0.0 --port 8080
   ```

2. **Terminal 2 - Frontend**:
   ```bash
   cd frontend && npm run dev
   ```

3. **Access**:
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8080
   - API Docs: http://localhost:8080/docs (Swagger)

### Adding a New GCP Service
1. Create SQLAlchemy models in `backend/database.py`
2. Create service logic in `backend/services/{service_name}/`
3. Create API routes in `backend/api/{service_name}.py`
4. Register route in `backend/main.py`
5. Create React page in `frontend/src/pages/`
6. Create API client in `frontend/src/api/{service_name}.ts`
7. Add routes to React Router in `frontend/src/App.tsx`

### Docker Integration
- **Backend**: Can be containerized with Dockerfile in `frontend/` (nginx proxy)
- **Frontend**: Served via Nginx in production
- **Database**: Expects PostgreSQL RDS connection via `DATABASE_URL` env var

## Environment Variables

### Backend (backend)
```ini
DATABASE_URL=postgresql://user:pass@host:5432/db_name
DOCKER_HOST=unix:///var/run/docker.sock  # or tcp://docker:2375
```

### Frontend (frontend)
```ini
VITE_API_BASE_URL=http://localhost:8080  # Backend API URL
```

## Key Features Implemented

✅ **Compute Engine** — VM instances, machine types, zones, gcloud CLI  
✅ **VPC Networks** — Custom networks, subnets, routes, gateways  
✅ **Cloud Storage** — Buckets, objects, upload/download, hashing  
✅ **IAM** — Service accounts with email generation & unique IDs  
✅ **Monitoring** — Metrics, monitoring dashboards, metric creation  
✅ **Autoscaling** — Instance groups, autoscaling policies  
✅ **GKE** — Kubernetes cluster emulation  
✅ **Frontend** — Modern React UI with real-time updates  

## Important Gotchas

1. **Docker Daemon Dependency**: Backend requires Docker daemon running. Container lifecycle operations fail if Docker is unavailable.

2. **Database Connection**: All backend requests depend on PostgreSQL RDS connection. Set `DATABASE_URL` or API will fail.

3. **File Storage**: Objects uploaded to Cloud Storage are stored on filesystem at `/tmp/gcs-storage/`. Ephemeral in container environments.

4. **Hot-reload**: Backend hot-reload (uvicorn --reload) can cause issues with Docker manager — may need full restart for some Docker operations.

5. **CORS**: Frontend makes requests to backend. Ensure CORS is configured if running on different domains/ports.

6. **Port Conflicts**: Ensure ports 3000 (frontend), 8080 (backend) are free before starting services.

7. **Network Mode**: Docker networks created by backend use bridge driver. Host network mode is NOT supported.

8. **gcloud CLI**: Requires `.env-gcloud` configured. Some commands have limited compatibility (87.5% for storage).

## Recent Features (from commits)

- Cloud Monitoring page with metric creation
- Instance groups and enhanced autoscaling UI
- Secret Manager, Autoscaling, Pub/Sub in service catalog
- Service catalog improvements
- Sidebar and proxy fixes
- Monitoring enhancements

## Testing Framework

- **Pytest** — Unit & integration tests via `tests/CloudTester/`
- **Test Suites** — Organized by service (storage, compute, vpc, iam, etc)
- **gcloud CLI Wrappers** — Validate gcloud command compatibility
- **CloudTester Base** — Reusable test fixtures and utilities

## Documentation

- `README.md` — Project overview
- `IMPLEMENTATION_TRACKER.md` — Feature checklist
- `CONTEXT_CHECKPOINT.md` — Context history
- API Docs — Auto-generated via Swagger at `/docs`

---

**Current Branch**: `feature/cloud-monitoring`  
**Latest Commit**: feat: add metric creation page and monitoring enhancements
