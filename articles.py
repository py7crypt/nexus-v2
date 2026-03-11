"""
/api/articles — GET list of articles / POST create article
Vercel Python Serverless Function
"""
from http.server import BaseHTTPRequestHandler
import json
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from _utils import (
    verify_token, ArticleCreate, get_all_articles, create_article
)


def run_async(coro):
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            raise RuntimeError
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


class handler(BaseHTTPRequestHandler):

    def _send(self, status: int, body: dict):
        data = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()
        self.wfile.write(data)

    def do_OPTIONS(self):
        self._send(200, {})

    def do_GET(self):
        from urllib.parse import urlparse, parse_qs
        qs = parse_qs(urlparse(self.path).query)

        category = qs.get("category", [None])[0]
        status   = qs.get("status", ["published"])[0]
        limit    = int(qs.get("limit", [20])[0])
        offset   = int(qs.get("offset", [0])[0])

        articles, total = run_async(
            get_all_articles(category=category, status=status, limit=limit, offset=offset)
        )
        self._send(200, {"success": True, "total": total, "articles": articles})

    def do_POST(self):
        auth = self.headers.get("Authorization", "")
        if not verify_token(auth):
            self._send(401, {"success": False, "error": "Unauthorized"})
            return

        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length)) if length else {}

        if not body.get("title") or not body.get("content") or not body.get("category"):
            self._send(400, {"success": False, "error": "title, content, and category are required"})
            return

        try:
            data = ArticleCreate(**body)
            article = run_async(create_article(data))
            self._send(201, {"success": True, "article": article})
        except Exception as e:
            self._send(500, {"success": False, "error": str(e)})

    def log_message(self, *args):
        pass  # suppress default logging
