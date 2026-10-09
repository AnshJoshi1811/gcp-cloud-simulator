#!/bin/bash
# ============================================================
# GCP Stimulator — Activate / Deactivate
# Usage:
#   source stimulator on     → Start simulator + redirect gcloud
#   source stimulator off    → Stop simulator + restore gcloud
#   source stimulator status → Check if running
# ============================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"
PID_FILE="$SCRIPT_DIR/.stimulator.pid"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

_stimulator_on() {
    echo -e "${CYAN}"
    echo "  ╔══════════════════════════════════════════╗"
    echo "  ║  🚀 GCP Stimulator — Starting...         ║"
    echo "  ╚══════════════════════════════════════════╝"
    echo -e "${NC}"

    # Check if already running
    if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
        echo -e "${YELLOW}⚠️  Stimulator is already running (PID: $(cat "$PID_FILE"))${NC}"
        return 0
    fi

    # Check if port 8080 is already in use
    if lsof -i :8080 -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo -e "${YELLOW}⚠️  Port 8080 is already in use. Stimulator may already be running.${NC}"
        echo -e "${YELLOW}   Run: source stimulator off  — to stop it first.${NC}"
        return 1
    fi

    # Start backend in background
    echo -e "${GREEN}[1/3]${NC} Starting FastAPI backend on port 8080..."
    cd "$BACKEND_DIR" && \
    nohup python -m uvicorn app.main:app --host 0.0.0.0 --port 8080 \
        > "$SCRIPT_DIR/.stimulator.log" 2>&1 &
    local backend_pid=$!
    echo "$backend_pid" > "$PID_FILE"
    cd "$SCRIPT_DIR"

    # Wait for backend to be ready
    echo -e "${GREEN}[2/3]${NC} Waiting for backend to be ready..."
    local retries=0
    while [ $retries -lt 15 ]; do
        if curl -s http://localhost:8080/health > /dev/null 2>&1; then
            break
        fi
        sleep 1
        retries=$((retries + 1))
    done

    if [ $retries -ge 15 ]; then
        echo -e "${RED}❌ Backend failed to start. Check .stimulator.log${NC}"
        kill "$backend_pid" 2>/dev/null
        rm -f "$PID_FILE"
        return 1
    fi

    # Redirect gcloud CLI to simulator
    echo -e "${GREEN}[3/3]${NC} Redirecting gcloud CLI to simulator..."
    export CLOUDSDK_API_ENDPOINT_OVERRIDES_STORAGE="http://localhost:8080/storage/v1/"
    export CLOUDSDK_API_ENDPOINT_OVERRIDES_COMPUTE="http://localhost:8080/compute/v1/"
    export CLOUDSDK_API_ENDPOINT_OVERRIDES_IAM="http://localhost:8080/iam/"
    export CLOUDSDK_API_ENDPOINT_OVERRIDES_CONTAINER="http://localhost:8080/container/"
    export CLOUDSDK_API_ENDPOINT_OVERRIDES_RUN="http://localhost:8080/"
    export CLOUDSDK_API_ENDPOINT_OVERRIDES_ARTIFACTREGISTRY="http://localhost:8080/"
    export CLOUDSDK_CORE_PROJECT="test-project"
    export CLOUDSDK_CORE_DISABLE_PROMPTS="1"
    export STORAGE_EMULATOR_HOST="http://localhost:8080"
    export GCP_STIMULATOR_ACTIVE="true"

    echo ""
    echo -e "${GREEN}  ╔══════════════════════════════════════════╗"
    echo -e "  ║  ✅ GCP Stimulator is ACTIVE               ║"
    echo -e "  ║                                            ║"
    echo -e "  ║  Backend:  http://localhost:8080            ║"
    echo -e "  ║  Docs:     http://localhost:8080/docs       ║"
    echo -e "  ║  PID:      $backend_pid                          ║"
    echo -e "  ║                                            ║"
    echo -e "  ║  All gcloud commands now hit the simulator ║"
    echo -e "  ║  To stop:  source stimulator off           ║"
    echo -e "  ╚══════════════════════════════════════════════╝${NC}"
    echo ""
}

_stimulator_off() {
    echo -e "${CYAN}"
    echo "  ╔══════════════════════════════════════════╗"
    echo "  ║  🛑 GCP Stimulator — Stopping...         ║"
    echo "  ╚══════════════════════════════════════════╝"
    echo -e "${NC}"

    # Stop backend
    if [ -f "$PID_FILE" ]; then
        local pid
        pid=$(cat "$PID_FILE")
        if kill -0 "$pid" 2>/dev/null; then
            echo -e "${RED}[1/2]${NC} Stopping backend (PID: $pid)..."
            kill "$pid" 2>/dev/null
            sleep 1
            # Force kill if still running
            kill -9 "$pid" 2>/dev/null
        fi
        rm -f "$PID_FILE"
    else
        echo -e "${YELLOW}[1/2]${NC} No PID file found, killing any uvicorn on port 8080..."
        lsof -i :8080 -sTCP:LISTEN -t 2>/dev/null | xargs -r kill 2>/dev/null
    fi

    # Restore gcloud CLI to real GCP
    echo -e "${RED}[2/2]${NC} Restoring gcloud CLI to real GCP..."
    unset CLOUDSDK_API_ENDPOINT_OVERRIDES_STORAGE
    unset CLOUDSDK_API_ENDPOINT_OVERRIDES_COMPUTE
    unset CLOUDSDK_API_ENDPOINT_OVERRIDES_IAM
    unset CLOUDSDK_API_ENDPOINT_OVERRIDES_CONTAINER
    unset CLOUDSDK_API_ENDPOINT_OVERRIDES_RUN
    unset CLOUDSDK_API_ENDPOINT_OVERRIDES_ARTIFACTREGISTRY
    unset CLOUDSDK_CORE_DISABLE_PROMPTS
    unset STORAGE_EMULATOR_HOST
    unset GCP_STIMULATOR_ACTIVE

    echo ""
    echo -e "${RED}  ╔══════════════════════════════════════════╗"
    echo -e "  ║  ⏹️  GCP Stimulator is OFF                 ║"
    echo -e "  ║                                            ║"
    echo -e "  ║  gcloud now points to REAL Google Cloud    ║"
    echo -e "  ║  To start:  source stimulator on           ║"
    echo -e "  ╚══════════════════════════════════════════════╝${NC}"
    echo ""
}

_stimulator_status() {
    echo ""
    if [ "$GCP_STIMULATOR_ACTIVE" = "true" ]; then
        local pid="N/A"
        [ -f "$PID_FILE" ] && pid=$(cat "$PID_FILE")

        local health="❌ DOWN"
        if curl -s http://localhost:8080/health | grep -q "healthy" 2>/dev/null; then
            health="✅ HEALTHY"
        fi

        echo -e "${GREEN}  🟢 Stimulator is ACTIVE${NC}"
        echo -e "     PID:     $pid"
        echo -e "     Health:  $health"
        echo -e "     Backend: http://localhost:8080"
        echo -e "     gcloud:  → localhost (simulator)"
    else
        echo -e "${RED}  🔴 Stimulator is OFF${NC}"
        echo -e "     gcloud:  → googleapis.com (real GCP)"
    fi
    echo ""
}

# ─── Main ───
case "${1:-}" in
    on|start|activate)
        _stimulator_on
        ;;
    off|stop|deactivate)
        _stimulator_off
        ;;
    status)
        _stimulator_status
        ;;
    *)
        echo ""
        echo "Usage: source stimulator <command>"
        echo ""
        echo "Commands:"
        echo "  on      Start simulator + redirect gcloud"
        echo "  off     Stop simulator + restore gcloud to real GCP"
        echo "  status  Check if simulator is running"
        echo ""
        ;;
esac
