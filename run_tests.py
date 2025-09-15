#!/usr/bin/env python3
"""
Test runner script for the yt-dlp wrapper project.
This script can be used to run tests without installing pytest globally.
"""

import sys
import subprocess
from pathlib import Path

def main():
    """Run the test suite."""
    project_root = Path(__file__).parent
    
    # Check if pytest is available
    try:
        import pytest
    except ImportError:
        print("❌ pytest is not installed. Installing requirements...")
        try:
            subprocess.check_call([
                sys.executable, "-m", "pip", "install", "-r", 
                str(project_root / "requirements-dev.txt")
            ])
            import pytest
        except Exception as e:
            print(f"❌ Failed to install requirements: {e}")
            print("Please run: pip install -r requirements-dev.txt")
            return 1
    
    print("🧪 Running test suite...")
    print("=" * 50)
    
    # Run pytest with the project configuration
    test_args = [
        str(project_root / "tests"),
        "-v",
        "--tb=short",
        "--color=yes"
    ]
    
    # Add any command line arguments passed to this script
    if len(sys.argv) > 1:
        test_args.extend(sys.argv[1:])
    
    try:
        exit_code = pytest.main(test_args)
        
        if exit_code == 0:
            print("\n✅ All tests passed!")
        else:
            print(f"\n❌ Tests failed with exit code: {exit_code}")
        
        return exit_code
        
    except Exception as e:
        print(f"❌ Error running tests: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
