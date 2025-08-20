#!/usr/bin/env python3
"""
Test runner for the viu project.

This script runs all tests and provides a comprehensive test report.
"""

import sys
import unittest
import os
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def discover_and_run_tests():
    """Discover and run all tests."""
    # Set up test discovery
    test_dir = Path(__file__).parent
    loader = unittest.TestLoader()
    
    # Discover all test modules
    suite = loader.discover(
        start_dir=str(test_dir),
        pattern='test_*.py',
        top_level_dir=str(project_root)
    )
    
    # Create a test runner with verbosity
    runner = unittest.TextTestRunner(
        verbosity=2,
        failfast=False,
        buffer=True
    )
    
    print("=" * 70)
    print("VIU PROJECT TEST SUITE")
    print("=" * 70)
    print(f"Running tests from: {test_dir}")
    print(f"Project root: {project_root}")
    print("=" * 70)
    
    # Run the tests
    result = runner.run(suite)
    
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Skipped: {len(result.skipped) if hasattr(result, 'skipped') else 0}")
    
    if result.failures:
        print("\nFAILURES:")
        for test, traceback in result.failures:
            print(f"- {test}")
    
    if result.errors:
        print("\nERRORS:")
        for test, traceback in result.errors:
            print(f"- {test}")
    
    success = len(result.failures) == 0 and len(result.errors) == 0
    print(f"\nResult: {'PASSED' if success else 'FAILED'}")
    print("=" * 70)
    
    return success

def run_specific_test_module(module_name):
    """Run tests from a specific module."""
    try:
        module = __import__(f'tests.{module_name}', fromlist=[''])
        suite = unittest.TestLoader().loadTestsFromModule(module)
        runner = unittest.TextTestRunner(verbosity=2)
        result = runner.run(suite)
        return len(result.failures) == 0 and len(result.errors) == 0
    except ImportError as e:
        print(f"Error importing test module '{module_name}': {e}")
        return False

if __name__ == '__main__':
    if len(sys.argv) > 1:
        # Run specific test module
        module_name = sys.argv[1]
        success = run_specific_test_module(module_name)
    else:
        # Run all tests
        success = discover_and_run_tests()
    
    sys.exit(0 if success else 1)