#!/bin/bash
set -e

echo "=========================================="
echo "Starting BARQ System Validation Suite"
echo "=========================================="

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

FAILED=0

check_endpoint() {
    local url=$1
    local expected_status=$2
    local desc=$3
    
    echo -n "Checking $desc ($url)... "
    status=$(curl -s -o /dev/null -w "%{http_code}" "$url")
    
    if [ "$status" -eq "$expected_status" ]; then
        echo -e "${GREEN}PASS (HTTP $status)${NC}"
    else
        echo -e "${RED}FAIL (Expected $expected_status, got $status)${NC}"
        FAILED=1
    fi
}

# 1. Check Public Access & Endpoints via NGINX (Port 8080)
check_endpoint "http://localhost:8080/" 200 "Root Endpoint"
check_endpoint "http://localhost:8080/health" 200 "Health Endpoint"
check_endpoint "http://localhost:8080/ready" 200 "Readiness Endpoint (DB+Redis)"
check_endpoint "http://localhost:8080/instance" 200 "Instance Identity Endpoint"

# Test POST/GET /records and /counter
echo -n "Checking /records creation... "
REC_RES=$(curl -s -X POST -H "Content-Type: application/json" -d '{"task":"validation_test"}' http://localhost:8080/records)
if echo "$REC_RES" | grep -q "id"; then
    echo -e "${GREEN}PASS${NC}"
else
    echo -e "${RED}FAIL${NC}"
    FAILED=1
fi

echo -n "Checking /counter increment... "
CNT_RES=$(curl -s -X GET http://localhost:8080/counter)
if echo "$CNT_RES" | grep -q "count"; then
    echo -e "${GREEN}PASS${NC}"
else
    echo -e "${RED}FAIL${NC}"
    FAILED=1
fi

# 2. Check Network Isolation & Prohibited Host Ports
echo -n "Checking prohibited PostgreSQL port (15432) binding... "
if nc -z localhost 15432 2>/dev/null; then
    echo -e "${RED}FAIL (PostgreSQL port 15432 is exposed to host!)${NC}"
    FAILED=1
else
    echo -e "${GREEN}PASS (Correctly isolated)${NC}"
fi

echo -n "Checking prohibited Redis port (16379) binding... "
if nc -z localhost 16379 2>/dev/null; then
    echo -e "${RED}FAIL (Redis port 16379 is exposed to host!)${NC}"
    FAILED=1
else
    echo -e "${GREEN}PASS (Correctly isolated)${NC}"
fi

echo "=========================================="
if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}All validations PASSED successfully!${NC}"
    exit 0
else
    echo -e "${RED}Some validations FAILED!${NC}"
    exit 1
fi
