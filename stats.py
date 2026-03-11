"""
/api/stats — GET dashboard statistics
Vercel Python Serverless Function
"""
from http.server import BaseHTTPRequestHandler
import json
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from _utils import verify_token, get_all_articles


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
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()
        self.wfile.write(data)

    def do_OPTIONS(self):
        self._send(200, {})

    def do_GET(self):
        auth = self.headers.get("Authorization", "")
        if not verify_token(auth):
            self._send(401, {"success": False, "error": "Unauthorized"})
            return

        async def fetch_stats():
            articles, _ = await get_all_articles(status="all", limit=1000)
            published    = [a for a in articles if a.get("status") == "published"]
            drafts       = [a for a in articles if a.get("status") == "draft"]
            total_views  = sum(a.get("views", 0) for a in articles)

            by_cat = {}
            for a in articles:
                cat = a.get("category", "Other")
                by_cat[cat] = by_cat.get(cat, 0) + 1

            recent = sorted(articles, key=lambda a: a.get("created_at", ""), reverse=True)[:5]
            recent = [
                {k: a[k] for k in ("id","title","category","status","created_at","views") if k in a}
                for a in recent
            ]

            return {
                "total": len(articles),
                "published": len(published),
                "drafts": len(drafts),
                "total_views": total_views,
                "by_category": by_cat,
                "recent": recent,
            }

        try:
            stats = run_async(fetch_stats())
            self._send(200, {"success": True, "stats": stats})
        except Exception as e:
            self._send(500, {"success": False, "error": str(e)})

    def log_message(self, *args):
        pass
