#!/usr/bin/env python3
"""Quick test to verify the setup works."""

import subprocess
import sys
from pathlib import Path


def test_syntax():
    """Test that all Python files have valid syntax."""
    files_to_test = [
        "src/oncall_agent/config.py",
        "test_pagerduty_alerts.py",
        "api_server.py"
    ]

    for file_path in files_to_test:
        if Path(file_path).exists():
            try:
                with open(file_path) as f:
                    compile(f.read(), file_path, 'exec')
                print(f"✓ {file_path} - syntax OK")
            except SyntaxError as e:
                print(f"✗ {file_path} - syntax error: {e}")
                return False
        else:
            print(f"✗ {file_path} - file not found")
            return False
    return True

def test_imports():
    """Test that we can import the config module."""
    try:
        # Test config import
        result = subprocess.run([
            ".venv/Scripts/python.exe", "-c",
            "from src.oncall_agent.config import get_config; print('Config import: OK')"
        ], capture_output=True, text=True, timeout=10)

        if result.returncode == 0:
            print("✓ Config module imports successfully")
            return True
        else:
            print(f"✗ Config import failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"✗ Import test failed: {e}")
        return False

def main():
    """Run quick tests."""
    print("Quick Setup Test")
    print("================")
    print()

    # Test 1: Syntax
    print("Testing Python syntax...")
    if not test_syntax():
        print("\n❌ Syntax test failed!")
        return 1

    print()

    # Test 2: Imports
    print("Testing imports...")
    if not test_imports():
        print("\n❌ Import test failed!")
        return 1

    print()
    print("✅ All tests passed!")
    print()
    print("Ready to run:")
    print("  .venv/Scripts/python.exe api_server.py")
    print("  .venv/Scripts/python.exe test_pagerduty_alerts.py --all")

    return 0

if __name__ == "__main__":
    sys.exit(main())
