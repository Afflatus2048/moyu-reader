"""Vercel Serverless Function entry point for MoYu Reader"""

import sys, os

# Add project root to path so we can import our modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app

# Vercel expects a WSGI app callable
handler = app