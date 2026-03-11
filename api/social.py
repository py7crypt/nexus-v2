import sys, os, json, asyncio
sys.path.insert(0, os.path.dirname(__file__))
from _utils import verify_token, kv_get, kv_set
from http.server import BaseHTTPRequestHandler

KV_KEY = "nexus:social"

def _run(c):
    loop = asyncio.new_event_loop()
    r = loop.run_until_complete(c)
    loop.close()
    return r

async def _get():
    raw = await kv_get(KV_KEY)
    if raw:
        try:
            data = json.loads(raw) if isinstance(raw, str) else raw
            # New format: list of {id, platform, label, url}
            if isinstance(data, list):
                return data
            # Migrate old flat dict format
            if isinstance(data, dict):
                ICONS = {"twitter":"𝕏","facebook":"📘","instagram":"📸","linkedin":"💼",
                         "youtube":"▶️","tiktok":"🎵"}
                return [
                    {"id": k, "platform": k, "label": k.capitalize(),
                     "icon": ICONS.get(k, "🔗"), "url": v}
                    for k, v in data.items() if v
                ]
        except Exception:
            pass
    return []

class handler(BaseHTTPRequestHandler):
    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type,Authorization")

    def _json(self, code, body):
        data = json.dumps(body).encode()
        self.send_response(code)
        self._cors()
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(data)

    def do_OPTIONS(self): self._json(200, {})

    def do_GET(self):
        links = _run(_get())
        self._json(200, {"success": True, "links": links})

    def do_POST(self):
        if not verify_token(self.headers.get("Authorization", "")):
            return self._json(401, {"success": False, "error": "Unauthorized"})
        n = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(n)) if n else {}
        links = body.get("links", [])
        # Validate each entry
        cleaned = []
        for item in links:
            if isinstance(item, dict) and item.get("url", "").strip():
                cleaned.append({
                    "id":       str(item.get("id", "")).strip(),
                    "platform": str(item.get("platform", "custom")).strip().lower(),
                    "label":    str(item.get("label", "")).strip(),
                    "icon":     str(item.get("icon", "🔗")).strip(),
                    "url":      str(item.get("url", "")).strip(),
                })
        _run(kv_set(KV_KEY, json.dumps(cleaned)))
        self._json(200, {"success": True, "links": cleaned})

    def log_message(self, *a): pass
