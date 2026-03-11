"""
GET  /api/likes?id=ARTICLE_ID  → { likes: N }
POST /api/likes  {id}          → increments like count, returns { likes: N }
"""
import sys, os, json, asyncio
sys.path.insert(0, os.path.dirname(__file__))
from _utils import kv_get, kv_set
from urllib.parse import urlparse, parse_qs
from http.server import BaseHTTPRequestHandler

def _run(c):
    loop = asyncio.new_event_loop()
    r = loop.run_until_complete(c)
    loop.close()
    return r

async def _get_likes(article_id):
    raw = await kv_get(f"likes:{article_id}")
    try: return int(raw) if raw else 0
    except Exception: return 0

class handler(BaseHTTPRequestHandler):
    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _json(self, code, body):
        data = json.dumps(body).encode()
        self.send_response(code)
        self._cors()
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(data)

    def do_OPTIONS(self): self._json(200, {})

    def do_GET(self):
        qs = parse_qs(urlparse(self.path).query)
        article_id = qs.get("id", [None])[0]
        if not article_id:
            return self._json(400, {"success": False, "error": "id required"})
        self._json(200, {"success": True, "likes": _run(_get_likes(article_id))})

    def do_POST(self):
        # Public — no auth needed
        n = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(n)) if n else {}
        article_id = str(body.get("id", "")).strip()
        if not article_id:
            return self._json(400, {"success": False, "error": "id required"})
        new_count = _run(_get_likes(article_id)) + 1
        _run(kv_set(f"likes:{article_id}", str(new_count)))
        self._json(200, {"success": True, "likes": new_count})

    def log_message(self, *a): pass
