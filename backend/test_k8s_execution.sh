#!/bin/bash

# Test script for K8s MCP execution functionality

echo "=================================="
echo "K8s MCP Execution Test Script"
echo "=================================="
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Check prerequisites
echo "Checking prerequisites..."

if ! command -v kubectl &> /dev/null; then
    echo -e "${RED}Error: kubectl not found${NC}"
    exit 1
fi

if ! kubectl cluster-info &> /dev/null; then
    echo -e "${RED}Error: No valid kubernetes cluster${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Prerequisites check passed${NC}"
echo ""

# Menu
echo "Select test scenario:"
echo "1. Test YOLO mode (auto-execute)"
echo "2. Test Approval mode"
echo "3. Test Plan mode (preview only)"
echo "4. Test with fuck_kubernetes.sh issues"
echo "5. Test via API endpoint"
echo ""

read -p "Enter choice (1-5): " choice

case $choice in
    1)
        echo -e "\n${YELLOW}Testing YOLO Mode${NC}"
        echo "This will auto-execute remediation commands"
        read -p "Continue? (y/n): " confirm
        if [ "$confirm" = "y" ]; then
            # Ensure YOLO mode is enabled
            export K8S_ENABLE_DESTRUCTIVE_OPERATIONS=true
            python test_yolo_mode.py
        fi
        ;;
        
    2)
        echo -e "\n${YELLOW}Testing Approval Mode${NC}"
        echo "This will request approval before executing"
        # Temporarily change mode in agent
        python -c "
import asyncio
from src.oncall_agent.agent_enhanced import EnhancedOncallAgent
from src.oncall_agent.api.schemas import AIMode
from src.oncall_agent.agent import PagerAlert
from datetime import datetime

async def test():
    agent = EnhancedOncallAgent(ai_mode=AIMode.APPROVAL)
    await agent.connect_integrations()
    
    alert = PagerAlert(
        alert_id='test-approval',
        severity='high',
        service_name='test-service',
        description='Pod test-pod is in CrashLoopBackOff state',
        timestamp=datetime.utcnow().isoformat(),
        metadata={'pod_name': 'test-pod', 'namespace': 'default'}
    )
    
    result = await agent.handle_pager_alert(alert)
    print(f'Mode: {result[\"ai_mode\"]}')
    print(f'Actions proposed: {len(result.get(\"resolution_actions\", []))}')
    
    await agent.shutdown()

asyncio.run(test())
"
        ;;
        
    3)
        echo -e "\n${YELLOW}Testing Plan Mode${NC}"
        echo "This will only show what would be executed"
        python -c "
import asyncio
from src.oncall_agent.agent_enhanced import EnhancedOncallAgent
from src.oncall_agent.api.schemas import AIMode
from src.oncall_agent.agent import PagerAlert
from datetime import datetime

async def test():
    agent = EnhancedOncallAgent(ai_mode=AIMode.PLAN)
    await agent.connect_integrations()
    
    alert = PagerAlert(
        alert_id='test-plan',
        severity='high',
        service_name='test-service',
        description='Pod test-pod is in CrashLoopBackOff state',
        timestamp=datetime.utcnow().isoformat(),
        metadata={'pod_name': 'test-pod', 'namespace': 'default'}
    )
    
    result = await agent.handle_pager_alert(alert)
    print(f'Mode: {result[\"ai_mode\"]}')
    
    if result.get('command_preview'):
        print('\\nCommand Preview:')
        for cmd in result['command_preview']:
            print(f'  {cmd[\"command\"]} (risk: {cmd[\"risk_level\"]})')
    
    await agent.shutdown()

asyncio.run(test())
"
        ;;
        
    4)
        echo -e "\n${YELLOW}Testing with fuck_kubernetes.sh${NC}"
        echo "This requires fuck_kubernetes.sh to create issues first"
        echo ""
        echo "1. Run: ./fuck_kubernetes.sh 1"
        echo "2. Wait for pods to crash"
        echo "3. Run this test"
        echo ""
        read -p "Have you created K8s issues? (y/n): " ready
        if [ "$ready" = "y" ]; then
            export K8S_ENABLE_DESTRUCTIVE_OPERATIONS=true
            python test_yolo_mode.py --fuck-kubernetes
        fi
        ;;
        
    5)
        echo -e "\n${YELLOW}Testing via API${NC}"
        echo "Starting API server..."
        
        # Start API in background
        python -m uvicorn src.oncall_agent.api:app --host 0.0.0.0 --port 8000 &
        API_PID=$!
        
        # Wait for API to start
        sleep 5
        
        echo -e "\n${GREEN}API Started${NC}"
        echo "You can now test:"
        echo ""
        echo "1. Get agent config:"
        echo "   curl http://localhost:8000/api/v1/agent/config"
        echo ""
        echo "2. Update mode to YOLO:"
        echo "   curl -X PUT http://localhost:8000/api/v1/agent/config \\"
        echo "     -H 'Content-Type: application/json' \\"
        echo "     -d '{\"mode\": \"yolo\"}'"
        echo ""
        echo "3. Execute a test action:"
        echo "   curl -X POST http://localhost:8000/api/v1/agent/execute-action \\"
        echo "     -H 'Content-Type: application/json' \\"
        echo "     -d '{"
        echo "       \"action_type\": \"restart_pod\","
        echo "       \"params\": {"
        echo "         \"pod_name\": \"test-pod\","
        echo "         \"namespace\": \"default\""
        echo "       },"
        echo "       \"dry_run\": true"
        echo "     }'"
        echo ""
        echo "4. Get execution history:"
        echo "   curl http://localhost:8000/api/v1/agent/execution-history"
        echo ""
        echo "5. Get K8s audit log:"
        echo "   curl http://localhost:8000/api/v1/agent/k8s-audit-log"
        echo ""
        
        read -p "Press Enter to stop API server..."
        kill $API_PID
        ;;
        
    *)
        echo -e "${RED}Invalid choice${NC}"
        exit 1
        ;;
esac

echo -e "\n${GREEN}Test completed${NC}"