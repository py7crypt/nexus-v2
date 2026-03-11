import sys, os, json, asyncio
# _utils.py is copied into this directory for Vercel bundling
sys.path.insert(0, os.path.dirname(__file__))
from _utils import verify_token, get_all_articles, kv_get, kv_set, kv_del, kv_lrem, ARTICLE_FIELDS, _parse_article
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

def _run(c):
    loop = asyncio.new_event_loop()
    r = loop.run_until_complete(c)
    loop.close()
    return r

def _get_id(path):
    """
    Vercel injects the [id] param in two ways:
    1. As ?id=UUID in the query string (file-based routing)
    2. As the last segment of self.path
    Try both.
    """
    parsed = urlparse(path)
    qs = parse_qs(parsed.query)

    # Method 1: Vercel query param injection
    if qs.get("id"):
        return qs["id"][0]

    # Method 2: last path segment
    segment = parsed.path.rstrip("/").split("/")[-1]
    # Ignore if it's literally "[id]" (rewrite didn't substitute)
    if segment and segment != "[id]":
        return segment

    return None

def _clean_id(raw_id):
    """Handle corrupt {"value": "uuid"} entries."""
    if raw_id and raw_id.startswith("{"):
        try:
            return json.loads(raw_id).get("value", raw_id)
        except Exception:
            pass
    return raw_id

def _load_article(article_id):
    if not article_id:
        return None

    article_id = _clean_id(article_id)

    # Fast path: direct KV key lookup
    raw = _run(kv_get(f"article:{article_id}"))
    a = _parse_article(raw)
    if a:
        return a

    # Fallback: scan all articles (handles slug-based URLs too)
    arts, _ = _run(get_all_articles(status="all", limit=5000))
    for art in arts:
        if art.get("id") == article_id or art.get("slug") == article_id:
            return art

    return None

class handler(BaseHTTPRequestHandler):
    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,PUT,DELETE,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type,Authorization")

    def _json(self, code, body):
        data = json.dumps(body).encode()
        self.send_response(code)
        self._cors()
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(data)

    def do_OPTIONS(self):
        self._json(200, {})

    def do_GET(self):
        article_id = _get_id(self.path)
        a = _load_article(article_id)
        if not a:
            return self._json(404, {"success": False, "error": "Article not found"})
        # Block draft articles from public access unless admin token provided
        is_admin = verify_token(self.headers.get("Authorization", ""))
        if a.get("status") != "published" and not is_admin:
            return self._json(404, {"success": False, "error": "Article not found"})
        a["views"] = a.get("views", 0) + 1
        _run(kv_set(f"article:{a['id']}", a))
        self._json(200, {"success": True, "article": a})

    def do_PUT(self):
        if not verify_token(self.headers.get("Authorization", "")):
            return self._json(401, {"success": False, "error": "Unauthorized"})
        article_id = _get_id(self.path)
        a = _load_article(article_id)
        if not a:
            return self._json(404, {"success": False, "error": "Article not found"})
        n = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(n)) if n else {}
        for k in ARTICLE_FIELDS:
            if k in body and body[k] is not None:
                a[k] = body[k]
        a["updated_at"] = datetime.now(timezone.utc).isoformat()
        _run(kv_set(f"article:{a['id']}", a))
        self._json(200, {"success": True, "article": a})

    def do_DELETE(self):
        if not verify_token(self.headers.get("Authorization", "")):
            return self._json(401, {"success": False, "error": "Unauthorized"})
        article_id = _get_id(self.path)
        a = _load_article(article_id)
        if not a:
            return self._json(404, {"success": False, "error": "Article not found"})
        _run(kv_del(f"article:{a['id']}"))
        _run(kv_lrem("article:ids", a["id"]))
        self._json(200, {"success": True, "message": "Deleted"})

    def log_message(self, *a): pass
