#!/usr/bin/env python3
"""Extract all external package imports from Python files."""

import ast
import os
import sys
from pathlib import Path
from typing import Set, List

# Standard library modules - these should be excluded
STDLIB_MODULES = {
    # Built-in modules
    'abc', 'argparse', 'array', 'ast', 'asyncio', 'atexit', 'base64', 'binascii',
    'builtins', 'calendar', 'collections', 'concurrent', 'contextlib', 'copy',
    'csv', 'ctypes', 'dataclasses', 'datetime', 'decimal', 'difflib', 'dis',
    'email', 'enum', 'errno', 'functools', 'gc', 'getopt', 'glob', 'gzip',
    'hashlib', 'heapq', 'hmac', 'html', 'http', 'importlib', 'inspect', 'io',
    'ipaddress', 'itertools', 'json', 'keyword', 'linecache', 'locale', 'logging',
    'math', 'mmap', 'multiprocessing', 'operator', 'os', 'pathlib', 'pickle',
    'platform', 'pprint', 'profile', 'queue', 'random', 're', 'secrets', 'select',
    'shlex', 'shutil', 'signal', 'socket', 'sqlite3', 'ssl', 'stat', 'statistics',
    'string', 'struct', 'subprocess', 'sys', 'tempfile', 'textwrap', 'threading',
    'time', 'timeit', 'token', 'tokenize', 'traceback', 'types', 'typing',
    'typing_extensions', 'unittest', 'urllib', 'uuid', 'warnings', 'weakref',
    'xml', 'zipfile', 'zlib',
    # Common sub-modules
    'urllib.parse', 'urllib.request', 'concurrent.futures', 'collections.abc',
    'multiprocessing.pool', 'xml.etree', 'xml.etree.ElementTree',
}

def extract_imports_from_file(filepath: Path) -> Set[str]:
    """Extract all import statements from a Python file."""
    imports = set()
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        tree = ast.parse(content)
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    module = alias.name.split('.')[0]
                    if module not in STDLIB_MODULES and not module.startswith('oncall_agent'):
                        imports.add(module)
            
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    module = node.module.split('.')[0]
                    if module not in STDLIB_MODULES and not module.startswith('oncall_agent'):
                        imports.add(module)
    
    except Exception as e:
        print(f"Error parsing {filepath}: {e}", file=sys.stderr)
    
    return imports

def main():
    backend_dir = Path("/mnt/c/Users/incha/oncall-agent/backend")
    all_imports = set()
    
    # Get all Python files
    python_files = []
    for root, dirs, files in os.walk(backend_dir):
        # Skip virtual environment
        if '.venv' in root or '__pycache__' in root:
            continue
        
        for file in files:
            if file.endswith('.py'):
                python_files.append(Path(root) / file)
    
    print(f"Scanning {len(python_files)} Python files...\n")
    
    # Extract imports from each file
    for filepath in sorted(python_files):
        imports = extract_imports_from_file(filepath)
        if imports:
            relative_path = filepath.relative_to(backend_dir)
            print(f"\n{relative_path}:")
            for imp in sorted(imports):
                print(f"  - {imp}")
            all_imports.update(imports)
    
    # Print summary
    print("\n" + "="*80)
    print("SUMMARY: All external packages found:")
    print("="*80)
    for package in sorted(all_imports):
        print(f"  {package}")
    
    print(f"\nTotal unique external packages: {len(all_imports)}")

if __name__ == "__main__":
    main()