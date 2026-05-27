#!/usr/bin/env python3
"""
Test script to verify core service can start with basic configuration
"""
import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Test that all core modules can be imported"""
    try:
        from config import settings
        print("✓ Configuration module imported successfully")

        from db import init_db
        print("✓ Database module imported successfully")

        from main import app
        print("✓ Main application imported successfully")

        print("All core modules imported successfully!")
        return True

    except Exception as e:
        print(f"✗ Import test failed: {e}")
        return False

def test_config_validation():
    """Test that configuration validation works"""
    try:
        from config import settings
        print("✓ Configuration validation passed")
        print(f"  Node name: {settings.node.name}")
        print(f"  Node public IP: {settings.node.public_ip}")
        return True
    except Exception as e:
        print(f"✗ Configuration validation failed: {e}")
        return False

if __name__ == "__main__":
    print("Testing core service startup components...")

    success = True
    success &= test_imports()
    success &= test_config_validation()

    if success:
        print("\n✓ Core service components are ready for Phase 2!")
    else:
        print("\n✗ Some tests failed")
        sys.exit(1)