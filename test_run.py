#!/usr/bin/env python3
"""Test script to check if the environment is set up correctly."""

import sys
print(f"Python version: {sys.version}")
print(f"Python executable: {sys.executable}")

try:
    import agno
    print("✓ agno is installed")
except ImportError:
    print("✗ agno is NOT installed")

try:
    import anthropic
    print("✓ anthropic is installed")
except ImportError:
    print("✗ anthropic is NOT installed")

try:
    import pydantic
    print("✓ pydantic is installed")
except ImportError:
    print("✗ pydantic is NOT installed")

try:
    import dotenv
    print("✓ python-dotenv is installed")
except ImportError:
    print("✗ python-dotenv is NOT installed")

print("\nTrying to import our modules...")
try:
    from src.oncall_agent.config import get_config
    print("✓ Can import config module")
except Exception as e:
    print(f"✗ Cannot import config module: {e}")

print("\nChecking environment variables...")
import os
api_key = os.getenv("ANTHROPIC_API_KEY")
if api_key:
    print(f"✓ ANTHROPIC_API_KEY is set (length: {len(api_key)})")
else:
    print("✗ ANTHROPIC_API_KEY is NOT set")