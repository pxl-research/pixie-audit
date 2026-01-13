import os

AUDIT_DB_URL = os.getenv("AUDIT_DB_URL", "")
LOG_LEVEL = os.getenv("LOG_LEVEL", "info")
AUDIT_API_KEY = os.getenv("AUDIT_API_KEY") or None
