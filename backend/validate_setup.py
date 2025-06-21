#!/usr/bin/env python3
"""
Validate the project setup and check for common issues.
"""

import os
import sys
from pathlib import Path

def check_python_syntax(file_path):
    """Check if a Python file has valid syntax."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            compile(f.read(), file_path, 'exec')
        return True, None
    except SyntaxError as e:
        return False, str(e)

def check_merge_conflicts(file_path):
    """Check if a file contains merge conflict markers."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            markers = ['<<<<<<<', '=======', '>>>>>>>']
            for marker in markers:
                if marker in content:
                    return True
        return False
    except:
        return False

def main():
    """Main validation function."""
    print("Validating Project Setup")
    print("=========================")
    print()
    
    issues = []
    
    # Check for .env file
    if not Path(".env").exists():
        issues.append("ERROR: .env file missing - copy .env.simple to .env")
    else:
        # Check if API key is set
        with open(".env", "r") as f:
            env_content = f.read()
            if "ANTHROPIC_API_KEY=sk-" not in env_content:
                issues.append("ERROR: ANTHROPIC_API_KEY not set in .env file")
            else:
                print("OK: .env file configured")
    
    # Check for merge conflicts in key files
    key_files = [
        "pyproject.toml",
        ".env.example", 
        "src/oncall_agent/config.py",
        "test_pagerduty_alerts.py"
    ]
    
    for file_path in key_files:
        if Path(file_path).exists():
            if check_merge_conflicts(file_path):
                issues.append(f"ERROR: Merge conflicts in {file_path}")
            else:
                print(f"OK: {file_path} - no merge conflicts")
        else:
            issues.append(f"ERROR: Missing file: {file_path}")
    
    # Check Python syntax for key Python files
    python_files = [
        "src/oncall_agent/config.py",
        "test_pagerduty_alerts.py", 
        "api_server.py"
    ]
    
    for file_path in python_files:
        if Path(file_path).exists():
            valid, error = check_python_syntax(file_path)
            if valid:
                print(f"OK: {file_path} - syntax OK")
            else:
                issues.append(f"ERROR: Syntax error in {file_path}: {error}")
        else:
            issues.append(f"ERROR: Missing file: {file_path}")
    
    # Check if virtual environment exists
    venv_python = Path(".venv/Scripts/python.exe")
    if venv_python.exists():
        print("OK: Virtual environment found")
    else:
        issues.append("ERROR: Virtual environment not found (.venv/Scripts/python.exe)")
    
    print()
    
    if not issues:
        print("SUCCESS: All validations passed!")
        print()
        print("You can now run tests with:")
        print("   .venv/Scripts/python.exe test_pagerduty_alerts.py --all")
        print("   OR")
        print("   .venv/Scripts/python.exe api_server.py")
        return 0
    else:
        print("WARNING: Issues found:")
        print()
        for issue in issues:
            print(f"   {issue}")
        print()
        print("Fix these issues before running tests.")
        return 1

if __name__ == "__main__":
    sys.exit(main())