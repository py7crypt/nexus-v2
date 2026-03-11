import sys, os, json, asyncio
sys.path.insert(0, os.path.dirname(__file__))
from _utils import verify_token, kv_get, kv_set
from http.server import BaseHTTPRequestHandler

DEFAULT_CATEGORIES = [
    {"name": "Technology",    "color": "#1E73FF", "icon": "💻"},
    {"name": "Science",       "color": "#7C3AED", "icon": "🔬"},
    {"name": "Business",      "color": "#059669", "icon": "📈"},
    {"name": "Health",        "color": "#DC2626", "icon": "❤️"},
    {"name": "Lifestyle",     "color": "#D97706", "icon": "🌿"},
    {"name": "Travel",        "color": "#0891B2", "icon": "✈️"},
    {"name": "Entertainment", "color": "#DB2777", "icon": "🎬"},
]

KV_KEY = "nexus:categories"

def _run(c):
    loop = asyncio.new_event_loop()
    r = loop.run_until_complete(c)
    loop.close()
    return r

async def _get_cats():
    raw = await kv_get(KV_KEY)
    if raw:
        try:
            return json.loads(raw) if isinstance(raw, str) else raw
        except Exception:
            pass
    return DEFAULT_CATEGORIES

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

    def do_OPTIONS(self):
        self._json(200, {})

    def do_GET(self):
        cats = _run(_get_cats())
        self._json(200, {"success": True, "categories": cats})

    def do_POST(self):
        # Public endpoint — no auth needed so public site can read
        # But saving requires auth
        if not verify_token(self.headers.get("Authorization", "")):
            return self._json(401, {"success": False, "error": "Unauthorized"})
        n = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(n)) if n else {}
        cats = body.get("categories")
        if not isinstance(cats, list):
            return self._json(400, {"success": False, "error": "categories array required"})
        # Validate each entry
        validated = []
        for c in cats:
            if isinstance(c, dict) and c.get("name"):
                validated.append({
                    "name":  str(c["name"]).strip(),
                    "color": str(c.get("color", "#1E73FF")),
                    "icon":  str(c.get("icon",  "📰")),
                })
        _run(kv_set(KV_KEY, json.dumps(validated)))
        self._json(200, {"success": True, "categories": validated})

    def log_message(self, *a): pass
