"""Test environment isolation for secure application settings."""

import os


os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("AI_SERVER_API_KEY", "dev-key-please-change-in-env")
