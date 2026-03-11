"""
/api/articles/[id] — GET single article, PUT update, DELETE
Vercel Python Serverless Function
"""
from http.server import BaseHTTPRequestHandler
import json
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from _utils import (
    verify_token, ArticleUpdate,
    kv_get, kv_set, kv_del, kv_lrem, get_all_articles
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
        self.send_header("Access-Control-Allow-Methods", "GET,PUT,DELETE,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()
        self.wfile.write(data)

    def _get_id(self) -> str:
        # Path: /api/articles/<id>
        parts = self.path.split("?")[0].rstrip("/").split("/")
        return parts[-1] if parts else ""

    def do_OPTIONS(self):
        self._send(200, {})

    def do_GET(self):
        article_id = self._get_id()

        async def fetch():
            raw = await kv_get(f"article:{article_id}")
            if not raw:
                # Try by slug
                all_arts, _ = await get_all_articles(status="all", limit=1000)
                for a in all_arts:
                    if a.get("slug") == article_id:
                        return a
                return None
            a = json.loads(raw) if isinstance(raw, str) else raw
            # Increment views
            a["views"] = a.get("views", 0) + 1
            await kv_set(f"article:{a['id']}", json.dumps(a))
            return a

        article = run_async(fetch())
        if not article:
            self._send(404, {"success": False, "error": "Article not found"})
            return
        self._send(200, {"success": True, "article": article})

    def do_PUT(self):
        auth = self.headers.get("Authorization", "")
        if not verify_token(auth):
            self._send(401, {"success": False, "error": "Unauthorized"})
            return

        article_id = self._get_id()
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length)) if length else {}

        async def update():
            from datetime import datetime, timezone
            raw = await kv_get(f"article:{article_id}")
            if not raw:
                return None
            existing = json.loads(raw) if isinstance(raw, str) else raw
            # Merge
            allowed = ["title", "content", "excerpt", "category", "author",
                       "tags", "status", "cover_image", "seo_title", "seo_description"]
            for field in allowed:
                if field in body and body[field] is not None:
                    existing[field] = body[field]
            existing["updated_at"] = datetime.now(timezone.utc).isoformat()
            await kv_set(f"article:{article_id}", json.dumps(existing))
            return existing

        updated = run_async(update())
        if not updated:
            self._send(404, {"success": False, "error": "Article not found"})
            return
        self._send(200, {"success": True, "article": updated})

    def do_DELETE(self):
        auth = self.headers.get("Authorization", "")
        if not verify_token(auth):
            self._send(401, {"success": False, "error": "Unauthorized"})
            return

        article_id = self._get_id()

        async def delete():
            raw = await kv_get(f"article:{article_id}")
            if not raw:
                return False
            await kv_del(f"article:{article_id}")
            await kv_lrem("article:ids", article_id)
            return True

        deleted = run_async(delete())
        if not deleted:
            self._send(404, {"success": False, "error": "Article not found"})
            return
        self._send(200, {"success": True, "message": "Article deleted"})

    def log_message(self, *args):
        pass
