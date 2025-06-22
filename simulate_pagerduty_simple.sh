#!/bin/bash

# Simple PagerDuty alert simulator that doesn't require Kubernetes
# This sends alerts directly to your PagerDuty webhook endpoint

set -e

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# PagerDuty webhook URL (update with your ngrok URL)
WEBHOOK_URL="${PAGERDUTY_WEBHOOK_URL:-http://localhost:8000/webhook/pagerduty}"

# Function to send a PagerDuty webhook
send_webhook() {
    local event_type="$1"
    local incident_id="$2"
    local title="$3"
    local status="${4:-triggered}"
    
    local timestamp=$(date -u +"%Y-%m-%dT%H:%M:%S.%3NZ")
    local event_id="TEST$(date +%s)$(( RANDOM % 1000 ))"
    
    local payload=$(cat <<EOF
{
  "event": {
    "id": "$event_id",
    "event_type": "incident.$event_type",
    "resource_type": "incident",
    "occurred_at": "$timestamp",
    "agent": {
      "id": "SIMULATED",
      "type": "service_reference",
      "summary": "Test Simulator"
    },
    "data": {
      "id": "$incident_id",
      "type": "incident",
      "title": "$title",
      "status": "$status",
      "incident_number": $((RANDOM % 1000 + 100)),
      "created_at": "$timestamp",
      "service": {
        "id": "TEST123",
        "name": "Test Service",
        "summary": "AI oncall test"
      },
      "urgency": "high"
    }
  }
}
EOF
)
    
    echo -e "${YELLOW}Sending $event_type webhook for: $title${NC}"
    
    # Send the webhook
    response=$(curl -s -X POST "$WEBHOOK_URL" \
        -H "Content-Type: application/json" \
        -H "X-PagerDuty-Signature: v1=test_signature" \
        -d "$payload" \
        -w "\n%{http_code}")
    
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | head -n-1)
    
    if [[ "$http_code" == "200" || "$http_code" == "201" || "$http_code" == "204" ]]; then
        echo -e "${GREEN}✓ Webhook sent successfully (HTTP $http_code)${NC}"
    else
        echo -e "${RED}✗ Webhook failed (HTTP $http_code)${NC}"
        echo "Response: $body"
    fi
    
    return 0
}

# Function to simulate different alert types
simulate_alert() {
    local alert_type="$1"
    local incident_id="INC$(date +%s)$(( RANDOM % 1000 ))"
    
    case "$alert_type" in
        1|pod_crash)
            echo -e "${RED}💥 Simulating Pod Crash Alert${NC}"
            send_webhook "triggered" "$incident_id" "Sum PodErrors GreaterThanOrEqualToThreshold 1.0"
            ;;
        2|oom)
            echo -e "${RED}💾 Simulating OOM Kill Alert${NC}"
            send_webhook "triggered" "$incident_id" "Sum OOMKills GreaterThanOrEqualToThreshold 1.0"
            ;;
        3|cpu)
            echo -e "${RED}🔥 Simulating High CPU Alert${NC}"
            send_webhook "triggered" "$incident_id" "CPU Utilization > 90% on production cluster"
            ;;
        4|deployment)
            echo -e "${RED}📦 Simulating Deployment Failure Alert${NC}"
            send_webhook "triggered" "$incident_id" "Deployment failed: oncall-agent-app"
            ;;
        5|generic)
            echo -e "${RED}🚨 Simulating Generic Alert${NC}"
            send_webhook "triggered" "$incident_id" "Sum ProblemPods GreaterThanOrEqualToThreshold 1.0"
            ;;
        resolve)
            if [ -z "$2" ]; then
                echo -e "${RED}Error: Please provide incident ID to resolve${NC}"
                echo "Usage: $0 resolve <incident_id>"
                exit 1
            fi
            echo -e "${GREEN}✅ Resolving incident: $2${NC}"
            send_webhook "resolved" "$2" "Incident Resolved" "resolved"
            ;;
        *)
            echo "Usage: $0 [option]"
            echo "Options:"
            echo "  1|pod_crash  - Simulate pod crash alert"
            echo "  2|oom        - Simulate OOM kill alert"
            echo "  3|cpu        - Simulate high CPU alert"
            echo "  4|deployment - Simulate deployment failure"
            echo "  5|generic    - Simulate generic alert"
            echo "  resolve <id> - Resolve an incident"
            echo ""
            echo "Webhook URL: $WEBHOOK_URL"
            echo "Set PAGERDUTY_WEBHOOK_URL env var to override"
            exit 1
            ;;
    esac
}

# Main execution
if [ $# -eq 0 ]; then
    # Default to pod crash
    simulate_alert "pod_crash"
else
    simulate_alert "$@"
fi

echo -e "${GREEN}Done!${NC}"