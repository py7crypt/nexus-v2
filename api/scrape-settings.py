"""
GET  /api/scrape-settings  → load scrape config
POST /api/scrape-settings  → save scrape config
Auth: Bearer required.

Config shape stored in KV key nexus:scrape-settings:
{
  "sites": [
    {
      "id":       "uuid",
      "name":     "BBC News",
      "rss_url":  "http://feeds.bbci.co.uk/news/rss.xml",
      "enabled":  true,
      "category": "Technology"   // optional default category
    }
  ],
  "google_news":    true,         // include Google News RSS
  "max_per_source": 10,           // articles per source
  "default_category": "General",
  "auto_excerpt_length": 200,
  "content_min_chars": 60        // min paragraph length to include
}
"""
import sys, os, json, uuid
sys.path.insert(0, os.path.dirname(__file__))
from _utils import verify_token, kv_get, kv_set
from http.server import BaseHTTPRequestHandler
import asyncio

KV_KEY = "nexus:scrape-settings"

DEFAULTS = {
    "sites": [
        {"id": "google-news", "name": "Google News",   "rss_url": "https://news.google.com/rss?hl=en-US&gl=US&ceid=US:en",            "enabled": True,  "category": ""},
        {"id": "bbc-news",    "name": "BBC News",       "rss_url": "http://feeds.bbci.co.uk/news/rss.xml",                             "enabled": True,  "category": ""},
        {"id": "reuters",     "name": "Reuters",        "rss_url": "https://feeds.reuters.com/reuters/topNews",                         "enabled": False, "category": ""},
        {"id": "techcrunch",  "name": "TechCrunch",     "rss_url": "https://techcrunch.com/feed/",                                      "enabled": False, "category": "Technology"},
        {"id": "theverge",    "name": "The Verge",      "rss_url": "https://www.theverge.com/rss/index.xml",                            "enabled": False, "category": "Technology"},
        {"id": "ars",         "name": "Ars Technica",   "rss_url": "http://feeds.arstechnica.com/arstechnica/index",                    "enabled": False, "category": "Technology"},
        {"id": "espn",        "name": "ESPN",            "rss_url": "https://www.espn.com/espn/rss/news",                               "enabled": False, "category": "Sports"},
        {"id": "health-nyt",  "name": "NYT Health",     "rss_url": "https://rss.nytimes.com/services/xml/rss/nyt/Health.xml",           "enabled": False, "category": "Health"},
        {"id": "sci-am",      "name": "Scientific Amer","rss_url": "http://rss.sciam.com/ScientificAmerican-Global",                    "enabled": False, "category": "Science"},
    ],
    "google_news":          True,
    "max_per_source":       10,
    "default_category":     "",
    "auto_excerpt_length":  200,
    "content_min_chars":    60,
}

def _run(c):
    loop = asyncio.new_event_loop()
    r = loop.run_until_complete(c)
    loop.close()
    return r

class handler(BaseHTTPRequestHandler):
    def _cors(self):
        self.send_header("Access-Control-Allow-Origin",  "*")
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
        if not verify_token(self.headers.get("Authorization", "")):
            return self._json(401, {"success": False, "error": "Unauthorized"})
        try:
            raw = _run(kv_get(KV_KEY))
            cfg = json.loads(raw) if raw else DEFAULTS
            # Merge any missing default keys
            for k, v in DEFAULTS.items():
                cfg.setdefault(k, v)
            self._json(200, {"success": True, "settings": cfg})
        except Exception as e:
            self._json(500, {"success": False, "error": str(e)})

    def do_POST(self):
        if not verify_token(self.headers.get("Authorization", "")):
            return self._json(401, {"success": False, "error": "Unauthorized"})
        try:
            n    = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(n)) if n else {}

            # Validate / sanitise sites
            sites = body.get("sites", [])
            clean_sites = []
            for s in sites:
                if not s.get("rss_url", "").strip():
                    continue
                clean_sites.append({
                    "id":       s.get("id") or str(uuid.uuid4())[:8],
                    "name":     s.get("name", "").strip() or "Unnamed",
                    "rss_url":  s.get("rss_url", "").strip(),
                    "enabled":  bool(s.get("enabled", True)),
                    "category": s.get("category", "").strip(),
                })

            cfg = {
                "sites":               clean_sites,
                "google_news":         bool(body.get("google_news",         DEFAULTS["google_news"])),
                "max_per_source":      int( body.get("max_per_source",      DEFAULTS["max_per_source"])),
                "default_category":    str( body.get("default_category",    DEFAULTS["default_category"])),
                "auto_excerpt_length": int( body.get("auto_excerpt_length", DEFAULTS["auto_excerpt_length"])),
                "content_min_chars":   int( body.get("content_min_chars",   DEFAULTS["content_min_chars"])),
            }
            _run(kv_set(KV_KEY, json.dumps(cfg)))
            self._json(200, {"success": True, "settings": cfg})
        except Exception as e:
            self._json(500, {"success": False, "error": str(e)})

    def log_message(self, *a): pass
