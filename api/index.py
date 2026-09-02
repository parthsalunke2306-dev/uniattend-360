"""
Vercel Serverless Function Entrypoint for UniAttend 360 FastAPI Backend.
Exports 'app' for the Vercel ASGI runtime handler.
"""

import os
import sys

# Ensure root directory is on Python path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from api.server import app
