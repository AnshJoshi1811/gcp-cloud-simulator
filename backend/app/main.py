"""Main FastAPI application"""
import asyncio
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from app.middleware.auth import AuthBypassMiddleware
from app.services.compute.router import router as compute_router
from app.services.compute.instance_groups import router as instance_groups_router
from app.services.vpc.router import router as vpc_router
from app.services.iam.router import router as iam_router
from app.services.gke.router import router as gke_router
from app.services.run.router import router as run_router
from app.services.artifacts.router import router as artifacts_router
from app.services.projects.router import router as projects_router
from app.services.monitoring.router import router as monitoring_router, storage as monitoring_storage
from app.services.monitoring.alert_evaluator import AlertPolicyEvaluator
from app.services.compute.metric_publisher import ComputeMetricPublisher
from app.services.gke.metric_publisher import GKEMetricPublisher
from app.services.run.metric_publisher import CloudRunMetricPublisher
from app.services.pubsub.router import router as pubsub_router
from app.services.autoscaling.router import router as autoscaling_router, storage as autoscaling_storage
from app.services.autoscaling.evaluator import AutoscalingEvaluator
from app.services.secretmanager.router import router as secretmanager_router
from app.services.kms.router import router as kms_router
from app.services.tasks.router import router as tasks_router
from app.services.sql.router import router as sql_router
from app.services.memorystore.router import router as memorystore_router
from app.api import storage  # storage remains in api/ (stable, 1100+ lines)
import os

app = FastAPI(
    title="GCP Stimulator",
    description="Minimal GCP API simulator with Docker integration",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Auth Bypass Middleware — logs identity from every request, never blocks
app.add_middleware(AuthBypassMiddleware)

@app.get("/")
def root():
    return {"message": "GCP Stimulator API", "version": "1.0.0"}

@app.get("/health")
def health():
    return {"status": "healthy"}

@app.get("/auth/info")
def auth_info(request: Request):
    """Returns the current auth mode and resolved caller identity."""
    return {
        "mode": "bypass",
        "identity": getattr(request.state, "user", "anonymous@stimulator"),
        "auth_method": getattr(request.state, "auth_method", "none"),
        "message": "All requests are accepted. Identity is extracted for logging only.",
    }

# Register routers with GCP API paths
app.include_router(compute_router, prefix="/compute/v1", tags=["Compute Engine"])
app.include_router(instance_groups_router, prefix="/compute/v1", tags=["Instance Groups"])
app.include_router(vpc_router, prefix="/compute/v1", tags=["VPC Networks"])
app.include_router(projects_router, prefix="/cloudresourcemanager/v1", tags=["Projects"])
app.include_router(iam_router, prefix="/v1", tags=["IAM & Admin"])

# Cloud Storage (in-memory implementation)
app.include_router(storage.router, tags=["Cloud Storage"])

# GKE — registered at both /container/v1 (internal UI) and /v1 (gcloud CLI compatibility)
app.include_router(gke_router, prefix="/container/v1", tags=["GKE"])
app.include_router(gke_router, prefix="/v1", tags=["GKE (gcloud CLI)"])

# Cloud Run — gcloud compatibility (run.googleapis.com/v2)
app.include_router(run_router, prefix="/v1", tags=["Cloud Run v1"])
app.include_router(run_router, prefix="/v2", tags=["Cloud Run"])
app.include_router(run_router, prefix="/run/v2", tags=["Cloud Run (alt)"])

# Artifact Registry — artifactregistry.googleapis.com/v1
app.include_router(artifacts_router, prefix="/v1", tags=["Artifact Registry"])

# Cloud Monitoring — monitoring.googleapis.com/v3
app.include_router(monitoring_router, prefix="/v3", tags=["Cloud Monitoring"])
app.include_router(monitoring_router, prefix="/monitoring/v3", tags=["Cloud Monitoring (alt)"])

# Cloud Pub/Sub — pubsub.googleapis.com/v1
app.include_router(pubsub_router, prefix="/v1", tags=["Cloud Pub/Sub"])
app.include_router(pubsub_router, prefix="/pubsub/v1", tags=["Cloud Pub/Sub (alt)"])

# Compute Engine Auto-Scaling — autoscaling.googleapis.com/v1
app.include_router(autoscaling_router, prefix="/compute/v1", tags=["Autoscaling"])

# Secret Manager — secretmanager.googleapis.com/v1
app.include_router(secretmanager_router, prefix="/v1", tags=["Secret Manager"])
app.include_router(secretmanager_router, prefix="/secretmanager/v1", tags=["Secret Manager (alt)"])

# Cloud KMS — cloudkms.googleapis.com/v1
app.include_router(kms_router, prefix="/v1", tags=["Cloud KMS"])
app.include_router(kms_router, prefix="/cloudkms/v1", tags=["Cloud KMS (alt)"])

# Cloud Tasks — cloudtasks.googleapis.com/v2
app.include_router(tasks_router, prefix="/v2", tags=["Cloud Tasks"])
app.include_router(tasks_router, prefix="/cloudtasks/v2", tags=["Cloud Tasks (alt)"])

# Cloud SQL — sqladmin.googleapis.com/v1
app.include_router(sql_router, prefix="/sql/v1beta4", tags=["Cloud SQL"])
app.include_router(sql_router, prefix="/sqladmin/v1", tags=["Cloud SQL (alt)"])

# Memorystore — redis.googleapis.com/v1
app.include_router(memorystore_router, prefix="/v1", tags=["Memorystore"])
app.include_router(memorystore_router, prefix="/redis/v1", tags=["Memorystore (alt)"])


def init_zones_and_machine_types(db):
    """Initialize zones and machine types if they don't exist"""
    from app.models.database import Zone, MachineType
    
    # Check if zones already exist
    if db.query(Zone).count() > 0:
        return
    
    # Define zones
    zones_data = [
        {"id": "us-central1-a", "name": "us-central1-a", "region": "us-central1", "status": "UP", "description": "us-central1-a"},
        {"id": "us-central1-b", "name": "us-central1-b", "region": "us-central1", "status": "UP", "description": "us-central1-b"},
        {"id": "us-central1-c", "name": "us-central1-c", "region": "us-central1", "status": "UP", "description": "us-central1-c"},
        {"id": "us-east1-b", "name": "us-east1-b", "region": "us-east1", "status": "UP", "description": "us-east1-b"},
        {"id": "us-east1-c", "name": "us-east1-c", "region": "us-east1", "status": "UP", "description": "us-east1-c"},
        {"id": "us-west1-a", "name": "us-west1-a", "region": "us-west1", "status": "UP", "description": "us-west1-a"},
        {"id": "us-west1-b", "name": "us-west1-b", "region": "us-west1", "status": "UP", "description": "us-west1-b"},
    ]
    
    # Define machine types (common types across zones)
    machine_types_data = [
        {"id": "e2-micro", "name": "e2-micro", "guest_cpus": 2, "memory_mb": 1024, "description": "2 vCPU, 1 GB RAM"},
        {"id": "e2-small", "name": "e2-small", "guest_cpus": 2, "memory_mb": 2048, "description": "2 vCPU, 2 GB RAM"},
        {"id": "e2-medium", "name": "e2-medium", "guest_cpus": 2, "memory_mb": 4096, "description": "2 vCPU, 4 GB RAM"},
        {"id": "n1-standard-1", "name": "n1-standard-1", "guest_cpus": 1, "memory_mb": 3840, "description": "1 vCPU, 3.75 GB RAM"},
        {"id": "n1-standard-2", "name": "n1-standard-2", "guest_cpus": 2, "memory_mb": 7680, "description": "2 vCPU, 7.5 GB RAM"},
        {"id": "n1-standard-4", "name": "n1-standard-4", "guest_cpus": 4, "memory_mb": 15360, "description": "4 vCPU, 15 GB RAM"},
    ]
    
    # Add zones
    for zone_data in zones_data:
        zone = Zone(**zone_data)
        db.add(zone)
    
    # Add machine types for each zone
    for zone_data in zones_data:
        for mt_data in machine_types_data:
            mt = MachineType(
                id=f"{zone_data['name']}-{mt_data['name']}",
                name=mt_data['name'],
                zone=zone_data['name'],
                guest_cpus=mt_data['guest_cpus'],
                memory_mb=mt_data['memory_mb'],
                description=mt_data.get('description')
            )
            db.add(mt)
    
    db.commit()
    print(f"✅ Initialized {len(zones_data)} zones and {len(zones_data) * len(machine_types_data)} machine types")


def initialize_default_projects(db):
    """Create default projects if they don't exist"""
    from app.models.database import Project
    from datetime import datetime
    
    default_projects = [
        {
            "id": "test-project",
            "name": "Test Project",
            "project_number": 123456789
        },
        {
            "id": "default",
            "name": "Default Project",
            "project_number": 987654321
        }
    ]
    
    for proj_data in default_projects:
        existing = db.query(Project).filter(Project.id == proj_data["id"]).first()
        if not existing:
            project = Project(
                id=proj_data["id"],
                name=proj_data["name"],
                project_number=proj_data["project_number"],
                compute_api_enabled=True
            )
            db.add(project)
            print(f"✅ Created default project: {proj_data['id']}")
        else:
            print(f"ℹ️  Project already exists: {proj_data['id']}")
    
    db.commit()
    print(f"✅ Default projects initialized")


@app.on_event("startup")
async def startup_event():
    """Initialize database tables, default networks, and background tasks"""
    from app.models.database import SessionLocal, Project, Base, engine
    from app.services.vpc.router import ensure_default_network
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        # Initialize default projects first
        initialize_default_projects(db)
        
        # Initialize zones and machine types
        init_zones_and_machine_types(db)
        
        # Initialize default networks for projects
        projects = db.query(Project).all()
        for project in projects:
            ensure_default_network(db, project.id)
        print(f"✅ Initialized default networks for {len(projects)} projects")
    except Exception as e:
        print(f"⚠️  Error initializing: {e}")
    finally:
        db.close()
    
    # Start Cloud Monitoring alert evaluator
    evaluator = AlertPolicyEvaluator(monitoring_storage)
    asyncio.create_task(evaluator.start())
    print("✅ Cloud Monitoring alert evaluator started")
    
    # Start metric publishers for Compute Engine, GKE, and Cloud Run
    compute_publisher = ComputeMetricPublisher(storage, monitoring_storage)
    asyncio.create_task(compute_publisher.start())
    print("✅ Compute Engine metric publisher started")
    
    gke_publisher = GKEMetricPublisher(storage, monitoring_storage)
    asyncio.create_task(gke_publisher.start())
    print("✅ GKE metric publisher started")
    
    run_publisher = CloudRunMetricPublisher(storage, monitoring_storage)
    asyncio.create_task(run_publisher.start())
    print("✅ Cloud Run metric publisher started")
    
    # Start Auto-Scaling evaluator
    autoscaling_evaluator = AutoscalingEvaluator(autoscaling_storage, monitoring_storage, storage)
    asyncio.create_task(autoscaling_evaluator.start())
    print("✅ Auto-Scaling evaluator started")


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8080))
    print(f"""
    ╔══════════════════════════════════════════════════════╗
    ║  🚀 GCP STIMULATOR BACKEND                          ║
    ║  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  ║
    ║  📍 http://0.0.0.0:{port}                           ║
    ║  📖 Docs: http://0.0.0.0:{port}/docs                ║
    ║  💾 Database: SQLite Local                          ║
    ║  🐳 Docker: Local daemon                            ║
    ╚══════════════════════════════════════════════════════╝
    """)
    uvicorn.run(app, host="0.0.0.0", port=port)
