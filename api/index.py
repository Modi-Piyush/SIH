import sys
import os

# Ensure the root project directory is on the python search path
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from app.main import app

# Vercel ASGI handler - exposes `app` for Vercel's Python runtime
# The `app` object is the FastAPI ASGI application
# Vercel will call app(scope, receive, send) with the full original path
