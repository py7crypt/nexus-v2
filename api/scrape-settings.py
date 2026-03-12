"""
GET  /api/scrape-settings  -> load scrape config from KV
POST /api/scrape-settings  -> save scrape config to KV
Auth: Bearer required.
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(__file__))
from _utils import verify_token, kv_get, kv_set
from http.server import BaseHTTPRequestHandler
import asyncio

KV_KEY = "nexus:scrape-settings"

DEFAULTS = {
    "sites": [
        {"id": "bbc-news",      "name": "BBC News",            "rss_url": "https://feeds.bbci.co.uk/news/rss.xml",                                     "enabled": True,  "category": ""},
        {"id": "reuters",       "name": "Reuters",             "rss_url": "https://feeds.reuters.com/reuters/topNews",                                  "enabled": True,  "category": ""},
        {"id": "ap-news",       "name": "AP News",             "rss_url": "https://feeds.apnews.com/apnews/topnews",                                    "enabled": True,  "category": ""},
        {"id": "aljazeera",     "name": "Al Jazeera",          "rss_url": "https://www.aljazeera.com/xml/rss/all.xml",                                  "enabled": True,  "category": ""},
        {"id": "the-guardian",  "name": "The Guardian",        "rss_url": "https://www.theguardian.com/world/rss",                                      "enabled": True,  "category": ""},
        {"id": "techcrunch",    "name": "TechCrunch",          "rss_url": "https://techcrunch.com/feed/",                                               "enabled": True,  "category": "Technology"},
        {"id": "the-verge",     "name": "The Verge",           "rss_url": "https://www.theverge.com/rss/index.xml",                                     "enabled": True,  "category": "Technology"},
        {"id": "wired",         "name": "Wired",               "rss_url": "https://www.wired.com/feed/rss",                                             "enabled": False, "category": "Technology"},
        {"id": "ars-technica",  "name": "Ars Technica",        "rss_url": "https://feeds.arstechnica.com/arstechnica/index",                            "enabled": False, "category": "Technology"},
        {"id": "nasa",          "name": "NASA",                "rss_url": "https://www.nasa.gov/rss/dyn/breaking_news.rss",                             "enabled": False, "category": "Science"},
        {"id": "sci-american",  "name": "Scientific American", "rss_url": "https://www.scientificamerican.com/platform/morgue/rss/sciam-news-feed.xml", "enabled": False, "category": "Science"},
        {"id": "nature",        "name": "Nature",              "rss_url": "https://www.nature.com/nature.rss",                                          "enabled": False, "category": "Science"},
        {"id": "bbc-business",  "name": "BBC Business",        "rss_url": "https://feeds.bbci.co.uk/news/business/rss.xml",                             "enabled": False, "category": "Business"},
        {"id": "bbc-sport",     "name": "BBC Sport",           "rss_url": "https://feeds.bbci.co.uk/sport/rss.xml",                                     "enabled": False, "category": "Sports"},
        {"id": "espn",          "name": "ESPN",                "rss_url": "https://www.espn.com/espn/rss/news",                                         "enabled": False, "category": "Sports"},
        {"id": "variety",       "name": "Variety",             "rss_url": "https://variety.com/feed/",                                                  "enabled": False, "category": "Entertainment"},
        {"id": "bbc-health",    "name": "BBC Health",          "rss_url": "https://feeds.bbci.co.uk/news/health/rss.xml",                               "enabled": False, "category": "Health"},
        {"id": "who",           "name": "WHO News",            "rss_url": "https://www.who.int/rss-feeds/news-english.xml",                             "enabled": False, "category": "Health"},
    ],
    "default_category": "",
}

def _run(coro):
    loop = asyncio.new_event_loop()
    result = loop.run_until_complete(coro)
    loop.close()
    return result

def _load():
    try:
        raw = _run(kv_get(KV_KEY))
        if raw:
            cfg = json.loads(raw)
            cfg.setdefault("sites", DEFAULTS["sites"])
            cfg.setdefault("default_category", "")
            # Strip obsolete fields
            for f in ("max_per_source", "content_min_chars", "auto_excerpt_length", "google_news"):
                cfg.pop(f, None)
            return cfg
    except Exception:
        pass
    return dict(DEFAULTS)

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
        if not verify_token(self.headers.get("Authorization", "")):
            return self._json(401, {"success": False, "error": "Unauthorized"})
        try:
            self._json(200, {"success": True, "settings": _load()})
        except Exception as e:
            self._json(500, {"success": False, "error": str(e)})

    def do_POST(self):
        if not verify_token(self.headers.get("Authorization", "")):
            return self._json(401, {"success": False, "error": "Unauthorized"})
        try:
            length = int(self.headers.get("Content-Length", 0))
            body   = json.loads(self.rfile.read(length) or b"{}")
            cfg = {
                "sites":            body.get("sites", DEFAULTS["sites"]),
                "default_category": body.get("default_category", ""),
            }
            _run(kv_set(KV_KEY, json.dumps(cfg)))
            self._json(200, {"success": True, "settings": cfg})
        except Exception as e:
            self._json(500, {"success": False, "error": str(e)})

    def log_message(self, *a): pass