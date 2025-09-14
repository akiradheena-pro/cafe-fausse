from flask import jsonify

def jerror(status: int, code: str, message: str, details: str | None = None):
    payload = {"code": code, "message": message}
    if details:
        payload["details"] = details
    return jsonify(payload), status
