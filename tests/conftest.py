"""Test environment isolation for secure application settings."""

import os


os.environ["APP_ENV"] = "test"
os.environ["AI_SERVER_API_KEY"] = "dev-key-please-change-in-env"
os.environ["ENABLE_MOCK_AI"] = "false"

