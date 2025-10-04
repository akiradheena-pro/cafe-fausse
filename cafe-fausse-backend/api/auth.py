import os
from flask import request
from pathlib import Path
from dotenv import dotenv_values

def _get_admin_token() -> str:

    token = os.getenv("ADMIN_TOKEN")
    if token and token.strip():
        return token.strip()

    try:
        root = Path(__file__).resolve().parents[1]
        env_path = root / ".env"
        if env_path.exists():
            env_vars = dotenv_values(str(env_path))
            token = env_vars.get("ADMIN_TOKEN")
            if token and token.strip():
                return token.strip()
    except Exception:
        pass

    return "dev-admin-token"

def check_admin() -> bool:
    """
    Checks the Authorization header for a valid admin bearer token.
    """
    expected_token = _get_admin_token()
    if not expected_token:
        return False 

    auth_header = request.headers.get("Authorization", "").strip()
    if not auth_header.lower().startswith("bearer "):
        return False

    provided_token = auth_header[7:].strip()
    return provided_token == expected_token