"""Configuration for the Socket.IO server."""
import os
from typing import List
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Server settings
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8001"))

# Security settings
API_KEY = os.getenv("TUNEUP_API_KEY")
if not API_KEY:
    raise ValueError("TUNEUP_API_KEY environment variable must be set in .env file")

# CORS settings
CORS_ORIGINS: List[str] = [
    # Local development
    "http://hassantest.tuneup.localhost:8000",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "http://localhost:3000",
    # Production domains
    "https://tuneup.sageteck.com",
    # All tenant subdomains pattern
    "https://*.tuneup.sageteck.com",
    "*"  # Allow all origins in development
] 