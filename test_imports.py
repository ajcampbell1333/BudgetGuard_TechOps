"""
Simple test script to verify imports work (after installing dependencies)
"""

import sys
from pathlib import Path

def test_imports():
    """Test that all imports work"""
    try:
        from gui.main_window import BudgetGuardTechOpsGUI
        print("✓ GUI module imported successfully")
    except ImportError as e:
        print(f"✗ GUI import failed: {e}")
        return False
    
    try:
        from config.config_manager import ConfigManager
        print("✓ Config module imported successfully")
    except ImportError as e:
        print(f"✗ Config import failed: {e}")
        return False
    
    try:
        from utils.logger import setup_logging
        print("✓ Logger module imported successfully")
    except ImportError as e:
        print(f"✗ Logger import failed: {e}")
        return False
    
    print("\nAll imports successful! Structure is correct.")
    print("\nNext step: Install dependencies with:")
    print("  pip install -r requirements.txt")
    return True

if __name__ == '__main__':
    test_imports()

