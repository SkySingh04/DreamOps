#!/usr/bin/env python3
"""
Demo: GitHub MCP Server Automatic Startup Flow
This demonstrates how the GitHub MCP server starts automatically in the oncall agent.
"""

import asyncio
import logging
import os
import subprocess

# Configure detailed logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class GitHubMCPStartupDemo:
    """Demonstrates the automatic GitHub MCP server startup process"""

    def __init__(self):
        self.server_process = None
        self.mcp_server_path = "/mnt/c/Users/harsh/OneDrive/Desktop/oncall/github-mcp-server/github-mcp-server"

    async def demonstrate_startup_flow(self):
        """Demonstrate the complete startup flow"""
        print("\n" + "="*70)
        print("🚀 GITHUB MCP SERVER AUTOMATIC STARTUP DEMONSTRATION")
        print("="*70)

        try:
            # Step 1: Check binary availability
            logger.info("📋 Step 1: Checking GitHub MCP server binary...")
            self._check_binary()

            # Step 2: Show what happens without token
            logger.info("⚠️  Step 2: Demonstrating startup without GitHub token...")
            await self._demo_startup_without_token()

            # Step 3: Show what happens with dummy token
            logger.info("🔑 Step 3: Demonstrating startup with dummy token...")
            await self._demo_startup_with_dummy_token()

            # Step 4: Show actual integration flow
            logger.info("🤖 Step 4: Showing how oncall agent would use it...")
            self._show_integration_flow()

            logger.info("✅ Demonstration completed!")

        except Exception as e:
            logger.error(f"❌ Demo failed: {e}")

        finally:
            await self._cleanup()

    def _check_binary(self):
        """Check if the GitHub MCP server binary is available"""
        if os.path.exists(self.mcp_server_path):
            logger.info(f"✅ GitHub MCP server binary found: {self.mcp_server_path}")

            # Check if it's executable
            if os.access(self.mcp_server_path, os.X_OK):
                logger.info("✅ Binary is executable")
            else:
                logger.warning("⚠️ Binary may not be executable")

            # Get file size
            size = os.path.getsize(self.mcp_server_path)
            logger.info(f"📦 Binary size: {size:,} bytes ({size/1024/1024:.1f} MB)")
        else:
            raise FileNotFoundError(f"GitHub MCP server binary not found at {self.mcp_server_path}")

    async def _demo_startup_without_token(self):
        """Show what happens when starting without GitHub token"""
        logger.info("🧪 Testing startup without GITHUB_PERSONAL_ACCESS_TOKEN...")

        try:
            # Start without token
            process = subprocess.Popen(
                [self.mcp_server_path, "stdio"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            # Wait briefly and check result
            await asyncio.sleep(1)
            stdout, stderr = process.communicate(timeout=2)

            logger.info(f"❌ Expected failure - Exit code: {process.returncode}")
            if stderr:
                logger.info(f"📤 Error message: {stderr.strip()}")

        except subprocess.TimeoutExpired:
            process.kill()
            logger.info("⏰ Process timed out (as expected)")
        except Exception as e:
            logger.info(f"❌ Error (as expected): {e}")

    async def _demo_startup_with_dummy_token(self):
        """Show startup with a dummy token"""
        logger.info("🧪 Testing startup with dummy GITHUB_PERSONAL_ACCESS_TOKEN...")

        try:
            # Set dummy token environment
            env = os.environ.copy()
            env["GITHUB_PERSONAL_ACCESS_TOKEN"] = "ghp_dummy_token_for_demo_1234567890abcdef"

            # Start the process
            process = subprocess.Popen(
                [self.mcp_server_path, "stdio"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=env
            )

            logger.info(f"🚀 Server started with PID: {process.pid}")
            logger.info("⏳ Server is running... (waiting 3 seconds)")

            # Wait and check if it's still running
            await asyncio.sleep(3)

            if process.poll() is None:
                logger.info("✅ Server is still running - ready to accept MCP requests!")
                logger.info("📡 At this point, the oncall agent would:")
                logger.info("   - Send MCP initialization messages")
                logger.info("   - List available tools")
                logger.info("   - Make GitHub API calls via MCP protocol")

                # Simulate sending an MCP message
                logger.info("📨 Simulating MCP communication...")
                try:
                    # Send a simple MCP initialize message
                    init_message = '{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "oncall-agent", "version": "1.0.0"}}}\n'

                    process.stdin.write(init_message)
                    process.stdin.flush()

                    # Try to read response (with timeout)
                    logger.info("⏳ Waiting for MCP response...")
                    await asyncio.sleep(2)

                except Exception as e:
                    logger.info(f"📨 MCP communication demo: {e}")

            else:
                stdout, stderr = process.communicate()
                logger.info(f"❌ Server exited with code: {process.returncode}")
                if stdout:
                    logger.info(f"📤 STDOUT: {stdout[:200]}...")
                if stderr:
                    logger.info(f"📤 STDERR: {stderr[:200]}...")

            # Clean up
            if process.poll() is None:
                process.terminate()
                await asyncio.sleep(1)
                if process.poll() is None:
                    process.kill()
                logger.info("🧹 Server process cleaned up")

        except Exception as e:
            logger.error(f"❌ Demo error: {e}")

    def _show_integration_flow(self):
        """Show how the oncall agent integration works"""
        logger.info("🤖 How the Oncall Agent Integration Works:")
        print("\n" + "-"*50)
        print("INTEGRATION FLOW:")
        print("-"*50)
        print("1. 🚀 Agent starts with --github-integration flag")
        print("2. 🔧 GitHubMCPIntegration.connect() method called")
        print("3. 📡 Subprocess starts: github-mcp-server stdio")
        print("4. 🔑 GITHUB_PERSONAL_ACCESS_TOKEN passed via env")
        print("5. ⏳ Agent waits 2 seconds for server startup")
        print("6. 🏓 Health check performed (MCP ping)")
        print("7. ✅ Connection established - ready for use!")
        print("8. 📊 During alert processing:")
        print("   - Fetch recent commits via MCP")
        print("   - Get GitHub Actions status via MCP")
        print("   - Create incident issues via MCP")
        print("   - Search code for error patterns via MCP")
        print("9. 🧹 On shutdown: server process terminated")
        print("-"*50)

        logger.info("📋 Configuration needed in .env file:")
        print("   GITHUB_TOKEN=your_github_personal_access_token")
        print("   GITHUB_MCP_SERVER_PATH=../github-mcp-server/github-mcp-server")
        print("   GITHUB_MCP_HOST=localhost")
        print("   GITHUB_MCP_PORT=8081")

        logger.info("🧪 Test command:")
        print("   uv run python simulate_pagerduty_alert.py pod_crash --github-integration")

    async def _cleanup(self):
        """Clean up any running processes"""
        if self.server_process and self.server_process.poll() is None:
            self.server_process.terminate()
            await asyncio.sleep(1)
            if self.server_process.poll() is None:
                self.server_process.kill()

async def demonstrate_real_world_scenario():
    """Show what a real alert scenario would look like"""
    print("\n" + "="*70)
    print("🎯 REAL-WORLD ALERT SCENARIO WITH GITHUB MCP")
    print("="*70)

    print("🚨 SCENARIO: Pod CrashLoopBackOff Alert")
    print("-"*40)
    print("1. 📦 EKS pod crashes due to missing config")
    print("2. 📟 PagerDuty alert triggered")
    print("3. 🤖 Oncall agent receives alert")
    print("4. 🚀 GitHub MCP server auto-starts")
    print("5. 🔍 Agent queries GitHub via MCP:")
    print("   - Recent commits to affected service")
    print("   - GitHub Actions deployment status")
    print("   - Search for config-related issues")
    print("   - Check if similar issues exist")
    print("6. 🧠 Claude AI analyzes all context")
    print("7. 📝 Agent creates GitHub issue via MCP")
    print("8. 💡 Suggests remediation steps")
    print("9. 📊 Updates incident documentation")
    print("10. 🧹 GitHub MCP server shuts down")

    print("\n💡 Key Benefits:")
    print("✅ Automatic server management - no manual setup")
    print("✅ Full GitHub API access via MCP protocol")
    print("✅ Contextual code analysis for better diagnosis")
    print("✅ Automated issue tracking and documentation")
    print("✅ Clean resource management")

async def main():
    """Run the demonstration"""
    demo = GitHubMCPStartupDemo()

    await demo.demonstrate_startup_flow()
    await demonstrate_real_world_scenario()

    print("\n" + "="*70)
    print("🎉 DEMONSTRATION COMPLETE!")
    print("="*70)
    print("💡 Key Takeaway: GitHub MCP server starts automatically")
    print("   when the oncall agent runs with GitHub integration!")
    print("="*70)

if __name__ == "__main__":
    asyncio.run(main())
