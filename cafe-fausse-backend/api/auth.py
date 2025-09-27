import os
from flask import request

def _get_admin_token() -> str:
    expected = (os.getenv("ADMIN_TOKEN") or "").strip()
    if expected:
        return expected

    # Fallback: load from backend .env if not in process env
    try:
        from pathlib import Path
        from dotenv import dotenv_values
        root = Path(__file__).resolve().parents[1]  # .../api -> backend root
        env_path = root / ".env"
        if env_path.exists():
            maybe = (dotenv_values(str(env_path)).get("ADMIN_TOKEN") or "").strip()
            if maybe:
                return maybe
    except Exception:
        pass
    return ""

def check_admin() -> bool:
    expected = _get_admin_token()
    if not expected:
        return False
    auth = request.headers.get("Authorization", "").strip()
    if not auth.startswith("Bearer "):
        return False
    return auth[7:] == expected
