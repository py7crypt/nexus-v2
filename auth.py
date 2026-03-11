"""
/api/auth — POST login, returns token
"""
from http.server import BaseHTTPRequestHandler
import json
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from _utils import verify_password, ADMIN_SECRET


class handler(BaseHTTPRequestHandler):

    def _send(self, status: int, body: dict):
        data = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()
        self.wfile.write(data)

    def do_OPTIONS(self):
        self._send(200, {})

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length)) if length else {}

        username = body.get("username", "")
        password = body.get("password", "")

        if not verify_password(username, password):
            self._send(401, {"success": False, "error": "Invalid credentials"})
            return

        self._send(200, {
            "success": True,
            "token": ADMIN_SECRET,
            "user": {"username": username, "role": "admin"}
        })

    def log_message(self, *args):
        pass
