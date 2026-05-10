#!/usr/bin/env python
"""
Setup Verification Script for DementiaNext Model Integration
Run this to verify your environment is ready for model integration
"""

import os
import sys
import json
from pathlib import Path

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'

def check(condition, message, critical=False):
    """Print a check result"""
    status = f"{Colors.GREEN}✓{Colors.END}" if condition else f"{Colors.RED}✗{Colors.END}"
    severity = f" {Colors.RED}[CRITICAL]{Colors.END}" if critical and not condition else ""
    print(f"{status} {message}{severity}")
    return condition

def main():
    print(f"\n{Colors.BLUE}=== DementiaNext Model Integration Verification ==={Colors.END}\n")
    
    checks_passed = 0
    checks_failed = 0
    
    # Check Python
    print(f"{Colors.BLUE}Python Environment:{Colors.END}")
    if check(sys.version_info >= (3, 8), "Python 3.8+", critical=True):
        checks_passed += 1
    else:
        checks_failed += 1
    
    # Check Backend Structure
    print(f"\n{Colors.BLUE}Backend Structure:{Colors.END}")
    backend_checks = [
        ("backend/models/", "Models directory"),
        ("backend/detection/", "Detection app"),
        ("backend/detection/models.py", "Detection models"),
        ("backend/detection/views.py", "Detection views"),
        ("backend/detection/serializers.py", "Serializers"),
        ("backend/detection/urls.py", "URL routing"),
    ]
    
    for path, desc in backend_checks:
        full_path = Path("backend") / path if not path.endswith("/") else Path("backend") / path
        exists = full_path.exists()
        if check(exists, desc, critical=True):
            checks_passed += 1
        else:
            checks_failed += 1
    
    # Check Model File
    print(f"\n{Colors.BLUE}Model File:{Colors.END}")
    model_path = Path("backend/models/dementia_detector.pth")
    if check(model_path.exists(), "dementia_detector.pth exists", critical=True):
        size_mb = model_path.stat().st_size / (1024*1024)
        check(size_mb > 50, f"  └─ File size valid ({size_mb:.1f} MB)", critical=True)
        checks_passed += 1
    else:
        checks_failed += 1
    
    # Check Frontend
    print(f"\n{Colors.BLUE}Frontend Structure:{Colors.END}")
    frontend_checks = [
        ("frontend/package.json", "package.json"),
        ("frontend/app/detection/page.tsx", "Detection page"),
    ]
    
    for path, desc in frontend_checks:
        full_path = Path(path)
        exists = full_path.exists()
        if check(exists, desc):
            checks_passed += 1
        else:
            checks_failed += 1
    
    # Check Python Dependencies (if in venv)
    print(f"\n{Colors.BLUE}Python Dependencies:{Colors.END}")
    try:
        import django
        check(True, f"Django {django.VERSION[0]}.{django.VERSION[1]}", critical=True)
        checks_passed += 1
    except ImportError:
        check(False, "Django not installed", critical=True)
        checks_failed += 1
    
    try:
        import torch
        check(True, f"PyTorch {torch.__version__}", critical=True)
        checks_passed += 1
    except ImportError:
        check(False, "PyTorch not installed", critical=True)
        checks_failed += 1
    
    try:
        import torchvision
        check(True, f"TorchVision {torchvision.__version__}")
        checks_passed += 1
    except ImportError:
        check(False, "TorchVision not installed")
    
    try:
        from PIL import Image
        check(True, "Pillow (PIL)")
        checks_passed += 1
    except ImportError:
        check(False, "Pillow not installed")
        checks_failed += 1
    
    # Check Database
    print(f"\n{Colors.BLUE}Database:{Colors.END}")
    try:
        import psycopg2
        from dotenv import load_dotenv
        # Be flexibile in case run from inside backend/ or run from project root
        env_path = ".env" if Path(".env").exists() else "backend/.env"
        load_dotenv(env_path)
        
        conn = psycopg2.connect(
            database=os.environ.get("DB_NAME", "dementianext_db"),
            user=os.environ.get("DB_USER", "postgres"),
            password=os.environ.get("DB_PASSWORD", "postgres"),
            host=os.environ.get("DB_HOST", "localhost"),
            port=os.environ.get("DB_PORT", "5432")
        )
        conn.close()
        check(True, "PostgreSQL database connected")
        checks_passed += 1
    except ImportError:
        check(False, "psycopg2 not installed")
        checks_failed += 1
    except Exception as e:
        check(False, "PostgreSQL connection failed")
        print(f"  {Colors.YELLOW}ℹ{Colors.END} Error: {e}")
        print(f"  {Colors.YELLOW}ℹ{Colors.END} Verify PostgreSQL is running and credentials in .env are correct")
        checks_failed += 1
    
    # Summary
    print(f"\n{Colors.BLUE}=== Summary ==={Colors.END}")
    total = checks_passed + checks_failed
    print(f"Passed: {Colors.GREEN}{checks_passed}/{total}{Colors.END}")
    print(f"Failed: {Colors.RED if checks_failed > 0 else Colors.YELLOW}{checks_failed}/{total}{Colors.END}")
    
    if checks_failed == 0:
        print(f"\n{Colors.GREEN}✓ All checks passed! Ready for deployment.{Colors.END}\n")
        return 0
    else:
        print(f"\n{Colors.RED}✗ Some checks failed. Please fix issues above.{Colors.END}\n")
        return 1

if __name__ == "__main__":
    sys.exit(main())
