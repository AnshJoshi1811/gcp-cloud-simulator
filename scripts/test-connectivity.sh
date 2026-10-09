#!/bin/bash
set -e

echo "=== GCS Stimulator Connectivity Test ==="
echo

echo "1. Testing Backend (Port 8080)..."
BACKEND_STATUS=$(curl -s -w "%{http_code}" -o /dev/null http://localhost:8080/health)
if [ "$BACKEND_STATUS" = "200" ]; then
    echo "   ✅ Backend is healthy"
else
    echo "   ❌ Backend is not responding (HTTP $BACKEND_STATUS)"
    exit 1
fi

echo

echo "2. Testing Frontend (Port 3000)..."
FRONTEND_STATUS=$(curl -s -w "%{http_code}" -o /dev/null http://localhost:3000/)
if [ "$FRONTEND_STATUS" = "200" ]; then
    echo "   ✅ Frontend is responding"
else
    echo "   ❌ Frontend is not responding (HTTP $FRONTEND_STATUS)"
    exit 1
fi

echo

echo "3. Testing Frontend → Backend Proxy..."
PROXY_STATUS=$(curl -s -w "%{http_code}" -o /dev/null http://localhost:3000/api/health)
if [ "$PROXY_STATUS" = "200" ]; then
    echo "   ✅ Proxy is working"
else
    echo "   ❌ Proxy is not working (HTTP $PROXY_STATUS)"
    exit 1
fi

echo

echo "4. Testing Storage API through Proxy..."
STORAGE_RESPONSE=$(curl -s "http://localhost:3000/api/storage/v1/b?project=demo-project")
if echo "$STORAGE_RESPONSE" | grep -q "kind"; then
    echo "   ✅ Storage API is accessible"
    echo "   Response: $STORAGE_RESPONSE"
else
    echo "   ❌ Storage API is not working"
    echo "   Response: $STORAGE_RESPONSE"
    exit 1
fi

echo

echo "5. Network Information..."
echo "   Internal IP: $(hostname -I | awk '{print $1}')"
echo "   Listening ports:"
ss -tlnp 2>/dev/null | grep -E ':(3000|8080)' || netstat -tlnp 2>/dev/null | grep -E ':(3000|8080)' || echo "   (Unable to check ports)"

echo

echo "=== All Tests Passed! ==="
echo

echo "📝 How to Access:"
echo "   1. FROM THIS MACHINE:"
echo "      - Frontend: http://localhost:3000"
echo "      - Backend:  http://localhost:8080"
echo

echo "   2. FROM YOUR LOCAL MACHINE (SSH Tunnel):"
echo "      Run this command on YOUR local machine:"
echo "      ssh -L 3000:localhost:3000 -L 8080:localhost:8080 ubuntu@<SERVER_IP>"
echo "      Then access: http://localhost:3000"
echo

echo "   3. FROM YOUR LOCAL MACHINE (Port Forward - if in Kubernetes):"
echo "      kubectl port-forward <POD_NAME> 3000:3000 8080:8080"
echo "      Then access: http://localhost:3000"
echo
