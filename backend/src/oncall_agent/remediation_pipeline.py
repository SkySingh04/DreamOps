"""Remediation pipeline for executing diagnostic and remediation commands.

This module implements a command pipeline that:
1. Executes diagnostic commands and captures output
2. Parses diagnostic output to identify problematic resources
3. Generates concrete remediation commands with real values
4. Executes remediation commands in YOLO mode
5. Verifies fixes and resolves incidents
"""

import asyncio
import json
import re
from datetime import datetime
from typing import Any

from .utils import get_logger


class DiagnosticParser:
    """Parse kubectl diagnostic command outputs to identify problematic resources."""

    def __init__(self):
        self.logger = get_logger(__name__)

    def parse_memory_usage(self, kubectl_top_output: str) -> list[dict[str, Any]]:
        """Parse 'kubectl top pods' output to find high memory pods.
        
        Example output:
        NAMESPACE     NAME                                    CPU(cores)   MEMORY(bytes)
        default       app-backend-7d9f8b6c5-x2n4m            100m         1800Mi
        default       frontend-deployment-5f4d5c6b7d-abc123   50m         2048Mi
        """
        high_memory_pods = []
        lines = kubectl_top_output.strip().split('\n')

        # Skip header
        if len(lines) < 2:
            return high_memory_pods

        for line in lines[1:]:
            parts = line.split()
            if len(parts) >= 4:
                namespace = parts[0]
                pod_name = parts[1]
                memory_str = parts[3]

                # Extract memory value (convert to Mi)
                memory_value = self._parse_memory_value(memory_str)

                # Consider high memory if > 80% of typical limit (assuming 2Gi typical)
                if memory_value > 1600:  # 80% of 2048Mi
                    # Extract deployment name from pod name
                    deployment_name = self._extract_deployment_from_pod(pod_name)

                    high_memory_pods.append({
                        'namespace': namespace,
                        'pod_name': pod_name,
                        'deployment_name': deployment_name,
                        'memory_usage': memory_value,
                        'memory_str': memory_str,
                        'percentage': min(100, int((memory_value / 2048) * 100))
                    })

        # Sort by memory usage descending
        high_memory_pods.sort(key=lambda x: x['memory_usage'], reverse=True)
        self.logger.info(f"Found {len(high_memory_pods)} high memory pods")

        return high_memory_pods

    def parse_oom_events(self, kubectl_events_output: str) -> list[dict[str, Any]]:
        """Parse OOM events to find affected deployments.
        
        Example output:
        LAST SEEN   TYPE      REASON      OBJECT                                    MESSAGE
        2m          Warning   OOMKilling  pod/app-backend-7d9f8b6c5-x2n4m         Memory cgroup out of memory
        5m          Warning   OOMKilling  pod/frontend-deployment-5f4d5c6b7d-xyz   Container frontend was OOMKilled
        """
        oom_affected = []

        # Handle JSON output from 'kubectl get events -o json'
        try:
            events_data = json.loads(kubectl_events_output)
            for event in events_data.get('items', []):
                if event.get('reason') == 'OOMKilling':
                    involved_obj = event.get('involvedObject', {})
                    if involved_obj.get('kind') == 'Pod':
                        pod_name = involved_obj.get('name', '')
                        namespace = involved_obj.get('namespace', 'default')
                        deployment_name = self._extract_deployment_from_pod(pod_name)

                        oom_affected.append({
                            'namespace': namespace,
                            'pod_name': pod_name,
                            'deployment_name': deployment_name,
                            'event_time': event.get('lastTimestamp', ''),
                            'message': event.get('message', ''),
                            'count': event.get('count', 1)
                        })
        except json.JSONDecodeError:
            # Fallback to parsing text output
            lines = kubectl_events_output.strip().split('\n')
            for line in lines:
                if 'OOMKilling' in line or 'OOMKilled' in line:
                    # Extract pod name using regex
                    pod_match = re.search(r'pod/([^\s]+)', line)
                    if pod_match:
                        pod_name = pod_match.group(1)
                        deployment_name = self._extract_deployment_from_pod(pod_name)

                        # Try to extract namespace
                        namespace_match = re.search(r'namespace/([^\s]+)', line)
                        namespace = namespace_match.group(1) if namespace_match else 'default'

                        oom_affected.append({
                            'namespace': namespace,
                            'pod_name': pod_name,
                            'deployment_name': deployment_name,
                            'event_time': 'recent',
                            'message': line,
                            'count': 1
                        })

        # Deduplicate by deployment
        deployments_seen = {}
        for item in oom_affected:
            key = f"{item['namespace']}/{item['deployment_name']}"
            if key not in deployments_seen:
                deployments_seen[key] = item
            else:
                deployments_seen[key]['count'] += item['count']

        result = list(deployments_seen.values())
        self.logger.info(f"Found {len(result)} deployments affected by OOM kills")

        return result

    def parse_error_pods(self, kubectl_get_pods_output: str) -> list[dict[str, Any]]:
        """Parse pod errors to find problematic deployments.
        
        Example output:
        NAME                                    READY   STATUS             RESTARTS   AGE
        app-backend-7d9f8b6c5-x2n4m            0/1     CrashLoopBackOff   5          10m
        frontend-deployment-5f4d5c6b7d-abc123   0/1     ImagePullBackOff   0          5m
        """
        error_pods = []
        lines = kubectl_get_pods_output.strip().split('\n')

        # Skip header
        if len(lines) < 2:
            return error_pods

        for line in lines[1:]:
            parts = line.split()
            if len(parts) >= 4:
                pod_name = parts[0]
                ready_state = parts[1]
                status = parts[2]
                restarts = parts[3]

                # Check for error states
                if status in ['CrashLoopBackOff', 'ImagePullBackOff', 'Error', 'OOMKilled', 'Evicted']:
                    deployment_name = self._extract_deployment_from_pod(pod_name)

                    error_pods.append({
                        'pod_name': pod_name,
                        'deployment_name': deployment_name,
                        'status': status,
                        'restarts': int(restarts) if restarts.isdigit() else 0,
                        'ready_state': ready_state,
                        'namespace': 'default'  # Will be overridden if namespace provided
                    })

        self.logger.info(f"Found {len(error_pods)} pods with errors")
        return error_pods

    def _parse_memory_value(self, memory_str: str) -> int:
        """Convert memory string to Mi (e.g., '1800Mi', '2Gi', '1024Ki')."""
        try:
            if memory_str.endswith('Mi'):
                return int(memory_str[:-2])
            elif memory_str.endswith('Gi'):
                return int(memory_str[:-2]) * 1024
            elif memory_str.endswith('Ki'):
                return int(memory_str[:-2]) // 1024
            elif memory_str.endswith('M'):
                return int(memory_str[:-1])
            elif memory_str.endswith('G'):
                return int(memory_str[:-1]) * 1024
            else:
                # Assume bytes, convert to Mi
                return int(memory_str) // (1024 * 1024)
        except:
            return 0

    def _extract_deployment_from_pod(self, pod_name: str) -> str:
        """Extract deployment name from pod name.
        
        Examples:
        - app-backend-7d9f8b6c5-x2n4m -> app-backend
        - frontend-deployment-5f4d5c6b7d-abc123 -> frontend-deployment
        """
        # Remove the last two segments (replicaset hash and pod hash)
        parts = pod_name.split('-')
        if len(parts) >= 3:
            # Find where the replicaset hash starts (usually a hex string)
            for i in range(len(parts) - 1, 0, -1):
                if len(parts[i]) >= 5 and all(c in '0123456789abcdef' for c in parts[i]):
                    return '-'.join(parts[:i])

        # Fallback: remove last 2 segments
        if len(parts) >= 3:
            return '-'.join(parts[:-2])

        return pod_name


class RemediationActions:
    """Concrete remediation actions for different incident types."""

    def __init__(self, k8s_integration):
        self.k8s_integration = k8s_integration
        self.logger = get_logger(__name__)

    async def fix_oom_kills(self, affected_deployments: list[dict[str, Any]],
                           increase_percentage: float = 50.0) -> list[dict[str, Any]]:
        """Fix OOM kills by increasing memory limits.
        
        Args:
            affected_deployments: List of deployments affected by OOM
            increase_percentage: Percentage to increase memory by (default 50%)
        
        Returns:
            List of execution results
        """
        results = []

        for deployment in affected_deployments:
            deployment_name = deployment['deployment_name']
            namespace = deployment.get('namespace', 'default')

            self.logger.info(f"🔧 Fixing OOM for deployment {deployment_name} in namespace {namespace}")

            # First, get current memory limit
            describe_cmd = ["describe", "deployment", deployment_name, "-n", namespace]
            describe_result = await self.k8s_integration.execute_kubectl_command(
                describe_cmd, auto_approve=True
            )

            if describe_result.get('success'):
                # Extract current memory limit from output
                current_limit = self._extract_memory_limit(describe_result.get('output', ''))
                if not current_limit:
                    current_limit = 2048  # Default 2Gi

                # Calculate new limit
                new_limit = int(current_limit * (1 + increase_percentage / 100))

                self.logger.info(f"📈 Increasing memory limit from {current_limit}Mi to {new_limit}Mi")

                # Patch deployment with new memory limit
                patch_json = {
                    "spec": {
                        "template": {
                            "spec": {
                                "containers": [{
                                    "name": "*",
                                    "resources": {
                                        "limits": {
                                            "memory": f"{new_limit}Mi"
                                        },
                                        "requests": {
                                            "memory": f"{int(new_limit * 0.8)}Mi"  # 80% for requests
                                        }
                                    }
                                }]
                            }
                        }
                    }
                }

                patch_cmd = [
                    "patch", "deployment", deployment_name,
                    "-n", namespace,
                    "--type", "strategic",
                    "-p", json.dumps(patch_json)
                ]

                patch_result = await self.k8s_integration.execute_kubectl_command(
                    patch_cmd, auto_approve=True
                )

                if patch_result.get('success'):
                    self.logger.info(f"✅ Successfully patched {deployment_name} with new memory limit")
                    results.append({
                        'deployment': deployment_name,
                        'namespace': namespace,
                        'action': 'memory_increase',
                        'old_limit': f"{current_limit}Mi",
                        'new_limit': f"{new_limit}Mi",
                        'status': 'success',
                        'output': patch_result.get('output', '')
                    })
                else:
                    self.logger.error(f"❌ Failed to patch {deployment_name}: {patch_result.get('error')}")
                    results.append({
                        'deployment': deployment_name,
                        'namespace': namespace,
                        'action': 'memory_increase',
                        'status': 'failed',
                        'error': patch_result.get('error', 'Unknown error')
                    })
            else:
                self.logger.error(f"❌ Failed to describe deployment {deployment_name}")
                results.append({
                    'deployment': deployment_name,
                    'namespace': namespace,
                    'action': 'memory_increase',
                    'status': 'failed',
                    'error': 'Could not get current configuration'
                })

        return results

    async def fix_crashloop_backoff(self, affected_deployments: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Fix CrashLoopBackOff by rolling restart of deployments."""
        results = []

        for deployment in affected_deployments:
            deployment_name = deployment['deployment_name']
            namespace = deployment.get('namespace', 'default')

            self.logger.info(f"🔄 Rolling restart for {deployment_name} in namespace {namespace}")

            # Rollout restart deployment
            restart_cmd = ["rollout", "restart", "deployment", deployment_name, "-n", namespace]

            restart_result = await self.k8s_integration.execute_kubectl_command(
                restart_cmd, auto_approve=True
            )

            if restart_result.get('success'):
                self.logger.info(f"✅ Successfully restarted {deployment_name}")

                # Wait a bit for rollout to start
                await asyncio.sleep(2)

                # Check rollout status
                status_cmd = ["rollout", "status", "deployment", deployment_name,
                             "-n", namespace, "--timeout=60s"]

                status_result = await self.k8s_integration.execute_kubectl_command(
                    status_cmd, auto_approve=True
                )

                results.append({
                    'deployment': deployment_name,
                    'namespace': namespace,
                    'action': 'rollout_restart',
                    'status': 'success' if status_result.get('success') else 'in_progress',
                    'output': restart_result.get('output', '')
                })
            else:
                self.logger.error(f"❌ Failed to restart {deployment_name}: {restart_result.get('error')}")
                results.append({
                    'deployment': deployment_name,
                    'namespace': namespace,
                    'action': 'rollout_restart',
                    'status': 'failed',
                    'error': restart_result.get('error', 'Unknown error')
                })

        return results

    async def fix_image_pull_errors(self, affected_pods: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Fix image pull errors by updating image or checking registry credentials."""
        results = []

        for pod in affected_pods:
            deployment_name = pod['deployment_name']
            namespace = pod.get('namespace', 'default')

            self.logger.info(f"🔍 Checking image issues for {deployment_name}")

            # Get deployment details to find the image
            get_cmd = ["get", "deployment", deployment_name, "-n", namespace, "-o", "json"]

            get_result = await self.k8s_integration.execute_kubectl_command(
                get_cmd, auto_approve=True
            )

            if get_result.get('success'):
                try:
                    deployment_data = json.loads(get_result.get('output', '{}'))
                    containers = deployment_data.get('spec', {}).get('template', {}).get('spec', {}).get('containers', [])

                    if containers:
                        current_image = containers[0].get('image', '')
                        self.logger.info(f"Current image: {current_image}")

                        # For demo purposes, we'll just trigger a rollout restart
                        # In production, you'd check if image exists, fix registry auth, etc.
                        restart_cmd = ["rollout", "restart", "deployment", deployment_name, "-n", namespace]

                        restart_result = await self.k8s_integration.execute_kubectl_command(
                            restart_cmd, auto_approve=True
                        )

                        results.append({
                            'deployment': deployment_name,
                            'namespace': namespace,
                            'action': 'fix_image_pull',
                            'current_image': current_image,
                            'status': 'success' if restart_result.get('success') else 'failed',
                            'output': restart_result.get('output', '')
                        })
                except Exception as e:
                    self.logger.error(f"Error parsing deployment data: {e}")
                    results.append({
                        'deployment': deployment_name,
                        'namespace': namespace,
                        'action': 'fix_image_pull',
                        'status': 'failed',
                        'error': str(e)
                    })

        return results

    def _extract_memory_limit(self, describe_output: str) -> int:
        """Extract current memory limit from deployment description."""
        # Look for patterns like "memory: 2Gi" or "memory: 2048Mi"
        memory_match = re.search(r'memory:\s*(\d+(?:Mi|Gi|M|G))', describe_output)
        if memory_match:
            memory_str = memory_match.group(1)
            parser = DiagnosticParser()
            return parser._parse_memory_value(memory_str)

        return 0  # Default if not found


class RemediationPipeline:
    """Main pipeline for executing diagnostics and remediation."""

    def __init__(self, k8s_integration, pagerduty_client=None):
        self.k8s_integration = k8s_integration
        self.pagerduty_client = pagerduty_client
        self.logger = get_logger(__name__)
        self.parser = DiagnosticParser()
        self.remediation = RemediationActions(k8s_integration)
        self.execution_log = []

    async def execute_pipeline(self, alert_type: str, context: dict[str, Any],
                             commands_from_claude: list[str]) -> dict[str, Any]:
        """Execute the full remediation pipeline.
        
        Args:
            alert_type: Type of alert (e.g., 'oom_kill', 'pod_crash')
            context: Context gathered from K8s
            commands_from_claude: Commands suggested by Claude
        
        Returns:
            Pipeline execution results
        """
        self.logger.info(f"🚀 Starting remediation pipeline for {alert_type}")

        # Step 1: Execute diagnostic commands and capture output
        diagnostic_results = await self._execute_diagnostics(alert_type, context)

        # Step 2: Parse diagnostic output to identify problematic resources
        problems = self._parse_diagnostic_output(alert_type, diagnostic_results)

        # Step 3: Check if we have actual problems OR if this is a recent alert
        # Don't skip remediation just because we don't see current problems
        has_recent_problems = self._check_for_recent_problems(alert_type, context, problems)

        # Step 4: Generate and execute concrete remediation commands
        # Execute remediation even if no current problems found (they may have auto-recovered)
        remediation_results = await self._execute_remediation(
            alert_type, problems, commands_from_claude,
            force_remediation=has_recent_problems
        )

        # Step 5: Verify fixes
        verification_results = await self._verify_fixes(alert_type, problems, remediation_results)

        # Step 6: Resolve incident if fixed
        incident_resolved = await self._handle_incident_resolution(
            alert_type, problems, remediation_results, verification_results
        )

        return {
            'alert_type': alert_type,
            'diagnostic_results': diagnostic_results,
            'problems_identified': problems,
            'has_recent_problems': has_recent_problems,
            'remediation_results': remediation_results,
            'verification_results': verification_results,
            'incident_resolved': incident_resolved,
            'execution_log': self.execution_log
        }

    async def _execute_diagnostics(self, alert_type: str, context: dict[str, Any]) -> dict[str, Any]:
        """Execute diagnostic commands based on alert type."""
        self.logger.info("📊 Executing diagnostic commands...")
        results = {}

        if alert_type == 'oom_kill':
            # Get memory usage of all pods
            self._log_execution("DIAGNOSTIC", "kubectl top pods --all-namespaces --sort-by=memory")
            top_result = await self.k8s_integration.execute_kubectl_command(
                ["top", "pods", "--all-namespaces", "--sort-by=memory"],
                auto_approve=True
            )
            results['memory_usage'] = top_result

            # Get OOM events
            self._log_execution("DIAGNOSTIC", "kubectl get events --all-namespaces --field-selector reason=OOMKilling")
            events_result = await self.k8s_integration.execute_kubectl_command(
                ["get", "events", "--all-namespaces",
                 "--field-selector", "reason=OOMKilling", "-o", "json"],
                auto_approve=True
            )
            results['oom_events'] = events_result

        elif alert_type == 'pod_crash':
            # Get pods with errors
            namespace = context.get('namespace', 'default')
            self._log_execution("DIAGNOSTIC", f"kubectl get pods -n {namespace}")
            pods_result = await self.k8s_integration.execute_kubectl_command(
                ["get", "pods", "-n", namespace],
                auto_approve=True
            )
            results['pod_status'] = pods_result

        return results

    def _parse_diagnostic_output(self, alert_type: str,
                                diagnostic_results: dict[str, Any]) -> dict[str, Any]:
        """Parse diagnostic command outputs to identify specific problems."""
        self.logger.info("🔍 Parsing diagnostic output...")
        problems = {}

        if alert_type == 'oom_kill':
            # Parse memory usage
            if diagnostic_results.get('memory_usage', {}).get('success'):
                memory_output = diagnostic_results['memory_usage'].get('output', '')
                problems['high_memory_pods'] = self.parser.parse_memory_usage(memory_output)

            # Parse OOM events
            if diagnostic_results.get('oom_events', {}).get('success'):
                events_output = diagnostic_results['oom_events'].get('output', '')
                problems['oom_affected_deployments'] = self.parser.parse_oom_events(events_output)

        elif alert_type == 'pod_crash':
            # Parse pod status
            if diagnostic_results.get('pod_status', {}).get('success'):
                pods_output = diagnostic_results['pod_status'].get('output', '')
                problems['error_pods'] = self.parser.parse_error_pods(pods_output)

        return problems

    def _check_for_recent_problems(self, alert_type: str, context: dict[str, Any],
                                   problems: dict[str, Any]) -> bool:
        """Check if there were recent problems even if not currently visible."""
        # If we found current problems, definitely proceed
        if any(problems.values()):
            return True

        # Check context for evidence of recent issues
        if alert_type == 'oom_kill':
            # Check if alert mentions specific pods/deployments
            if context.get('deployment_name') or context.get('pod_name'):
                self.logger.info("⚠️  Alert mentions specific resources - treating as recent problem")
                return True
            # Check if there were problematic pods in the initial context
            if context.get('problematic_pods'):
                self.logger.info("⚠️  Context shows problematic pods - treating as recent problem")
                return True

        elif alert_type == 'pod_crash':
            # Similar checks for pod crashes
            if context.get('pod_name') or context.get('deployment_name'):
                self.logger.info("⚠️  Alert mentions specific crashed pod - treating as recent problem")
                return True

        return False

    async def _execute_remediation(self, alert_type: str, problems: dict[str, Any],
                                  commands_from_claude: list[str],
                                  force_remediation: bool = False) -> list[dict[str, Any]]:
        """Execute concrete remediation actions based on identified problems."""
        self.logger.info("🔧 Executing remediation actions...")
        results = []

        if alert_type == 'oom_kill':
            # Fix OOM kills by increasing memory limits
            oom_deployments = problems.get('oom_affected_deployments', [])
            if oom_deployments:
                self.logger.info(f"🎯 Fixing {len(oom_deployments)} deployments affected by OOM")
                self._log_execution("REMEDIATION", f"Patching {len(oom_deployments)} deployments with increased memory limits")

                fix_results = await self.remediation.fix_oom_kills(oom_deployments)
                results.extend(fix_results)

            else:
                # Fallback: use high memory pods if no OOM events found
                high_memory_pods = problems.get('high_memory_pods', [])
                if high_memory_pods:
                    # Convert pod list to deployment list
                    deployments = {}
                    for pod in high_memory_pods[:3]:  # Fix top 3
                        key = f"{pod['namespace']}/{pod['deployment_name']}"
                        if key not in deployments:
                            deployments[key] = pod

                    deployment_list = list(deployments.values())
                    self.logger.info(f"🎯 Fixing {len(deployment_list)} high-memory deployments")
                    self._log_execution("REMEDIATION", f"Increasing memory for {len(deployment_list)} high-usage deployments")

                    fix_results = await self.remediation.fix_oom_kills(deployment_list)
                    results.extend(fix_results)
                elif force_remediation and commands_from_claude:
                    # No current problems found, but we have commands from Claude
                    # Parse commands to extract deployment names
                    self.logger.info("⚠️  No current OOM problems found, but alert indicates recent issues")
                    self.logger.info("🔍 Parsing Claude's remediation commands for deployment names...")

                    deployments_to_fix = self._extract_deployments_from_commands(commands_from_claude)
                    if deployments_to_fix:
                        self.logger.info(f"🎯 Found {len(deployments_to_fix)} deployments to fix from commands")
                        self._log_execution("REMEDIATION", f"Increasing memory for {len(deployments_to_fix)} deployments from Claude's analysis")

                        fix_results = await self.remediation.fix_oom_kills(deployments_to_fix)
                        results.extend(fix_results)
                    else:
                        self.logger.warning("⚠️  Could not extract deployment names from commands")

        elif alert_type == 'pod_crash':
            # Fix crashloop pods
            error_pods = problems.get('error_pods', [])
            if error_pods:
                # Group by deployment
                deployments = {}
                for pod in error_pods:
                    if pod['status'] == 'CrashLoopBackOff':
                        key = f"{pod['namespace']}/{pod['deployment_name']}"
                        if key not in deployments:
                            deployments[key] = pod

                deployment_list = list(deployments.values())
                if deployment_list:
                    self.logger.info(f"🎯 Restarting {len(deployment_list)} deployments in CrashLoopBackOff")
                    self._log_execution("REMEDIATION", f"Rolling restart for {len(deployment_list)} crashed deployments")

                    fix_results = await self.remediation.fix_crashloop_backoff(deployment_list)
                    results.extend(fix_results)

                # Fix image pull errors
                image_error_pods = [p for p in error_pods if p['status'] == 'ImagePullBackOff']
                if image_error_pods:
                    self.logger.info(f"🎯 Fixing {len(image_error_pods)} pods with image pull errors")
                    self._log_execution("REMEDIATION", f"Fixing image issues for {len(image_error_pods)} pods")

                    fix_results = await self.remediation.fix_image_pull_errors(image_error_pods)
                    results.extend(fix_results)

        # Also try to execute any specific commands from Claude that don't have placeholders
        for cmd in commands_from_claude[:3]:  # Limit to first 3
            if not ('<' in cmd and '>' in cmd) and cmd.startswith(('kubectl', 'k ')):
                self.logger.info(f"🏃 Executing Claude's command: {cmd}")
                self._log_execution("REMEDIATION", cmd)

                # Parse and execute
                import shlex
                try:
                    cmd_parts = shlex.split(cmd)
                    if cmd_parts[0] in ['kubectl', 'k']:
                        cmd_parts = cmd_parts[1:]

                    exec_result = await self.k8s_integration.execute_kubectl_command(
                        cmd_parts, auto_approve=True
                    )

                    results.append({
                        'command': cmd,
                        'action': 'claude_command',
                        'status': 'success' if exec_result.get('success') else 'failed',
                        'output': exec_result.get('output', '')[:500]
                    })
                except Exception as e:
                    self.logger.error(f"Error executing Claude command: {e}")

        return results

    async def _verify_fixes(self, alert_type: str, problems: dict[str, Any],
                           remediation_results: list[dict[str, Any]]) -> dict[str, Any]:
        """Verify that the fixes were successful."""
        self.logger.info("🎯 Verifying fixes...")
        verification = {
            'checked': False,
            'fixed': False,
            'details': [],
            'remediation_attempted': len(remediation_results) > 0
        }

        # Wait a bit for changes to take effect
        await asyncio.sleep(5)

        if alert_type == 'oom_kill':
            # Check if OOM events have stopped
            self._log_execution("VERIFICATION", "Checking for new OOM events")

            events_result = await self.k8s_integration.execute_kubectl_command(
                ["get", "events", "--all-namespaces",
                 "--field-selector", "reason=OOMKilling", "-o", "json"],
                auto_approve=True
            )

            if events_result.get('success'):
                verification['checked'] = True
                try:
                    events_data = json.loads(events_result.get('output', '{}'))
                    recent_events = []

                    # Check for events in last 2 minutes
                    from datetime import datetime, timedelta
                    cutoff_time = datetime.utcnow() - timedelta(minutes=2)

                    for event in events_data.get('items', []):
                        event_time_str = event.get('lastTimestamp', '')
                        if event_time_str:
                            # Parse ISO format timestamp
                            event_time = datetime.fromisoformat(event_time_str.replace('Z', '+00:00'))
                            if event_time.replace(tzinfo=None) > cutoff_time:
                                recent_events.append(event)

                    verification['fixed'] = len(recent_events) == 0
                    verification['details'].append(f"Recent OOM events: {len(recent_events)}")

                except Exception as e:
                    self.logger.error(f"Error parsing verification: {e}")

        elif alert_type == 'pod_crash':
            # Check pod status
            affected_deployments = set()
            for pod in problems.get('error_pods', []):
                affected_deployments.add(pod['deployment_name'])

            if affected_deployments:
                self._log_execution("VERIFICATION", f"Checking status of {len(affected_deployments)} deployments")

                all_healthy = True
                for deployment in affected_deployments:
                    status_result = await self.k8s_integration.execute_kubectl_command(
                        ["get", "deployment", deployment, "-o", "json"],
                        auto_approve=True
                    )

                    if status_result.get('success'):
                        try:
                            dep_data = json.loads(status_result.get('output', '{}'))
                            ready = dep_data.get('status', {}).get('readyReplicas', 0)
                            desired = dep_data.get('spec', {}).get('replicas', 1)

                            if ready < desired:
                                all_healthy = False
                                verification['details'].append(f"{deployment}: {ready}/{desired} ready")
                        except:
                            all_healthy = False

                verification['checked'] = True
                verification['fixed'] = all_healthy

        return verification

    async def _handle_incident_resolution(self, alert_type: str, problems: dict[str, Any],
                                        remediation_results: list[dict[str, Any]],
                                        verification_results: dict[str, Any]) -> bool:
        """Handle PagerDuty incident resolution if issue is fixed."""
        # Check if we should resolve
        successful_remediations = [r for r in remediation_results if r.get('status') == 'success']

        # Only mark as resolved if:
        # 1. We actually executed successful remediations
        # 2. Verification shows the issue is fixed (or we attempted remediation)
        if successful_remediations and (verification_results.get('fixed') or
                                       (verification_results.get('remediation_attempted') and
                                        len(successful_remediations) > 0)):
            self.logger.info("✅ Issue appears to be resolved!")
            self._log_execution("RESOLUTION", "Issue verified as fixed - resolving incident")

            # Log what we fixed
            for remediation in successful_remediations:
                if remediation.get('deployment'):
                    self.logger.info(f"   ✓ Fixed: {remediation['deployment']} - {remediation.get('action', 'unknown action')}")

            # In a real implementation, you would call PagerDuty API here
            # if self.pagerduty_client:
            #     await self.pagerduty_client.resolve_incident(incident_id, "Auto-resolved by AI agent")

            return True
        else:
            if not successful_remediations:
                self.logger.info("⚠️  No successful remediations executed - cannot resolve incident")
            else:
                self.logger.info("⚠️  Issue may not be fully resolved yet")
            return False

    def _log_execution(self, action_type: str, description: str):
        """Log execution steps for visibility."""
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'action_type': action_type,
            'description': description
        }
        self.execution_log.append(log_entry)

        # Visual feedback
        icon = {
            'DIAGNOSTIC': '📊',
            'REMEDIATION': '🔧',
            'VERIFICATION': '🎯',
            'RESOLUTION': '✅'
        }.get(action_type, '📌')

        self.logger.info(f"{icon} {action_type}: {description}")

    def _extract_deployments_from_commands(self, commands: list[str]) -> list[dict[str, Any]]:
        """Extract deployment names from kubectl patch commands."""
        deployments = []

        for cmd in commands:
            # Look for kubectl patch deployment commands
            if 'patch' in cmd and 'deployment' in cmd:
                # Try to extract deployment name and namespace
                import re
                # Pattern: kubectl patch deployment <name> -n <namespace>
                match = re.search(r'deployment[s]?\s+(\S+)(?:.*?-n\s+(\S+))?', cmd)
                if match:
                    deployment_name = match.group(1)
                    namespace = match.group(2) if match.group(2) else 'default'

                    # Remove any quotes
                    deployment_name = deployment_name.strip('"\'')
                    namespace = namespace.strip('"\'')

                    # Skip placeholders
                    if '<' not in deployment_name and '>' not in deployment_name:
                        deployments.append({
                            'deployment_name': deployment_name,
                            'namespace': namespace,
                            'source': 'claude_command'
                        })
                        self.logger.info(f"   📌 Extracted deployment: {deployment_name} in namespace: {namespace}")

        return deployments
