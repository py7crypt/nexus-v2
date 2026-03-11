"""
Debug endpoint.
GET /api/debug              → env + KV health + article list
GET /api/debug?id=UUID      → look up one article
GET /api/debug?cleanup=1    → fix corrupt {"value":"uuid"} IDs in KV
"""
import sys, os, json, asyncio
sys.path.insert(0, os.path.dirname(__file__))
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from _utils import _has_kv, _upstash, kv_get, kv_lrange, kv_lrem, kv_lpush, ADMIN_SECRET, verify_token, _parse_article

def _run(c):
    loop = asyncio.new_event_loop()
    r = loop.run_until_complete(c)
    loop.close()
    return r

class handler(BaseHTTPRequestHandler):
    def _json(self, code, body):
        data = json.dumps(body, indent=2).encode()
        self.send_response(code)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        qs         = parse_qs(urlparse(self.path).query)
        article_id = qs.get("id",      [None])[0]
        cleanup    = qs.get("cleanup", [None])[0]

        kv_url   = os.environ.get("KV_REST_API_URL", "")
        kv_token = os.environ.get("KV_REST_API_TOKEN", "")

        result = {
            "self_path":  self.path,
            "env": {
                "KV_REST_API_URL":   (kv_url[:40] + "...") if len(kv_url) > 40 else (kv_url or "NOT SET"),
                "KV_REST_API_TOKEN": "SET ✓" if kv_token else "NOT SET ✗",
                "ADMIN_SECRET":      "SET ✓" if os.environ.get("ADMIN_SECRET") else "NOT SET ✗",
            },
            "admin_secret_value": ADMIN_SECRET,
            "auth_valid":    verify_token(self.headers.get("Authorization", "")),
            "kv_configured": _has_kv(),
        }

        if _has_kv():
            result["kv_write"]   = _upstash("SET", "nexus:debug:test", "ok")
            result["kv_read"]    = _upstash("GET", "nexus:debug:test")
            result["kv_working"] = result["kv_read"] == "ok"

            raw_ids = _run(kv_lrange("article:ids", 0, -1))
            corrupt = [x for x in raw_ids if x.startswith("{")]
            clean   = [x for x in raw_ids if not x.startswith("{")]
            result["article_ids"]    = raw_ids
            result["corrupt_count"]  = len(corrupt)

            if cleanup and corrupt:
                fixed = []
                for bad in corrupt:
                    try:
                        real_id = json.loads(bad).get("value", "")
                        if real_id:
                            _run(kv_lrem("article:ids", bad))
                            _run(kv_lpush("article:ids", real_id))
                            fixed.append({"removed": bad, "added": real_id})
                    except Exception as e:
                        fixed.append({"error": str(e), "entry": bad})
                result["cleanup_result"] = fixed
                result["cleanup_done"]   = True

            if article_id:
                key = f"article:{article_id}"
                raw = _upstash("GET", key)
                a   = _parse_article(raw)
                result["lookup"] = {
                    "key":    key,
                    "found":  raw is not None,
                    "parsed": a is not None,
                    "title":  a.get("title") if a else None,
                }

        self._json(200, result)

    def log_message(self, *a): pass
