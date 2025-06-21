#!/usr/bin/env python3
"""
Test Kubernetes PagerDuty Integration End-to-End

This script tests the complete flow:
1. Monitors Kubernetes cluster for issues
2. Generates PagerDuty-style alerts
3. Sends them to the Oncall Agent API
4. Verifies the agent's response
"""

import argparse
import asyncio
import json
import subprocess
from datetime import UTC, datetime

import httpx


class K8sMonitor:
    """Monitor Kubernetes cluster for issues."""

    def __init__(self, namespace: str = "demo-apps"):
        self.namespace = namespace
        self.known_issues = {}

    def run_kubectl(self, *args) -> dict:
        """Run kubectl command and return parsed JSON output."""
        cmd = ["kubectl", "-n", self.namespace] + list(args) + ["-o", "json"]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return json.loads(result.stdout)
        except subprocess.CalledProcessError as e:
            print(f"kubectl error: {e.stderr}")
            return {}
        except json.JSONDecodeError:
            return {}

    def check_pods(self) -> list[dict]:
        """Check for pod issues and return alerts."""
        alerts = []
        pods_data = self.run_kubectl("get", "pods")

        for pod in pods_data.get("items", []):
            pod_name = pod["metadata"]["name"]
            status = pod["status"]

            # Check for CrashLoopBackOff
            for container_status in status.get("containerStatuses", []):
                if container_status.get("state", {}).get("waiting", {}).get("reason") == "CrashLoopBackOff":
                    alerts.append({
                        "severity": "critical",
                        "service": pod["metadata"]["labels"].get("app", "unknown"),
                        "title": f"Pod {pod_name} is in CrashLoopBackOff",
                        "details": f"Container {container_status['name']} has restarted {container_status.get('restartCount', 0)} times",
                        "pod_name": pod_name,
                        "namespace": self.namespace,
                        "restart_count": container_status.get('restartCount', 0)
                    })

                # Check for ImagePullBackOff
                elif container_status.get("state", {}).get("waiting", {}).get("reason") == "ImagePullBackOff":
                    alerts.append({
                        "severity": "high",
                        "service": pod["metadata"]["labels"].get("app", "unknown"),
                        "title": f"Pod {pod_name} - ImagePullBackOff",
                        "details": f"Failed to pull image {container_status.get('image', 'unknown')}",
                        "pod_name": pod_name,
                        "namespace": self.namespace,
                        "image": container_status.get('image', 'unknown')
                    })

                # Check for OOMKilled
                elif container_status.get("lastState", {}).get("terminated", {}).get("reason") == "OOMKilled":
                    alerts.append({
                        "severity": "high",
                        "service": pod["metadata"]["labels"].get("app", "unknown"),
                        "title": f"Pod {pod_name} - OOMKilled",
                        "details": "Container terminated due to memory limit exceeded",
                        "pod_name": pod_name,
                        "namespace": self.namespace,
                        "memory_limit": pod["spec"]["containers"][0].get("resources", {}).get("limits", {}).get("memory", "unknown")
                    })

        return alerts

    def check_deployments(self) -> list[dict]:
        """Check for deployment issues."""
        alerts = []
        deployments = self.run_kubectl("get", "deployments")

        for deployment in deployments.get("items", []):
            name = deployment["metadata"]["name"]
            spec = deployment["spec"]
            status = deployment["status"]

            desired = spec.get("replicas", 0)
            available = status.get("availableReplicas", 0)

            # Check for zero replicas or unavailable replicas
            if desired == 0:
                alerts.append({
                    "severity": "high",
                    "service": name,
                    "title": f"Deployment {name} scaled to zero",
                    "details": "No replicas are running",
                    "deployment_name": name,
                    "namespace": self.namespace,
                    "desired_replicas": 0
                })
            elif available < desired:
                alerts.append({
                    "severity": "critical",
                    "service": name,
                    "title": f"Deployment {name} degraded",
                    "details": f"Only {available}/{desired} replicas available",
                    "deployment_name": name,
                    "namespace": self.namespace,
                    "desired_replicas": desired,
                    "available_replicas": available
                })

        return alerts

    def check_services(self) -> list[dict]:
        """Check for service issues."""
        alerts = []

        # Get all services
        services = self.run_kubectl("get", "services")

        # Get all endpoints
        endpoints = self.run_kubectl("get", "endpoints")
        endpoint_map = {ep["metadata"]["name"]: ep for ep in endpoints.get("items", [])}

        for service in services.get("items", []):
            name = service["metadata"]["name"]

            # Check if service has endpoints
            ep = endpoint_map.get(name, {})
            if not ep.get("subsets", []):
                alerts.append({
                    "severity": "critical",
                    "service": name,
                    "title": f"Service {name} has no endpoints",
                    "details": "No healthy pods available for this service",
                    "service_name": name,
                    "namespace": self.namespace
                })

        return alerts


def create_pagerduty_webhook(alert: dict) -> dict:
    """Convert K8s alert to PagerDuty webhook format."""
    incident_id = f"k8s-{alert.get('service', 'unknown')}-{datetime.now().timestamp():.0f}"

    return {
        "event": {
            "id": incident_id,
            "event_type": "incident.triggered",
            "incident": {
                "id": incident_id,
                "incident_number": int(datetime.now().timestamp() % 10000),
                "title": alert["title"],
                "description": alert["details"],
                "created_at": datetime.now(UTC).isoformat(),
                "status": "triggered",
                "incident_key": incident_id,
                "service": {
                    "id": f"svc-{alert.get('service', 'unknown')}",
                    "name": alert.get("service", "unknown"),
                    "type": "service"
                },
                "urgency": "high" if alert["severity"] == "critical" else "low",
                "body": {
                    "type": "incident_body",
                    "details": json.dumps({
                        k: v for k, v in alert.items()
                        if k not in ["severity", "service", "title", "details"]
                    })
                }
            }
        }
    }


async def send_alert_to_api(webhook_data: dict, api_url: str = "http://localhost:8000"):
    """Send PagerDuty webhook to the API."""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{api_url}/webhook/pagerduty",
                json=webhook_data,
                timeout=30.0
            )
            return response.status_code, response.json()
        except httpx.ConnectError:
            return None, {"error": "Cannot connect to API server. Is it running?"}
        except Exception as e:
            return None, {"error": str(e)}


async def main():
    """Main test function."""
    parser = argparse.ArgumentParser(description="Test K8s PagerDuty Integration")
    parser.add_argument("--api-url", default="http://localhost:8000", help="API server URL")
    parser.add_argument("--namespace", default="demo-apps", help="Kubernetes namespace to monitor")
    parser.add_argument("--once", action="store_true", help="Run once instead of continuous monitoring")
    args = parser.parse_args()

    print("🔍 Kubernetes PagerDuty Integration Test")
    print(f"📡 API URL: {args.api_url}")
    print(f"📦 Namespace: {args.namespace}")
    print("")

    # Check API health
    async with httpx.AsyncClient() as client:
        try:
            health = await client.get(f"{args.api_url}/health")
            if health.status_code == 200:
                print("✅ API server is healthy")
            else:
                print("⚠️  API server returned non-200 status")
        except:
            print("❌ Cannot connect to API server. Please ensure it's running:")
            print("   uv run python api_server.py")
            return

    monitor = K8sMonitor(namespace=args.namespace)
    processed_alerts = set()

    while True:
        print(f"\n🔍 Checking cluster at {datetime.now().strftime('%H:%M:%S')}...")

        # Collect all alerts
        all_alerts = []
        all_alerts.extend(monitor.check_pods())
        all_alerts.extend(monitor.check_deployments())
        all_alerts.extend(monitor.check_services())

        # Process new alerts
        for alert in all_alerts:
            alert_key = f"{alert['service']}-{alert['title']}"

            if alert_key not in processed_alerts:
                processed_alerts.add(alert_key)

                print(f"\n🚨 New Alert: {alert['title']}")
                print(f"   Service: {alert['service']}")
                print(f"   Severity: {alert['severity']}")
                print(f"   Details: {alert['details']}")

                # Convert to PagerDuty format
                webhook = create_pagerduty_webhook(alert)

                # Send to API
                print("   📤 Sending to Oncall Agent...")
                status, response = await send_alert_to_api(webhook, args.api_url)

                if status == 200:
                    print("   ✅ Alert processed successfully")
                    if "processing_id" in response:
                        print(f"   📋 Processing ID: {response['processing_id']}")
                else:
                    print(f"   ❌ Failed to send alert: {response.get('error', 'Unknown error')}")

        if not all_alerts:
            print("✅ No issues found in cluster")
        else:
            print(f"\n📊 Total active issues: {len(all_alerts)}")

        if args.once:
            break

        # Wait before next check
        print("\n⏳ Waiting 30 seconds before next check...")
        await asyncio.sleep(30)


if __name__ == "__main__":
    asyncio.run(main())
