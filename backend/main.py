#!/usr/bin/env python3
"""Main entry point for the oncall AI agent."""

import asyncio
import logging
from datetime import datetime, timezone

from src.oncall_agent.agent import OncallAgent, PagerAlert
from src.oncall_agent.utils import setup_logging
from src.oncall_agent.config import get_config


async def simulate_pager_alert() -> PagerAlert:
    """Simulate receiving a pager alert for demonstration purposes."""
    # You can switch between different alert types for testing
    alert_type = "kubernetes"  # Change to "general" for non-k8s alert
    
    if alert_type == "kubernetes":
        # Kubernetes pod crash alert
        return PagerAlert(
            alert_id="K8S-ALERT-001",
            severity="critical",
            service_name="payment-service",
            description="Pod payment-service-7d9f8b6c5-x2n4m is in CrashLoopBackOff state, restarting every 30 seconds",
            timestamp=datetime.now(timezone.utc).isoformat(),
            metadata={
                "pod_name": "payment-service-7d9f8b6c5-x2n4m",
                "namespace": "production",
                "deployment_name": "payment-service",
                "restart_count": 12,
                "last_restart": "30 seconds ago",
                "cluster": "prod-us-east-1"
            }
        )
    else:
        # General service alert
        return PagerAlert(
            alert_id="ALERT-12345",
            severity="high",
            service_name="api-gateway",
            description="API Gateway experiencing high error rate (15% 5xx responses)",
            timestamp=datetime.now(timezone.utc).isoformat(),
            metadata={
                "error_rate": "15%",
                "affected_endpoints": ["/api/v1/users", "/api/v1/orders"],
                "duration": "5 minutes",
                "region": "us-east-1"
            }
        )


async def main():
    """Main function demonstrating the oncall agent."""
    # Set up logging
    config = get_config()
    setup_logging(level=config.log_level)
    logger = logging.getLogger(__name__)
    
    logger.info("Starting Oncall AI Agent")
    
    try:
        # Initialize the agent
        agent = OncallAgent()
        
        # Connect to any configured integrations (none for now)
        await agent.connect_integrations()
        
        # Simulate receiving a pager alert
        logger.info("Simulating pager alert reception...")
        alert = await simulate_pager_alert()
        
        logger.info(f"Received alert: {alert.alert_id} - {alert.description}")
        
        # Process the alert
        result = await agent.handle_pager_alert(alert)
        
        # Display the results
        logger.info("Alert Analysis Complete:")
        logger.info(f"Status: {result.get('status')}")
        
        # Show K8s-specific information if detected
        if result.get('k8s_alert_type'):
            logger.info(f"Kubernetes Alert Type: {result['k8s_alert_type']}")
            if result.get('k8s_context') and not result['k8s_context'].get('error'):
                logger.info("Kubernetes context successfully gathered")
                if result.get('suggested_actions'):
                    logger.info(f"Automated actions available: {len(result['suggested_actions'])}")
        
        if result.get('analysis'):
            print("\n" + "="*60)
            print("ALERT ANALYSIS")
            print("="*60)
            print(result['analysis'])
            print("="*60 + "\n")
        
        # Demonstrate how MCP integrations would be used
        if result.get('available_integrations'):
            logger.info(f"Available MCP integrations: {', '.join(result['available_integrations'])}")
            
            # Example of how to use MCP integrations (when implemented)
            logger.info("In a real scenario, the agent would now:")
            logger.info("1. Fetch metrics from Grafana MCP")
            logger.info("2. Check pod status via Kubernetes MCP")
            logger.info("3. Review recent deployments through GitHub MCP")
            logger.info("4. Update incident notes in Notion MCP")
        
        # Shutdown the agent
        await agent.shutdown()
        
    except KeyboardInterrupt:
        logger.info("Received interrupt signal, shutting down...")
    except Exception as e:
        logger.error(f"Error in main: {e}", exc_info=True)
    finally:
        logger.info("Oncall AI Agent shutdown complete")


if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())