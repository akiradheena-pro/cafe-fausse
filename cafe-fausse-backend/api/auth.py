import os
from flask import request

import os
from flask import request

def _get_admin_token() -> str:
    # 1) Process environment
    expected = (os.getenv("ADMIN_TOKEN") or "").strip()
    if expected:
        return expected

    # 2) Backend .env (mounted or copied)
    try:
        from pathlib import Path
        from dotenv import dotenv_values
        root = Path(__file__).resolve().parents[1]  # /app/api -> /app
        env_path = root / ".env"
        if env_path.exists():
            maybe = (dotenv_values(str(env_path)).get("ADMIN_TOKEN") or "").strip()
            if maybe:
                return maybe
        # 3) Fallback to .env.example
        env_example = root / ".env.example"
        if env_example.exists():
            maybe = (dotenv_values(str(env_example)).get("ADMIN_TOKEN") or "").strip()
            if maybe:
                return maybe
    except Exception:
        pass

    # 4) Final default for dev
    return "dev-admin-token"

def check_admin() -> bool:
    expected = _get_admin_token()
    auth = (request.headers.get("Authorization") or "").strip()
    if not auth.startswith("Bearer "):
        return False
    return auth[7:] == expected


def check_admin() -> bool:
    expected = _get_admin_token()
    if not expected:
        return False
    auth = request.headers.get("Authorization", "").strip()
    if not auth.startswith("Bearer "):
        return False
    return auth[7:] == expected
