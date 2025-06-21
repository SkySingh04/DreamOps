"""Test PagerDuty alert generator for validating the integration."""

import argparse
import asyncio
import json
import random
from datetime import datetime
from typing import Any

import httpx

from src.oncall_agent.config import get_config
from src.oncall_agent.utils import get_logger

logger = get_logger(__name__)
config = get_config()


class MockPagerDutyAlertGenerator:
    """Generate realistic PagerDuty webhook payloads for testing."""

    def __init__(self, webhook_url: str | None = None):
        self.webhook_url = webhook_url or f"http://localhost:{config.api_port}/webhook/pagerduty"
        self.incident_counter = 1000

        # Alert templates
        self.alert_templates = {
            "database": [
                {
                    "title": "Database connection pool exhausted",
                    "description": "MySQL connection pool has reached maximum capacity",
                    "custom_details": {
                        "connection_count": 150,
                        "max_connections": 150,
                        "error_rate": "45%",
                        "affected_service": "user-service",
                        "query_time": "5000ms",
                        "database": "users_db"
                    }
                },
                {
                    "title": "Database query timeout - slow queries detected",
                    "description": "Multiple queries exceeding 30s timeout threshold",
                    "custom_details": {
                        "slow_queries": 25,
                        "avg_query_time": "45s",
                        "table": "order_history",
                        "operation": "SELECT with JOIN",
                        "affected_users": 1200
                    }
                }
            ],
            "server": [
                {
                    "title": "High CPU usage on production server",
                    "description": "CPU usage above 90% for more than 5 minutes",
                    "custom_details": {
                        "cpu_usage": "95%",
                        "memory_usage": "78%",
                        "load_average": "12.5, 11.2, 10.8",
                        "server": "prod-api-01",
                        "processes": 342,
                        "top_process": "java -Xmx4g"
                    }
                },
                {
                    "title": "Memory leak detected - OOM killer activated",
                    "description": "Out of memory killer terminated critical process",
                    "custom_details": {
                        "memory_usage": "98%",
                        "killed_process": "payment-service",
                        "pid": 12345,
                        "oom_score": 1000,
                        "container": "payment-service-7d9f8b6c5-xkz9p"
                    }
                }
            ],
            "security": [
                {
                    "title": "Suspicious authentication attempts detected",
                    "description": "Multiple failed login attempts from unknown IPs",
                    "custom_details": {
                        "failed_attempts": 150,
                        "unique_ips": 45,
                        "top_ip": "192.168.1.100",
                        "pattern": "brute_force",
                        "affected_accounts": 25,
                        "geo_location": "unknown"
                    }
                },
                {
                    "title": "Potential SQL injection attack",
                    "description": "Malicious SQL patterns detected in API requests",
                    "custom_details": {
                        "endpoint": "/api/v1/users",
                        "attack_pattern": "'; DROP TABLE users; --",
                        "source_ip": "10.0.0.50",
                        "user_agent": "sqlmap/1.4",
                        "blocked": True
                    }
                }
            ],
            "network": [
                {
                    "title": "Network latency spike - CDN issues",
                    "description": "Response times degraded across multiple regions",
                    "custom_details": {
                        "latency": "2500ms",
                        "normal_latency": "50ms",
                        "packet_loss": "12%",
                        "affected_regions": ["us-east-1", "eu-west-1"],
                        "cdn_provider": "cloudflare"
                    }
                },
                {
                    "title": "DNS resolution failures",
                    "description": "Internal DNS server not responding",
                    "custom_details": {
                        "dns_server": "10.0.0.53",
                        "failure_rate": "85%",
                        "timeout": "5s",
                        "affected_services": 12,
                        "fallback_dns": "8.8.8.8"
                    }
                }
            ],
            "kubernetes": [
                {
                    "title": "Pod crashloop detected in production",
                    "description": "Payment service pods failing to start",
                    "custom_details": {
                        "pod": "payment-service-7d9f8b6c5-xkz9p",
                        "namespace": "production",
                        "restart_count": 15,
                        "error": "Error: Cannot connect to Redis",
                        "deployment": "payment-service",
                        "replicas": "1/3"
                    }
                },
                {
                    "title": "Kubernetes node pressure - DiskPressure condition",
                    "description": "Node running out of disk space",
                    "custom_details": {
                        "node": "k8s-worker-03",
                        "disk_usage": "92%",
                        "condition": "DiskPressure=True",
                        "pods_affected": 8,
                        "namespace": "production"
                    }
                }
            ]
        }

    def generate_incident(self, alert_type: str | None = None, urgency: str = "high") -> dict[str, Any]:
        """Generate a single PagerDuty incident."""
        if not alert_type:
            alert_type = random.choice(list(self.alert_templates.keys()))

        template = random.choice(self.alert_templates[alert_type])
        self.incident_counter += 1

        incident_id = f"Q{self.incident_counter}ABCD"

        return {
            "id": incident_id,
            "incident_number": self.incident_counter,
            "title": template["title"],
            "description": template["description"],
            "created_at": datetime.now().isoformat(),
            "status": "triggered",
            "incident_key": f"alert-{alert_type}-{self.incident_counter}",
            "service": {
                "id": f"P{random.randint(100000, 999999)}",
                "name": f"{alert_type}-service",
                "html_url": "https://example.pagerduty.com/services/P123456",
                "summary": f"Service handling {alert_type} operations"
            },
            "urgency": urgency,
            "priority": {
                "id": "P53950",
                "name": urgency.upper(),
                "color": "red" if urgency == "high" else "yellow"
            },
            "custom_details": template["custom_details"],
            "html_url": f"https://example.pagerduty.com/incidents/{incident_id}"
        }

    def generate_webhook_payload(self, incidents: list[dict[str, Any]],
                               event: str = "incident.triggered") -> dict[str, Any]:
        """Generate a complete PagerDuty webhook payload."""
        messages = []

        for incident in incidents:
            messages.append({
                "id": f"msg-{incident['id']}",
                "incident": incident,
                "log_entries": [
                    {
                        "id": f"log-{incident['id']}",
                        "type": "trigger_log_entry",
                        "summary": f"Triggered: {incident['title']}",
                        "created_at": incident["created_at"],
                        "html_url": f"{incident['html_url']}/log_entries/Q1234"
                    }
                ]
            })

        return {
            "messages": messages,
            "event": event
        }

    async def send_webhook(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Send webhook to the API server."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                # Add signature header if secret is configured
                headers = {"Content-Type": "application/json"}
                if config.pagerduty_webhook_secret:
                    import hashlib
                    import hmac
                    body = json.dumps(payload).encode('utf-8')
                    signature = hmac.new(
                        config.pagerduty_webhook_secret.encode('utf-8'),
                        body,
                        hashlib.sha256
                    ).hexdigest()
                    headers["X-PagerDuty-Signature"] = signature

                response = await client.post(
                    self.webhook_url,
                    json=payload,
                    headers=headers
                )
                response.raise_for_status()
                return response.json()
            except Exception as e:
                logger.error(f"Error sending webhook: {e}")
                return {"error": str(e)}

    async def test_single_alert(self, alert_type: str | None = None, urgency: str = "high"):
        """Test with a single alert."""
        incident = self.generate_incident(alert_type, urgency)
        payload = self.generate_webhook_payload([incident])

        logger.info(f"Sending test alert: {incident['title']}")
        result = await self.send_webhook(payload)

        if "error" not in result:
            logger.info(f"✓ Alert sent successfully: {result}")
        else:
            logger.error(f"✗ Failed to send alert: {result}")

        return result

    async def test_batch_alerts(self, count: int = 5):
        """Test with multiple alerts."""
        incidents = []
        for _ in range(count):
            alert_type = random.choice(list(self.alert_templates.keys()))
            urgency = random.choice(["high", "medium", "low"])
            incidents.append(self.generate_incident(alert_type, urgency))

        payload = self.generate_webhook_payload(incidents)

        logger.info(f"Sending batch of {count} alerts")
        result = await self.send_webhook(payload)

        if "error" not in result:
            logger.info(f"✓ Batch sent successfully: {result}")
        else:
            logger.error(f"✗ Failed to send batch: {result}")

        return result

    async def test_all_types(self):
        """Test one alert of each type."""
        results = []

        for alert_type in self.alert_templates.keys():
            logger.info(f"\nTesting {alert_type} alert...")
            result = await self.test_single_alert(alert_type)
            results.append({
                "type": alert_type,
                "success": "error" not in result,
                "result": result
            })
            await asyncio.sleep(1)  # Small delay between alerts

        # Summary
        success_count = sum(1 for r in results if r["success"])
        logger.info(f"\n{'='*50}")
        logger.info(f"Test Summary: {success_count}/{len(results)} alerts processed successfully")

        return results

    async def stress_test(self, duration_seconds: int = 30, alerts_per_second: float = 1.0):
        """Stress test the webhook endpoint."""
        logger.info(f"Starting stress test: {alerts_per_second} alerts/sec for {duration_seconds}s")

        start_time = asyncio.get_event_loop().time()
        alerts_sent = 0
        errors = 0

        while asyncio.get_event_loop().time() - start_time < duration_seconds:
            try:
                await self.test_single_alert()
                alerts_sent += 1
            except Exception as e:
                logger.error(f"Error during stress test: {e}")
                errors += 1

            await asyncio.sleep(1.0 / alerts_per_second)

        elapsed = asyncio.get_event_loop().time() - start_time
        logger.info("\nStress Test Results:")
        logger.info(f"  Duration: {elapsed:.1f}s")
        logger.info(f"  Alerts sent: {alerts_sent}")
        logger.info(f"  Errors: {errors}")
        logger.info(f"  Success rate: {(alerts_sent-errors)/alerts_sent*100:.1f}%")
        logger.info(f"  Actual rate: {alerts_sent/elapsed:.2f} alerts/sec")


async def main():
    """Main test runner."""
    parser = argparse.ArgumentParser(description="Test PagerDuty webhook integration")
    parser.add_argument("--url", default=None, help="Webhook URL (default: http://localhost:8000/webhook/pagerduty)")
    parser.add_argument("--type", choices=["database", "server", "security", "network", "kubernetes"],
                       help="Alert type to test")
    parser.add_argument("--urgency", choices=["high", "medium", "low"], default="high",
                       help="Alert urgency")
    parser.add_argument("--batch", type=int, help="Send batch of N alerts")
    parser.add_argument("--all", action="store_true", help="Test all alert types")
    parser.add_argument("--stress", type=int, help="Run stress test for N seconds")
    parser.add_argument("--rate", type=float, default=1.0, help="Alerts per second for stress test")

    args = parser.parse_args()

    # Initialize generator
    generator = MockPagerDutyAlertGenerator(args.url)

    # Check API health first
    async with httpx.AsyncClient() as client:
        try:
            health_url = args.url.replace("/webhook/pagerduty", "/health") if args.url else f"http://localhost:{config.api_port}/health"
            response = await client.get(health_url)
            health = response.json()
            logger.info(f"API Health: {health}")
        except Exception as e:
            logger.error(f"API not reachable: {e}")
            logger.error("Make sure the API server is running: uv run python api_server.py")
            return

    # Run tests
    if args.all:
        await generator.test_all_types()
    elif args.batch:
        await generator.test_batch_alerts(args.batch)
    elif args.stress:
        await generator.stress_test(args.stress, args.rate)
    else:
        await generator.test_single_alert(args.type, args.urgency)


if __name__ == "__main__":
    asyncio.run(main())
