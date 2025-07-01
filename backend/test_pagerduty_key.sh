#!/bin/bash
# Test script to verify PagerDuty integration key

INTEGRATION_KEY="${1:-4b7180d556684d0bc03539be88631e9c}"

echo "Testing PagerDuty integration key: $INTEGRATION_KEY"

curl -X POST https://events.pagerduty.com/v2/enqueue \
  -H 'Content-Type: application/json' \
  -d "{
    \"routing_key\": \"$INTEGRATION_KEY\",
    \"event_action\": \"trigger\",
    \"dedup_key\": \"test-key-verification-$(date +%s)\",
    \"payload\": {
      \"summary\": \"TEST: Integration Key Verification\",
      \"severity\": \"info\",
      \"source\": \"integration-key-tester\",
      \"custom_details\": {
        \"message\": \"This is a test to verify which service this integration key belongs to\",
        \"timestamp\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"
      }
    }
  }"

echo ""
echo "Check your PagerDuty dashboard to see which service received this test alert."
echo "The service that gets the alert is the one this integration key belongs to."