#!/usr/bin/env python3
"""
Run script for LLM Adventure API
"""

import os
import sys

# Add the current directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app

if __name__ == '__main__':
    app = create_app()
    print("Starting LLM Adventure API...")
    app.run(
        host=os.getenv('HOST', '127.0.0.1'),
        port=int(os.getenv('PORT', 5000)),
        debug=True
    )