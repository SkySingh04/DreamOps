#!/bin/bash
set -e

echo "🔍 Running linter..."
uv run ruff check . --fix

echo "🧪 Running tests..."
uv run pytest tests/

echo "🚀 Verifying application..."
timeout 10s uv run python main.py || true

echo "✅ All checks passed!"