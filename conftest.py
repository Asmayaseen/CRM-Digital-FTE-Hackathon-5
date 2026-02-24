"""
conftest.py — pytest configuration for the full project.
Ensures PYTHONPATH includes the project root so all imports resolve.
"""
import sys
import os

# Add project root to sys.path
sys.path.insert(0, os.path.dirname(__file__))
