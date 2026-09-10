"""
Vercel Python Serverless entry point.
Exposes the FastAPI app via Mangum ASGI adapter for Vercel's Lambda-compatible runtime.
All backend source files are co-located in the api/ folder.
"""
import sys
import os

# Make api/ importable as a package so relative imports work on Vercel
sys.path.insert(0, os.path.dirname(__file__))

from app import app  # noqa: E402  (imported after sys.path fix)

# Vercel calls the module-level `app` directly as an ASGI app.
# No extra adapter needed — Vercel's Python runtime supports ASGI natively.
