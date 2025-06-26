#!/usr/bin/env python3
"""
Simple database setup checker - no external dependencies required
"""

import os
from pathlib import Path

# Colors for output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
ENDC = '\033[0m'
BOLD = '\033[1m'

def check_env_file(env_name, backend_file, frontend_file):
    """Check if environment files exist and contain database URLs"""
    print(f"\n{BOLD}🔍 Checking {env_name} environment:{ENDC}")
    
    backend_path = Path('backend') / backend_file
    frontend_path = Path('frontend') / frontend_file
    
    results = {
        'backend_exists': False,
        'backend_has_db': False,
        'frontend_exists': False,
        'frontend_has_db': False,
        'db_urls': []
    }
    
    # Check backend
    if backend_path.exists():
        results['backend_exists'] = True
        print(f"  ✅ Backend: {backend_file} exists")
        
        with open(backend_path, 'r') as f:
            content = f.read()
            if 'DATABASE_URL=' in content:
                results['backend_has_db'] = True
                # Extract URL (basic extraction)
                for line in content.split('\n'):
                    if line.startswith('DATABASE_URL='):
                        url = line.split('=', 1)[1].strip()
                        if url and not url.startswith('postgresql://username:password'):
                            results['db_urls'].append(url[:50] + '...')
                        break
                print(f"  ✅ Backend: DATABASE_URL configured")
            else:
                print(f"  {RED}❌ Backend: DATABASE_URL not found{ENDC}")
    else:
        print(f"  {RED}❌ Backend: {backend_file} not found{ENDC}")
    
    # Check frontend
    if frontend_path.exists():
        results['frontend_exists'] = True
        print(f"  ✅ Frontend: {frontend_file} exists")
        
        with open(frontend_path, 'r') as f:
            content = f.read()
            if 'POSTGRES_URL=' in content:
                results['frontend_has_db'] = True
                print(f"  ✅ Frontend: POSTGRES_URL configured")
            else:
                print(f"  {RED}❌ Frontend: POSTGRES_URL not found{ENDC}")
    else:
        print(f"  {RED}❌ Frontend: {frontend_file} not found{ENDC}")
    
    return results

def main():
    print(f"{BOLD}{BLUE}🚀 DreamOps Database Setup Checker{ENDC}")
    print("=" * 50)
    
    # Change to project root
    os.chdir(Path(__file__).parent)
    
    environments = [
        ("LOCAL", ".env.local", ".env.local"),
        ("STAGING", ".env.staging", ".env.staging"),
        ("PRODUCTION", ".env.production", ".env.production")
    ]
    
    all_results = []
    
    for env_name, backend_file, frontend_file in environments:
        result = check_env_file(env_name, backend_file, frontend_file)
        all_results.append((env_name, result))
    
    # Summary
    print(f"\n{BOLD}📊 Setup Summary{ENDC}")
    print("=" * 50)
    
    ready_count = 0
    for env_name, result in all_results:
        if result['backend_exists'] and result['backend_has_db'] and result['frontend_exists'] and result['frontend_has_db']:
            print(f"{GREEN}✅ {env_name}: Fully configured{ENDC}")
            ready_count += 1
        elif result['backend_exists'] or result['frontend_exists']:
            print(f"{YELLOW}⚠️  {env_name}: Partially configured{ENDC}")
        else:
            print(f"{RED}❌ {env_name}: Not configured{ENDC}")
    
    # Next steps
    if ready_count == 0:
        print(f"\n{BOLD}📝 Next Steps:{ENDC}")
        print("1. Create a Neon account at https://neon.tech")
        print("2. Create 3 projects: local, staging, production")
        print("3. Copy the connection strings")
        print("4. Run: ./scripts/setup-neon-databases.sh")
        print("   OR manually create the .env files")
        
        print(f"\n{BOLD}🔧 Quick Start:{ENDC}")
        print("For backend:")
        print("  cp backend/.env.local.example backend/.env.local")
        print("  cp backend/.env.staging.example backend/.env.staging")
        print("  cp backend/.env.production.example backend/.env.production")
        print("\nFor frontend:")
        print("  Create frontend/.env.local with POSTGRES_URL")
        print("  Create frontend/.env.staging with POSTGRES_URL")
        print("  Create frontend/.env.production with POSTGRES_URL")
        
    elif ready_count < 3:
        print(f"\n{YELLOW}⚠️  Some environments are not fully configured{ENDC}")
        print("Complete the setup for all environments to ensure proper separation")
    else:
        print(f"\n{GREEN}🎉 All environments are configured!{ENDC}")
        print("Run the full connection tests to verify database separation")
    
    # Check for example files
    print(f"\n{BOLD}📄 Example Files Available:{ENDC}")
    example_files = [
        "backend/.env.local.example",
        "backend/.env.staging.example",
        "backend/.env.production.example"
    ]
    
    for file in example_files:
        if Path(file).exists():
            print(f"  ✅ {file}")

if __name__ == "__main__":
    main()