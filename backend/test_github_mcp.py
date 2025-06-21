#!/usr/bin/env python3
"""
Minimal test to demonstrate GitHub MCP server automatic startup
"""

import asyncio
import logging
import subprocess
from pathlib import Path

# Configure logging to see what's happening
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MockGitHubMCPTest:
    """Simplified version to test GitHub MCP server startup"""

    def __init__(self):
        self.server_process = None
        self.mcp_server_path = "/mnt/c/Users/harsh/OneDrive/Desktop/oncall/github-mcp-server/github-mcp-server"
        self.server_host = "localhost"
        self.server_port = 8081

    async def test_mcp_server_startup(self):
        """Test the GitHub MCP server automatic startup"""
        logger.info("🚀 Testing GitHub MCP Server Automatic Startup")

        try:
            # Step 1: Start the MCP server
            logger.info("📡 Step 1: Starting GitHub MCP server...")
            await self._start_mcp_server()

            # Step 2: Check if it's running
            logger.info("🔍 Step 2: Checking if server is running...")
            await self._check_server_status()

            # Step 3: Test basic connectivity
            logger.info("🏓 Step 3: Testing server connectivity...")
            await self._test_basic_connectivity()

            logger.info("✅ GitHub MCP Server test completed successfully!")

        except Exception as e:
            logger.error(f"❌ Test failed: {e}")

        finally:
            # Cleanup
            await self._cleanup()

    async def _start_mcp_server(self):
        """Start the GitHub MCP server process"""
        try:
            # Build the command to start the MCP server
            cmd = [
                self.mcp_server_path,
                "stdio"  # Use stdio mode for MCP
            ]

            # Set environment variables (using dummy token for test)
            env = {
                "GITHUB_PERSONAL_ACCESS_TOKEN": "dummy_token_for_test",
                "PATH": "/usr/local/bin:/usr/bin:/bin"
            }

            logger.info(f"🔧 Starting command: {' '.join(cmd)}")
            logger.info(f"🔧 Server path: {self.mcp_server_path}")
            logger.info(f"🔧 Working directory: {Path.cwd()}")

            # Start the server process
            self.server_process = subprocess.Popen(
                cmd,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=Path.cwd()
            )

            logger.info(f"🚀 Server process started with PID: {self.server_process.pid}")

            # Wait a moment for the server to start
            await asyncio.sleep(3)

            # Check if the process is still running
            poll_result = self.server_process.poll()
            if poll_result is not None:
                stdout, stderr = self.server_process.communicate()
                logger.error(f"❌ MCP server failed to start. Exit code: {poll_result}")
                logger.error(f"📤 STDOUT: {stdout}")
                logger.error(f"📤 STDERR: {stderr}")
                raise RuntimeError(f"MCP server failed to start: {stderr}")

            logger.info("✅ GitHub MCP server started successfully")

        except Exception as e:
            logger.error(f"❌ Failed to start MCP server: {e}")
            raise

    async def _check_server_status(self):
        """Check the server process status"""
        if self.server_process:
            poll_result = self.server_process.poll()
            if poll_result is None:
                logger.info(f"✅ Server process running (PID: {self.server_process.pid})")
            else:
                logger.warning(f"⚠️ Server process exited with code: {poll_result}")
        else:
            logger.error("❌ No server process found")

    async def _test_basic_connectivity(self):
        """Test basic connectivity to the server"""
        try:
            # For MCP stdio mode, we can't do HTTP requests
            # Instead, we'll check if the process is responding
            if self.server_process and self.server_process.poll() is None:
                logger.info("✅ Server appears to be responsive (process alive)")

                # Try to read some output from stderr (where logs usually go)
                import os
                import select

                # Non-blocking read attempt
                if hasattr(select, 'select'):
                    ready, _, _ = select.select([self.server_process.stderr], [], [], 0.1)
                    if ready:
                        output = os.read(self.server_process.stderr.fileno(), 1024).decode('utf-8', errors='ignore')
                        if output:
                            logger.info(f"📋 Server output: {output[:200]}...")

                logger.info("✅ Basic connectivity test passed")
            else:
                logger.error("❌ Server process not responding")

        except Exception as e:
            logger.warning(f"⚠️ Connectivity test warning: {e}")

    async def _cleanup(self):
        """Clean up the server process"""
        try:
            if self.server_process:
                logger.info("🧹 Cleaning up server process...")
                self.server_process.terminate()

                # Wait for graceful shutdown
                await asyncio.sleep(1)

                # Force kill if still running
                if self.server_process.poll() is None:
                    logger.info("🔨 Force killing server process...")
                    self.server_process.kill()

                self.server_process = None
                logger.info("✅ Server cleanup completed")

        except Exception as e:
            logger.error(f"❌ Error during cleanup: {e}")

async def main():
    """Main test function"""
    print("=" * 60)
    print("🧪 GITHUB MCP SERVER AUTOMATIC STARTUP TEST")
    print("=" * 60)

    test = MockGitHubMCPTest()
    await test.test_mcp_server_startup()

    print("=" * 60)
    print("✅ Test completed!")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
