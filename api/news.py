"""
GET /api/news                 → articles from all enabled sources
GET /api/news?q=TOPIC         → search Google News
GET /api/news?category=X      → category-filtered search
GET /api/news?source_id=ID    → articles from one specific source only
GET /api/news?fetch=URL       → scrape full article meta from URL

Reads source list + settings from KV (nexus:scrape-settings).
Uses BeautifulSoup4 if available, falls back to stdlib regex.
Auth: Bearer required.
"""
import sys, os, json, re, urllib.request, urllib.parse
import xml.etree.ElementTree as ET
from html import unescape
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import asyncio

sys.path.insert(0, os.path.dirname(__file__))
from _utils import verify_token, kv_get

try:
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False

KV_SETTINGS_KEY = "nexus:scrape-settings"

DEFAULTS = {
    "sites": [
        {"id": "google-news", "name": "Google News", "rss_url": "https://news.google.com/rss?hl=en-US&gl=US&ceid=US:en", "enabled": True,  "category": ""},
        {"id": "bbc-news",    "name": "BBC News",     "rss_url": "http://feeds.bbci.co.uk/news/rss.xml",                  "enabled": True,  "category": ""},
    ],
    "max_per_source":     10,
    "default_category":   "",
    "content_min_chars":  60,
    "auto_excerpt_length": 200,
}

CATEGORY_QUERIES = {
    "technology":    "technology",
    "science":       "science",
    "business":      "business finance",
    "health":        "health medicine",
    "politics":      "politics government",
    "sports":        "sports",
    "entertainment": "entertainment celebrity",
    "travel":        "travel",
    "culture":       "culture society",
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept":          "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

def _run(c):
    loop = asyncio.new_event_loop()
    r = loop.run_until_complete(c)
    loop.close()
    return r

def _load_settings():
    try:
        raw = _run(kv_get(KV_SETTINGS_KEY))
        if raw:
            cfg = json.loads(raw)
            for k, v in DEFAULTS.items():
                cfg.setdefault(k, v)
            return cfg
    except Exception:
        pass
    return dict(DEFAULTS)

def _get(url, timeout=10):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read(600_000).decode("utf-8", errors="replace")

# ── RSS parser ────────────────────────────────────────────────────────────────

def _parse_rss(xml_text, source_name="", default_category="", max_items=10):
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return []
    articles = []
    # Support both RSS <item> and Atom <entry>
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    items = root.findall(".//item") or root.findall(".//atom:entry", ns)
    for item in items[:max_items]:
        title  = unescape(item.findtext("title", "") or item.findtext("atom:title", "", ns))
        link   = item.findtext("link",    "") or item.findtext("atom:link", "", ns)
        desc   = unescape(re.sub(r"<[^>]+>", "", item.findtext("description", "") or item.findtext("atom:summary", "", ns)))
        pub    = item.findtext("pubDate", "") or item.findtext("atom:published", "", ns)
        src_el = item.find("source")
        source = src_el.text.strip() if src_el is not None else source_name

        # Atom <link> is an element with href attr
        if not link:
            link_el = item.find("atom:link", ns)
            if link_el is not None:
                link = link_el.get("href", "")

        # Google News appends " - Source Name" to titles
        if source and title.endswith(f" - {source}"):
            title = title[:-(len(source) + 3)]

        if title and link:
            articles.append({
                "title":    title.strip(),
                "url":      link.strip(),
                "excerpt":  desc.strip()[:300],
                "source":   source,
                "pub_date": pub,
                "category": default_category,
            })
    return articles

def _fetch_rss(url, source_name="", default_category="", max_items=10):
    return _parse_rss(_get(url), source_name=source_name, default_category=default_category, max_items=max_items)

# ── Article meta scraper ──────────────────────────────────────────────────────

def _scrape_article(url, min_chars=60):
    html = _get(url, timeout=10)
    if HAS_BS4:
        soup = BeautifulSoup(html, "html.parser")

        def og(prop):
            tag = (soup.find("meta", property=f"og:{prop}") or
                   soup.find("meta", attrs={"name": f"twitter:{prop}"}) or
                   soup.find("meta", attrs={"name": prop}))
            return (tag.get("content") or "").strip() if tag else ""

        title   = og("title")  or (soup.find("h1").get_text(strip=True) if soup.find("h1") else "")
        excerpt = og("description")
        image   = og("image")
        site    = og("site_name")

        # Best-effort article body
        container = (soup.find("article") or
                     soup.find(class_=re.compile(r"article|content|story|post", re.I)) or
                     soup.body)

        paragraphs = []
        if container:
            for p in container.find_all("p"):
                t = p.get_text(strip=True)
                if len(t) >= min_chars:
                    paragraphs.append(t)

        if not paragraphs:
            for p in soup.find_all("p"):
                t = p.get_text(strip=True)
                if len(t) >= min_chars:
                    paragraphs.append(t)
    else:
        def _meta(prop):
            m = re.search(
                rf'<meta[^>]+property=["\']og:{re.escape(prop)}["\'][^>]+content=["\']([^"\']+)["\']',
                html, re.I)
            if not m:
                m = re.search(
                    rf'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:{re.escape(prop)}["\']',
                    html, re.I)
            return unescape(m.group(1).strip()) if m else ""

        title      = _meta("title")
        excerpt    = _meta("description")
        image      = _meta("image")
        site       = _meta("site_name")
        paragraphs = [unescape(p) for p in re.findall(r"<p[^>]*>([^<]{%d,})</p>" % min_chars, html, re.I)]

    # Build HTML content
    if paragraphs:
        content_html = "\n".join(f"<p>{p}</p>" for p in paragraphs[:20])
        content_html += f'\n<p><em>Source: <a href="{url}" target="_blank">{site or url}</a></em></p>'
    else:
        content_html = (f"<p>{excerpt}</p>\n" if excerpt else "") + \
                       f'<p><em>Source: <a href="{url}" target="_blank">{site or url}</a></em></p>'

    return {
        "title":        title,
        "excerpt":      (excerpt or " ".join(paragraphs)[:200]).strip(),
        "cover_image":  image,
        "site_name":    site,
        "content_html": content_html,
        "source_url":   url,
        "parser":       "beautifulsoup4" if HAS_BS4 else "stdlib-regex",
    }

# ── Handler ───────────────────────────────────────────────────────────────────

class handler(BaseHTTPRequestHandler):
    def _cors(self):
        self.send_header("Access-Control-Allow-Origin",  "*")
        self.send_header("Access-Control-Allow-Methods", "GET,OPTIONS")
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

        qs        = parse_qs(urlparse(self.path).query)
        query     = qs.get("q",         [None])[0]
        category  = qs.get("category",  [None])[0]
        fetch_url = qs.get("fetch",     [None])[0]
        source_id = qs.get("source_id", [None])[0]

        try:
            cfg        = _load_settings()
            max_each   = cfg.get("max_per_source", 10)
            min_chars  = cfg.get("content_min_chars", 60)

            # ── Mode: scrape article meta ───────────────────────────────────
            if fetch_url:
                meta = _scrape_article(urllib.parse.unquote(fetch_url), min_chars=min_chars)
                return self._json(200, {"success": True, "meta": meta})

            # ── Mode: Google News search (q or category) ────────────────────
            if query or category:
                base = "https://news.google.com/rss"
                if query:
                    q   = urllib.parse.quote(query)
                    url = f"{base}/search?q={q}&hl=en-US&gl=US&ceid=US:en"
                else:
                    kw  = CATEGORY_QUERIES.get(category.lower(), category)
                    q   = urllib.parse.quote(kw)
                    url = f"{base}/search?q={q}&hl=en-US&gl=US&ceid=US:en"
                articles = _fetch_rss(url, source_name="Google News", default_category=category or "", max_items=max_each * 2)
                return self._json(200, {"success": True, "articles": articles, "count": len(articles)})

            # ── Mode: single source ─────────────────────────────────────────
            sites = cfg.get("sites", [])
            if source_id:
                site = next((s for s in sites if s["id"] == source_id), None)
                if not site:
                    return self._json(404, {"success": False, "error": "Source not found"})
                arts = _fetch_rss(site["rss_url"], source_name=site["name"],
                                  default_category=site.get("category",""), max_items=max_each)
                return self._json(200, {"success": True, "articles": arts, "count": len(arts), "source": site["name"]})

            # ── Mode: all enabled sources ───────────────────────────────────
            all_articles = []
            errors = []
            for site in sites:
                if not site.get("enabled", False):
                    continue
                try:
                    arts = _fetch_rss(
                        site["rss_url"],
                        source_name=site["name"],
                        default_category=site.get("category", cfg.get("default_category","")),
                        max_items=max_each,
                    )
                    all_articles.extend(arts)
                except Exception as e:
                    errors.append({"source": site["name"], "error": str(e)})

            # Sort by pub_date descending (best effort)
            def _date_key(a):
                try:
                    from email.utils import parsedate_to_datetime
                    return parsedate_to_datetime(a["pub_date"]).timestamp()
                except Exception:
                    return 0
            all_articles.sort(key=_date_key, reverse=True)

            self._json(200, {
                "success":  True,
                "articles": all_articles,
                "count":    len(all_articles),
                "errors":   errors,
            })

        except Exception as e:
            self._json(500, {"success": False, "error": str(e)})

    def log_message(self, *a): pass
