# GCP Stimulator 🚀

A **local GCP emulator** for development and testing: FastAPI backend with Docker-backed
services where that mirrors real GCP behavior (VM instances and Cloud SQL/Memorystore are
real Docker containers; VPCs are real Docker networks), and a React + TypeScript console UI.

> **📊 Status: 24 of 26 cataloged services implemented** (see
> [IMPLEMENTATION_TRACKER.md](IMPLEMENTATION_TRACKER.md) for the authoritative,
> per-service status). One service (Service Management / billing-quotas) is
> intentionally left partial and one (Deployment Manager) is intentionally
> skipped — both decisions, with rationale, are recorded in
> [DECISIONS.md](DECISIONS.md). This is a **local development tool**, not a
> certified or production GCP replacement: it is not API-complete, does not
> enforce IAM/quota limits, and several services use simplified semantics
> documented inline (e.g. Cloud KMS encryption is a reversible local stand-in,
> not real cryptography). It is, however, functionally real where it counts:
> Compute/VPC/SQL/Memorystore spin up actual Docker containers and networks,
> Cloud Functions actually executes your code, Cloud CDN actually caches real
> Storage bytes, and Event Routing actually dispatches Pub/Sub messages to
> Cloud Functions.
>
> **📝 Last updated**: 2026-10-09.

## 📁 Project Structure

```
gcs-emulator/
│
├── backend/                      # FastAPI Backend (Port 8080)
│   ├── app/
│   │   ├── api/                  # API routes (storage, compute, vpc, iam, firewall, gke)
│   │   │   ├── storage.py       # Cloud Storage API
│   │   │   ├── compute.py       # Compute Engine API
│   │   │   ├── vpc.py           # VPC Networks API
│   │   │   ├── routes.py        # Route Tables API
│   │   │   ├── firewall.py      # Firewall Rules API
│   │   │   ├── gke.py           # GKE Clusters API
│   │   │   ├── iam.py           # IAM API
│   │   │   └── projects.py      # Projects API
│   │   ├── services/             # Business logic by service
│   │   │   ├── compute/         # Compute Engine service
│   │   │   ├── vpc/             # VPC Network service
│   │   │   ├── iam/             # IAM service
│   │   │   ├── gke/             # GKE service
│   │   │   ├── monitoring/      # Cloud Monitoring service
│   │   │   ├── autoscaling/     # Autoscaling service
│   │   │   ├── pubsub/          # Cloud Pub/Sub service
│   │   │   ├── run/             # Cloud Run service
│   │   │   ├── artifacts/       # Artifact Registry service
│   │   │   ├── secretmanager/   # Secret Manager service
│   │   │   └── projects/        # Projects service
│   │   ├── models/               # SQLAlchemy ORM models
│   │   │   └── database.py
│   │   ├── core/                 # Core utilities
│   │   │   └── docker_manager.py # Docker lifecycle management
│   │   ├── utils/                # Utility scripts
│   │   │   ├── ip_manager.py
│   │   │   ├── migrate_cidr.py
│   │   │   ├── region_subnets.py
│   │   │   └── sync_docker_instances.py
│   │   └── main.py              # FastAPI entry point
│   ├── database.py              # Backward-compatibility layer
│   ├── core/                    # Legacy compatibility
│   ├── requirements.txt         # Python dependencies
│   └── README.md
│
├── frontend/                     # React + TypeScript Frontend (Port 3000)
│   ├── src/
│   │   ├── pages/               # Service pages (Storage, Compute, VPC, IAM, Monitoring, etc.)
│   │   ├── components/          # Reusable UI components
│   │   ├── api/                 # API client functions
│   │   ├── contexts/            # React context providers
│   │   ├── hooks/               # Custom React hooks
│   │   ├── layouts/             # Layout components
│   │   ├── types/               # TypeScript interfaces
│   │   ├── utils/               # Utility functions
│   │   ├── config/              # Configuration
│   │   ├── App.tsx              # Main app component
│   │   └── main.tsx             # React entry point
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   ├── Dockerfile
│   ├── nginx.conf
│   └── README.md
│
├── tests/                        # Test suites
│   ├── integration/              # Integration tests (20+ test suites)
│   ├── fixtures/                 # Test fixtures and utilities
│   ├── gcloud_wrappers/          # gcloud CLI wrappers
│   ├── scripts/                  # Test automation scripts
│   ├── unit/                     # Unit tests (ready for expansion)
│   ├── mocks/                    # Mock utilities (ready for expansion)
│   ├── conftest.py
│   └── README.md
│
├── docs/
│   └── archived/                 # Archived documentation
│
├── Files/                        # Important reference documentation
│   ├── CLAUDE.md
│   ├── DEVELOPMENT_RULES.md
│   ├── SKILLS_ROADMAP.md
│   └── ...
│
├── CLAUDE.md                    # Project context and architecture
├── IMPLEMENTATION_TRACKER.md    # Feature checklist
├── README.md                    # This file
├── pytest.ini                   # Pytest configuration
└── .env-gcloud                  # gcloud CLI environment
```

## 🗂️ Service Catalog (authoritative status)

| Service | Status | Notes |
|---|---|---|
| Projects, VPC, Compute Engine, Cloud Storage, IAM | ✅ Complete | Core infra, Docker-backed |
| GKE, Cloud Run, Artifact Registry | ✅ Complete | |
| Pub/Sub, Cloud Monitoring, Autoscaling | ✅ Complete | |
| Secret Manager, Cloud KMS, Cloud Tasks | ✅ Complete | KMS encryption is a local reversible stand-in, not real crypto |
| Cloud SQL, Memorystore | ✅ Complete | Real Postgres/MySQL/Redis containers (stub record if Docker unavailable) |
| Firestore, Cloud Logging | ✅ Complete | In-memory |
| Cloud Load Balancing | ✅ Complete | `:simulate` performs real round-robin HTTP routing to backend instances |
| Cloud Functions | ✅ Complete | Real execution: container-backed when Docker is available, in-process otherwise; Python only |
| API Gateway | ✅ Complete | Real proxy to deployed Cloud Functions or external URLs |
| Cloud Identity Platform | ✅ Complete | Email/password auth, salted-hashed, per project |
| Cloud CDN | ✅ Complete | Real in-memory cache fronting actual Storage objects |
| Event Routing (Eventarc-style) | ✅ Complete | Real Pub/Sub → Cloud Functions dispatch |
| Service Management | 🟡 Partial | Left as-is — no real billing to emulate locally, see DECISIONS.md |
| Deployment Manager | ⬜ Skipped | Deliberate — see DECISIONS.md (MiniCloud covers Terraform/IaC instead) |

Full per-service detail, dependencies, and history: [IMPLEMENTATION_TRACKER.md](IMPLEMENTATION_TRACKER.md).
Engineering decisions and rationale: [DECISIONS.md](DECISIONS.md).

## ✨ Features

### 🖥️ Compute Engine
- ✅ **VM Instances** - Create, start, stop, delete instances
- ✅ **Docker Integration** - Each VM = Docker container (ubuntu:22.04)
- ✅ **Networking** - Internal IPs, NAT gateway, Internet Gateway metadata
- ✅ **Machine Types** - 10 pre-configured types (e2-micro to n1-standard-8)
- ✅ **Zones & Regions** - 10 zones across 4 regions (us-central1, us-west1, us-east1, europe-west1)
- ✅ **gcloud CLI** - Full `gcloud compute` command support

### 🌐 VPC Networks
- ✅ **Custom VPCs** - Create, list, delete virtual networks
- ✅ **Docker Networks** - Each VPC = Docker network with bridge driver
- ✅ **Network Mapping** - Automatic instance-to-network attachment
- ✅ **Subnet Modes** - Auto and custom subnet support
- ✅ **Internet Gateway** - Default gateway for outbound connectivity (0.0.0.0/0)
- ✅ **Route Tables** - Manage routing with expandable data table UI
- ✅ **Subnets** - Create and manage subnets with CIDR validation
- ✅ **Routes** - Add and manage custom routes with priority levels

### 💾 Cloud Storage
- ✅ **Bucket Management** - Create, list, delete buckets
- ✅ **Object Operations** - Upload, download, list, delete objects
- ✅ **File System Storage** - Objects stored in `/tmp/gcs-storage/`
- ✅ **Hash Verification** - MD5 and CRC32C checksums
- ✅ **gcloud CLI** - 14/16 commands working (87.5% compatibility)
- ✅ **Metadata API** - Full object metadata support

### 👤 IAM Service Accounts
- ✅ **Service Accounts** - Create, list, get, delete accounts
- ✅ **Email Generation** - Automatic `{account}@{project}.iam.gserviceaccount.com`
- ✅ **Unique IDs** - Numeric identifiers for each account
- ✅ **REST API** - Full IAM API v1 compatibility

### 🎨 Frontend UI
- ✅ **Storage Dashboard** - Bucket and object management with upload/download
- ✅ **Compute Dashboard** - Instance lifecycle management
- ✅ **VPC Dashboard** - Network creation and management with quick access cards
- ✅ **Route Tables** - Data table UI with expandable rows for detailed routes view
- ✅ **Subnets & Routes** - Comprehensive networking resource management
- ✅ **IAM Dashboard** - Service account management
- ✅ **Real-time Updates** - Auto-refresh and health monitoring
- ✅ **Responsive Design** - Modern React with Tailwind CSS and Lucide icons

### 🗄️ Database & Architecture
- ✅ **PostgreSQL RDS** - Production-grade database in AWS RDS
- ✅ **11 Tables** - instances, networks, buckets, objects, projects, zones, machine_types, service_accounts, route_tables, routes, subnets
- ✅ **Foreign Keys** - Proper relationships and data integrity
- ✅ **Docker Backend** - Container lifecycle management via Docker API
- ✅ **File System** - Hybrid storage (metadata in DB, files on disk)
- ✅ **Auto-created Resources** - Internet Gateway routes created automatically for new VPCs

## 🚀 Quick Start

### Prerequisites
- Docker installed and running
- PostgreSQL RDS database (configured in `DATABASE_URL`)
- Node.js 18+ and npm
- Python 3.9+
- gcloud CLI (optional, for command-line testing)

### 1. Start Backend (Port 8080)

```bash
cd /home/ubuntu/gcs-emulator/backend

# Install Python dependencies
pip install -r requirements.txt

# Start FastAPI server with hot-reload
uvicorn app.main:app --reload --host 0.0.0.0 --port 8080

# Verify backend is running
curl http://localhost:8080/health
```

### 2. Start Frontend (Port 3000)

```bash
cd /home/ubuntu/gcs-emulator/frontend

# Install Node dependencies (first time only)
npm install

# Start Vite dev server
npm run dev -- --host 0.0.0.0

# Access UI at: http://localhost:3000
```

### 3. Configure gcloud CLI (Optional)

```bash
# Source environment variables
source /home/ubuntu/gcs-stimulator/.env-gcloud

# Test gcloud commands
gcloud compute zones list --project=test-project
gcloud storage buckets list --project=test-project
```

### Quick Test

```bash
# Create a VM instance
gcloud compute instances create test-vm \
  --zone=us-central1-a \
  --machine-type=e2-micro \
  --project=test-project

# Create a storage bucket
gcloud storage buckets create gs://my-test-bucket --project=test-project

# Upload a file
echo "Hello GCP!" > test.txt
gcloud storage cp test.txt gs://my-test-bucket/

# List objects
gcloud storage ls gs://my-test-bucket/
```

## 📖 Documentation

### Core Documentation
- **[GCLOUD_COMMANDS_REFERENCE.md](GCLOUD_COMMANDS_REFERENCE.md)** - Complete gcloud commands guide (14 working commands)
- **[DEMO_READY_CHECKLIST.md](DEMO_READY_CHECKLIST.md)** - System verification checklist
- **[DEMO_DAY_QUICK_START.md](DEMO_DAY_QUICK_START.md)** - Step-by-step demo guide

### Examples
- **[examples/gcloud-cli.md](examples/gcloud-cli.md)** - gcloud CLI usage examples
- **[examples/python-sdk.md](examples/python-sdk.md)** - Python SDK integration examples
- **[examples/rest-api.md](examples/rest-api.md)** - Direct REST API calls

### Architecture
- **Database Design** - 8 tables (instances, networks, buckets, objects, projects, zones, machine_types, service_accounts)
- **Docker Integration** - VM instances run as containers, VPCs as Docker networks
- **Storage Backend** - Hybrid model (metadata in PostgreSQL, files in `/tmp/gcs-storage/`)

## 🛠️ gcloud CLI Support

### Working Commands (14/16 = 87.5%)

**Compute Engine:**
```bash
gcloud compute zones list
gcloud compute machine-types list --zones=us-central1-a
gcloud compute instances list --zones=us-central1-a
gcloud compute instances create <name> --zone=us-central1-a --machine-type=e2-micro
gcloud compute instances stop <name> --zone=us-central1-a
gcloud compute instances start <name> --zone=us-central1-a
gcloud compute instances delete <name> --zone=us-central1-a
```

**VPC Networks:**
```bash
gcloud compute networks list
gcloud compute networks create <name> --subnet-mode=auto
gcloud compute networks delete <name>
```

**Cloud Storage:**
```bash
gcloud storage buckets list
gcloud storage buckets create gs://<bucket>
gcloud storage buckets delete gs://<bucket>
gcloud storage cp <local-file> gs://<bucket>/
gcloud storage ls gs://<bucket>/
gcloud storage rm gs://<bucket>/<object>
```

### Known Issues
- ⚠️ `gcloud storage cp gs://bucket/file ./local` - Download has gcloud client bug (use curl workaround)
- ⚠️ `gcloud storage cat gs://bucket/file` - Cat has gcloud client bug (use curl workaround)

**Workaround:**
```bash
# Download file
curl -o file.txt "http://localhost:8080/storage/v1/b/BUCKET/o/OBJECT?alt=media"
```

## 📊 API Endpoints

### Health & Status
- `GET /health` - Backend health check

### Compute Engine API
- `GET /compute/v1/projects/{project}/zones` - List zones
- `GET /compute/v1/projects/{project}/zones/{zone}` - Get zone details
- `GET /compute/v1/projects/{project}/zones/{zone}/machineTypes` - List machine types
- `GET /compute/v1/projects/{project}/zones/{zone}/instances` - List instances
- `POST /compute/v1/projects/{project}/zones/{zone}/instances` - Create instance
- `GET /compute/v1/projects/{project}/zones/{zone}/instances/{instance}` - Get instance
- `POST /compute/v1/projects/{project}/zones/{zone}/instances/{instance}/stop` - Stop instance
- `POST /compute/v1/projects/{project}/zones/{zone}/instances/{instance}/start` - Start instance
- `DELETE /compute/v1/projects/{project}/zones/{zone}/instances/{instance}` - Delete instance
- `GET /compute/v1/projects/{project}/global/internetGateways` - List internet gateways
- `GET /compute/v1/projects/{project}/global/internetGateways/{gateway}` - Get gateway

### VPC Networks API
- `GET /compute/v1/projects/{project}/global/networks` - List networks
- `POST /compute/v1/projects/{project}/global/networks` - Create network
- `GET /compute/v1/projects/{project}/global/networks/{network}` - Get network
- `DELETE /compute/v1/projects/{project}/global/networks/{network}` - Delete network

### Route Tables API
- `GET /compute/v1/projects/{project}/global/routeTables` - List all route tables
- `GET /compute/v1/projects/{project}/global/routeTables/{name}` - Get route table with embedded routes
- `POST /compute/v1/projects/{project}/global/routeTables` - Create route table
- `POST /compute/v1/projects/{project}/global/routeTables/{name}/addRoute` - Add route to table
- `DELETE /compute/v1/projects/{project}/global/routeTables/{name}` - Delete route table

### Routes API
- `GET /compute/v1/projects/{project}/global/routes` - List all routes
- `POST /compute/v1/projects/{project}/global/routes` - Create route
- `DELETE /compute/v1/projects/{project}/global/routes/{route}` - Delete route

### Cloud Storage API
- `GET /storage/v1/b` - List buckets
- `POST /storage/v1/b` - Create bucket
- `GET /storage/v1/b/{bucket}` - Get bucket
- `DELETE /storage/v1/b/{bucket}` - Delete bucket
- `GET /storage/v1/b/{bucket}/o` - List objects
- `GET /storage/v1/b/{bucket}/o/{object}?alt=media` - Download object
- `POST /upload/storage/v1/b/{bucket}/o` - Upload object
- `DELETE /storage/v1/b/{bucket}/o/{object}` - Delete object

### IAM API
- `GET /v1/projects/{project}/serviceAccounts` - List service accounts
- `POST /v1/projects/{project}/serviceAccounts` - Create service account
- `GET /v1/projects/{project}/serviceAccounts/{account}` - Get service account
- `DELETE /v1/projects/{project}/serviceAccounts/{account}` - Delete service account

### Projects API
- `GET /cloudresourcemanager/v1/projects` - List projects

## 🏗️ Architecture

### Docker Integration
```
GCP Instance ←→ Docker Container (ubuntu:22.04)
  ├── Instance ID → Container ID
  ├── Internal IP → Docker network IP (172.17.x.x)
  ├── External IP → NAT IP (127.0.0.1)
  └── Network → Docker network (gcp-vpc-{project}-{name})

GCP VPC ←→ Docker Network (bridge driver)
  ├── Network ID → Docker network name
  ├── Instances attached to VPC → Containers on Docker network
  └── Internet Gateway → Docker bridge (default NAT)
```

### Storage Architecture
```
Buckets → PostgreSQL buckets table
Objects → PostgreSQL objects table (metadata)
       → File system /tmp/gcs-storage/{bucket}/{object} (content)
```

### Database Schema
- **instances** - VM instances with Docker container mapping
- **networks** - VPC networks with Docker network mapping
- **buckets** - Cloud Storage buckets
- **objects** - Object metadata with file paths
- **projects** - GCP projects
- **zones** - Availability zones (10 pre-seeded)
- **machine_types** - VM types (10 pre-seeded)
- **service_accounts** - IAM service accounts

## 🎯 Use Cases

- ✅ **Local Development** - Test GCP services without cloud costs
- ✅ **CI/CD Pipelines** - Automated testing with real GCP API compatibility
- ✅ **Integration Testing** - Test multi-service GCP workflows
- ✅ **Offline Development** - Work without internet connection
- ✅ **Learning & Training** - Learn GCP without real credentials or costs
- ✅ **Demo & POC** - Demonstrate GCP architectures locally
- ✅ **Cost Optimization** - Develop and test before deploying to real GCP

## 📈 Current Status

**Services Implemented:** 4/4
- ✅ Compute Engine
- ✅ VPC Networks with Routes & Subnets
- ✅ Cloud Storage
- ✅ IAM Service Accounts

**API Compatibility:**
- Compute: 11 endpoints
- VPC: 4 endpoints
- Routes: 7 endpoints
- Storage: 8 endpoints
- IAM: 4 endpoints
- **Total: 34+ endpoints**

**gcloud CLI Compatibility:**
- Working: 14/16 commands (87.5%)
- Not working: 2 commands (gcloud client bugs, not backend issues)

**Frontend Pages:** 4/4 + Additional Views
- Storage Dashboard ✅
- Compute Dashboard ✅
- VPC Dashboard with Networking Resources ✅
- Route Tables Management ✅
- Subnets Management ✅
- Routes Management ✅
- IAM Dashboard ✅

## 🧪 Testing

### Backend Health Check
```bash
curl http://localhost:8080/health
# Expected: {"status":"healthy"}
```

### Test Full Workflow
```bash
# 1. Create VPC
gcloud compute networks create demo-vpc --subnet-mode=auto --project=test-project

# 2. Create VM on VPC
gcloud compute instances create demo-vm \
  --zone=us-central1-a \
  --machine-type=e2-micro \
  --network=demo-vpc \
  --project=test-project

# 3. Create bucket
gcloud storage buckets create gs://demo-bucket --project=test-project

# 4. Upload file
echo "Demo content" > demo.txt
gcloud storage cp demo.txt gs://demo-bucket/

# 5. Verify in UI
# Open http://localhost:3000 and check all resources
```

## 📝 License

MIT License

## 🤝 Contributing

Contributions welcome! 

### Recent Updates (Feb 10, 2026)
- ✅ Route Tables management with data table UI
- ✅ Expandable route table rows showing embedded routes
- ✅ Lazy-loaded route details when expanding tables
- ✅ VPC Dashboard integration with Networking Resources cards
- ✅ Route Tables quick access from VPC page
- ✅ Automatic Internet Gateway route creation (0.0.0.0/0)
- ✅ Subnets and Routes management pages
- ✅ Repository cleanup - removed documentation files

### Development Setup
```bash
# Clone repository
git clone <repo-url>
cd gcs-emulator

# Start backend
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload

# Start frontend
cd ../frontend
npm install
npm run dev
```

## 🐛 Known Issues

1. **gcloud storage download** - Client-side bug in gcloud CLI (not backend issue)
   - Workaround: Use curl for downloads
   
2. **gcloud storage cat** - Client-side bug in gcloud CLI (not backend issue)
   - Workaround: Use curl to view files

See [GCLOUD_COMMANDS_REFERENCE.md](GCLOUD_COMMANDS_REFERENCE.md) for complete workarounds.

## 📞 Support

- **Documentation**: See docs in root directory
- **Issues**: Report via GitHub issues
- **Demo**: See [DEMO_DAY_QUICK_START.md](DEMO_DAY_QUICK_START.md)

---

**Built with ❤️ for local GCP development and testing**

**Last Updated:** February 10, 2026  
**Version:** 2.0.0 - Route Tables Edition  
**Status:** ✅ Production Ready with Advanced Networking