"""Grafana MCP integration for metrics and dashboards access."""

import asyncio
import json
import subprocess
from datetime import datetime
from typing import Any

import httpx

from .base import MCPIntegration


class GrafanaMCPIntegration(MCPIntegration):
    """Grafana MCP integration for metrics, dashboards, and alerts."""

    def __init__(self, config: dict[str, Any] | None = None):
        """Initialize Grafana MCP integration.
        
        Args:
            config: Configuration dictionary containing:
                - grafana_url: Grafana instance URL
                - grafana_api_key: Grafana API key
                - grafana_username: Grafana username (alternative to API key)
                - grafana_password: Grafana password (alternative to API key)
                - mcp_server_path: Path to Grafana MCP server binary
                - server_host: Host for MCP server
                - server_port: Port for MCP server
        """
        super().__init__("grafana", config)
        self.process: subprocess.Popen | None = None
        self.client: httpx.AsyncClient | None = None

        # Grafana connection details
        self.grafana_url = self.config.get("grafana_url")
        self.grafana_api_key = self.config.get("grafana_api_key")
        self.grafana_username = self.config.get("grafana_username")
        self.grafana_password = self.config.get("grafana_password")

        # MCP server configuration
        self.mcp_server_path = self.config.get("mcp_server_path", "../../mcp-grafana/dist/mcp-grafana")
        self.server_host = self.config.get("server_host", "localhost")
        self.server_port = self.config.get("server_port", 8081)
        self.server_url = f"http://{self.server_host}:{self.server_port}"

        # Validate configuration
        if not self.grafana_url:
            raise ValueError("grafana_url is required in config")

        if not self.grafana_api_key and not (self.grafana_username and self.grafana_password):
            raise ValueError("Either grafana_api_key or grafana_username/password is required")

    async def connect(self) -> None:
        """Connect to the Grafana MCP server."""
        try:
            # Set up environment variables for the MCP server
            env = {
                "GRAFANA_URL": self.grafana_url,
                "GRAFANA_HOST": self.server_host,
                "GRAFANA_PORT": str(self.server_port)
            }

            # Add authentication
            if self.grafana_api_key:
                env["GRAFANA_API_KEY"] = self.grafana_api_key
            else:
                env["GRAFANA_USERNAME"] = self.grafana_username
                env["GRAFANA_PASSWORD"] = self.grafana_password

            # Start the Grafana MCP server process
            self.logger.info(f"Starting Grafana MCP server: {self.mcp_server_path}")
            self.process = subprocess.Popen(
                [self.mcp_server_path, "stdio"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env={**env}
            )

            # Wait for the server to start
            await asyncio.sleep(3)

            # Check if process is still running
            if self.process.poll() is not None:
                stderr = self.process.stderr.read() if self.process.stderr else ""
                raise ConnectionError(f"Grafana MCP server failed to start: {stderr}")

            # Initialize MCP connection
            try:
                await self._initialize_mcp_connection()
                self.connected = True
                self.connection_time = datetime.now()
                self.logger.info("Connected to Grafana MCP server")
            except Exception as e:
                self.logger.warning(f"MCP server initialization failed, using direct mode: {e}")
                # Fall back to direct Grafana API mode
                await self._setup_direct_mode()

        except Exception as e:
            self.logger.error(f"Failed to connect to Grafana MCP: {e}")
            # Try direct Grafana API as fallback
            try:
                await self._setup_direct_mode()
            except Exception as direct_error:
                raise ConnectionError(f"Both MCP and direct modes failed: {e}, {direct_error}")

    async def _setup_direct_mode(self) -> None:
        """Set up direct Grafana API connection as fallback."""
        headers = {}
        if self.grafana_api_key:
            headers["Authorization"] = f"Bearer {self.grafana_api_key}"

        # Ensure grafana_url is not None
        if not self.grafana_url:
            raise ValueError("grafana_url is required for direct mode")

        self.client = httpx.AsyncClient(
            base_url=self.grafana_url,
            headers=headers,
            timeout=30.0
        )

        # Test direct connection
        response = await self.client.get("/api/health")
        if response.status_code == 200:
            self.connected = True
            self.connection_time = datetime.now()
            self.logger.info("Connected to Grafana via direct API")
        else:
            raise ConnectionError(f"Direct Grafana API connection failed: {response.status_code}")

    async def _initialize_mcp_connection(self) -> None:
        """Initialize MCP connection via stdio."""
        if not self.process or not self.process.stdout or not self.process.stdin:
            raise ConnectionError("MCP process not properly initialized")

        # Send initialization message
        init_message = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "oncall-agent",
                    "version": "1.0.0"
                }
            }
        }

        # Send initialization
        init_json = json.dumps(init_message) + "\n"
        self.process.stdin.write(init_json.encode())
        self.process.stdin.flush()

        # Wait for response
        response = self.process.stdout.readline()
        if not response:
            raise ConnectionError("No response from MCP server")

        response_data = json.loads(response.decode().strip())
        if "error" in response_data:
            raise ConnectionError(f"MCP initialization failed: {response_data['error']}")

        # Send initialized notification
        initialized_message = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "initialized",
            "params": {}
        }

        initialized_json = json.dumps(initialized_message) + "\n"
        self.process.stdin.write(initialized_json.encode())
        self.process.stdin.flush()

        self.logger.info("MCP connection initialized successfully")

    async def _call_mcp_tool(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Call an MCP tool via stdio communication."""
        if not self.process or self.process.poll() is not None:
            raise RuntimeError("MCP server is not running")

        if not self.process.stdin or not self.process.stdout:
            raise RuntimeError("MCP process streams not available")

        message_id = self._generate_message_id()

        # Create tool call message
        tool_message = {
            "jsonrpc": "2.0",
            "id": message_id,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }

        # Send message
        message_json = json.dumps(tool_message) + "\n"
        self.process.stdin.write(message_json.encode())
        self.process.stdin.flush()

        # Read response
        response_line = await asyncio.wait_for(
            asyncio.create_task(asyncio.to_thread(self.process.stdout.readline)),
            timeout=10.0
        )

        if not response_line:
            raise RuntimeError(f"No response for tool call: {tool_name}")

        response = json.loads(response_line.decode().strip())

        if "error" in response:
            raise RuntimeError(f"MCP tool error: {response['error']}")

        if "result" in response:
            return response["result"]

        raise RuntimeError(f"Invalid response for tool call: {tool_name}")

    async def disconnect(self) -> None:
        """Disconnect from the Grafana MCP server."""
        if self.client:
            await self.client.aclose()
            self.client = None

        if self.process:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()
            self.process = None

        self.connected = False
        self.connection_time = None
        self.logger.info("Disconnected from Grafana MCP server")

    async def fetch_context(self, context_type: str, **kwargs) -> dict[str, Any]:
        """Fetch context information from Grafana.
        
        Args:
            context_type: Type of context to fetch:
                - "dashboards": Get available dashboards
                - "metrics": Get specific metrics
                - "alerts": Get current alerts
                - "datasources": Get available data sources
                - "search": Search dashboards/panels
            **kwargs: Additional parameters
        
        Returns:
            Context information from Grafana
        """
        self.validate_connection()

        try:
            if context_type == "dashboards":
                return await self._fetch_dashboards(**kwargs)
            elif context_type == "metrics":
                return await self._fetch_metrics(**kwargs)
            elif context_type == "alerts":
                return await self._fetch_alerts(**kwargs)
            elif context_type == "datasources":
                return await self._fetch_datasources(**kwargs)
            elif context_type == "search":
                return await self._search_grafana(**kwargs)
            else:
                raise ValueError(f"Unsupported context type: {context_type}")
        except Exception as e:
            self.logger.error(f"Failed to fetch {context_type} context: {e}")
            return {"error": str(e)}

    async def execute_action(self, action: str, params: dict[str, Any]) -> dict[str, Any]:
        """Execute an action in Grafana.
        
        Args:
            action: Action to perform:
                - "create_dashboard": Create new dashboard
                - "update_dashboard": Update existing dashboard
                - "create_alert": Create alert rule
                - "silence_alert": Silence an alert
                - "query_metrics": Query metrics data
            params: Parameters for the action
        
        Returns:
            Result of the action
        """
        self.validate_connection()

        try:
            if action == "create_dashboard":
                return await self._create_dashboard(**params)
            elif action == "update_dashboard":
                return await self._update_dashboard(**params)
            elif action == "create_alert":
                return await self._create_alert(**params)
            elif action == "silence_alert":
                return await self._silence_alert(**params)
            elif action == "query_metrics":
                return await self._query_metrics(**params)
            else:
                raise ValueError(f"Unsupported action: {action}")
        except Exception as e:
            self.logger.error(f"Failed to execute {action}: {e}")
            return {"error": str(e)}

    async def get_capabilities(self) -> dict[str, list[str]]:
        """Get capabilities of the Grafana integration."""
        return {
            "context_types": [
                "dashboards",
                "metrics",
                "alerts",
                "datasources",
                "search"
            ],
            "actions": [
                "create_dashboard",
                "update_dashboard",
                "create_alert",
                "silence_alert",
                "query_metrics"
            ],
            "features": [
                "metrics_monitoring",
                "dashboard_creation",
                "alert_management",
                "incident_visualization",
                "performance_analysis"
            ]
        }

    async def _fetch_dashboards(self, **kwargs) -> dict[str, Any]:
        """Fetch available dashboards."""
        try:
            # Use MCP if process is running
            if self.process and self.process.poll() is None:
                try:
                    result = await self._call_mcp_tool("list_dashboards", {
                        "query": kwargs.get("query", ""),
                        "folder_id": kwargs.get("folder_id"),
                        "tags": kwargs.get("tags", [])
                    })

                    # Extract dashboards from MCP response
                    if isinstance(result, dict) and "content" in result:
                        for content in result["content"]:
                            if content.get("type") == "resource" and "resource" in content:
                                resource = content["resource"]
                                if "dashboards" in resource:
                                    dashboards = resource["dashboards"]
                                    return {
                                        "dashboards": dashboards,
                                        "count": len(dashboards) if isinstance(dashboards, list) else 0
                                    }

                    return {"dashboards": [], "count": 0}

                except Exception as e:
                    self.logger.warning(f"MCP call failed, falling back to direct API: {e}")

            # Fall back to direct API
            if not self.client:
                raise ConnectionError("Client not initialized")

            response = await self.client.get("/api/search?type=dash-db")
            response.raise_for_status()
            dashboards = response.json()

            return {
                "dashboards": dashboards,
                "count": len(dashboards) if isinstance(dashboards, list) else 0
            }
        except Exception as e:
            self.logger.error(f"Failed to fetch dashboards: {e}")
            return {"error": str(e)}

    async def _fetch_metrics(self, query: str = "", **kwargs) -> dict[str, Any]:
        """Fetch metrics data."""
        try:
            # Use MCP if process is running
            if self.process and self.process.poll() is None:
                try:
                    result = await self._call_mcp_tool("query_metrics", {
                        "query": query,
                        "start": kwargs.get("start", "-1h"),
                        "end": kwargs.get("end", "now"),
                        "step": kwargs.get("step", "15s")
                    })

                    # Extract metrics from MCP response
                    if isinstance(result, dict) and "content" in result:
                        for content in result["content"]:
                            if content.get("type") == "resource" and "resource" in content:
                                resource = content["resource"]
                                if "metrics" in resource:
                                    return resource["metrics"]

                    return {}

                except Exception as e:
                    self.logger.warning(f"MCP call failed, falling back to direct API: {e}")

            # Fall back to direct API
            if not self.client:
                raise ConnectionError("Client not initialized")

            params = {
                "query": query,
                "start": kwargs.get("start", "-1h"),
                "end": kwargs.get("end", "now"),
                "step": kwargs.get("step", "15s")
            }

            # Direct Prometheus query through Grafana
            response = await self.client.get("/api/datasources/proxy/1/api/v1/query_range", params=params)

            response.raise_for_status()
            return response.json()
        except Exception as e:
            self.logger.error(f"Failed to fetch metrics: {e}")
            return {"error": str(e)}

    async def _fetch_alerts(self, **kwargs) -> dict[str, Any]:
        """Fetch current alerts."""
        try:
            # Use MCP if process is running
            if self.process and self.process.poll() is None:
                try:
                    result = await self._call_mcp_tool("list_alerts", {
                        "state": kwargs.get("state", "")
                    })

                    # Extract alerts from MCP response
                    if isinstance(result, dict) and "content" in result:
                        for content in result["content"]:
                            if content.get("type") == "resource" and "resource" in content:
                                resource = content["resource"]
                                if "alerts" in resource:
                                    return {"alerts": resource["alerts"]}

                    return {"alerts": []}

                except Exception as e:
                    self.logger.warning(f"MCP call failed, falling back to direct API: {e}")

            # Fall back to direct API
            if not self.client:
                raise ConnectionError("Client not initialized")

            response = await self.client.get("/api/alerts")

            response.raise_for_status()
            return response.json()
        except Exception as e:
            self.logger.error(f"Failed to fetch alerts: {e}")
            return {"error": str(e)}

    async def _fetch_datasources(self, **kwargs) -> dict[str, Any]:
        """Fetch available data sources."""
        try:
            if not self.client:
                raise ConnectionError("Client not initialized")

            if self.server_url in str(self.client.base_url):
                response = await self.client.get("/datasources")
            else:
                response = await self.client.get("/api/datasources")

            response.raise_for_status()
            return response.json()
        except Exception as e:
            self.logger.error(f"Failed to fetch datasources: {e}")
            return {"error": str(e)}

    async def _search_grafana(self, query: str = "", **kwargs) -> dict[str, Any]:
        """Search Grafana for dashboards, panels, etc."""
        try:
            if not self.client:
                raise ConnectionError("Client not initialized")

            params = {"q": query}

            if self.server_url in str(self.client.base_url):
                response = await self.client.get("/search", params=params)
            else:
                response = await self.client.get("/api/search", params=params)

            response.raise_for_status()
            return response.json()
        except Exception as e:
            self.logger.error(f"Failed to search Grafana: {e}")
            return {"error": str(e)}

    async def _create_dashboard(self, **params) -> dict[str, Any]:
        """Create a new dashboard."""
        try:
            if not self.client:
                raise ConnectionError("Client not initialized")

            dashboard_data = params.get("dashboard", {})

            if self.server_url in str(self.client.base_url):
                response = await self.client.post("/dashboard", json=dashboard_data)
            else:
                response = await self.client.post("/api/dashboards/db", json={"dashboard": dashboard_data})

            response.raise_for_status()
            return response.json()
        except Exception as e:
            self.logger.error(f"Failed to create dashboard: {e}")
            return {"error": str(e)}

    async def _update_dashboard(self, **params) -> dict[str, Any]:
        """Update an existing dashboard."""
        return await self._create_dashboard(**params)  # Same endpoint in Grafana

    async def _create_alert(self, **params) -> dict[str, Any]:
        """Create an alert rule."""
        try:
            if not self.client:
                raise ConnectionError("Client not initialized")

            alert_data = params.get("alert", {})

            if self.server_url in str(self.client.base_url):
                response = await self.client.post("/alert", json=alert_data)
            else:
                response = await self.client.post("/api/alert-notifications", json=alert_data)

            response.raise_for_status()
            return response.json()
        except Exception as e:
            self.logger.error(f"Failed to create alert: {e}")
            return {"error": str(e)}

    async def _silence_alert(self, **params) -> dict[str, Any]:
        """Silence an alert."""
        try:
            if not self.client:
                raise ConnectionError("Client not initialized")

            alert_id = params.get("alert_id")
            duration = params.get("duration", "1h")

            silence_data = {
                "matchers": [{"name": "alertname", "value": alert_id}],
                "startsAt": datetime.now().isoformat(),
                "endsAt": (datetime.now()).isoformat(),  # Would calculate end time
                "comment": params.get("comment", "Silenced by oncall agent")
            }

            if self.server_url in str(self.client.base_url):
                response = await self.client.post("/silence", json=silence_data)
            else:
                response = await self.client.post("/api/alertmanager/grafana/api/v1/silences", json=silence_data)

            response.raise_for_status()
            return response.json()
        except Exception as e:
            self.logger.error(f"Failed to silence alert: {e}")
            return {"error": str(e)}

    async def _query_metrics(self, **params) -> dict[str, Any]:
        """Query specific metrics."""
        return await self._fetch_metrics(**params)

    async def get_incident_metrics(self, service_name: str, time_range: str = "-1h") -> dict[str, Any]:
        """Get relevant metrics for an incident."""
        try:
            # Common metrics queries for incident analysis
            metrics_queries = [
                f'up{{job="{service_name}"}}',  # Service uptime
                f'rate(http_requests_total{{service="{service_name}"}}[5m])',  # Request rate
                f'rate(http_requests_total{{service="{service_name}",status=~"5.."}},5m])',  # Error rate
                f'histogram_quantile(0.95, rate(http_request_duration_seconds_bucket{{service="{service_name}"}}[5m]))',  # Latency
                f'process_resident_memory_bytes{{job="{service_name}"}}',  # Memory usage
                f'rate(process_cpu_seconds_total{{job="{service_name}"}}[5m])'  # CPU usage
            ]

            results = {}
            for query in metrics_queries:
                try:
                    result = await self._fetch_metrics(query=query, start=time_range)
                    if "error" not in result:
                        metric_name = query.split('{')[0]  # Extract metric name
                        results[metric_name] = result
                except Exception as e:
                    self.logger.warning(f"Failed to query metric {query}: {e}")

            return {
                "service": service_name,
                "time_range": time_range,
                "metrics": results,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            self.logger.error(f"Failed to get incident metrics: {e}")
            return {"error": str(e)}

    def _generate_message_id(self) -> int:
        """Generate a unique message ID for MCP communication."""
        if not hasattr(self, '_message_counter'):
            self._message_counter = 2  # Start from 2 since we used 1 and 2 for init
        else:
            self._message_counter += 1
        return self._message_counter
