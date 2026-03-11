"""
GET /api/news              → top headlines (Google News RSS)
GET /api/news?q=TOPIC      → search Google News
GET /api/news?category=X   → category filter
GET /api/news?fetch=URL    → scrape full article meta from URL

Uses BeautifulSoup4 for HTML parsing. No AI needed.
Auth: Bearer token required.
"""
import sys, os, json, re, urllib.request, urllib.parse
import xml.etree.ElementTree as ET
from html import unescape
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

sys.path.insert(0, os.path.dirname(__file__))
from _utils import verify_token

try:
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                  '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
}

CATEGORY_QUERIES = {
    'technology':    'technology',
    'science':       'science',
    'business':      'business finance',
    'health':        'health medicine',
    'politics':      'politics government',
    'sports':        'sports',
    'entertainment': 'entertainment celebrity',
    'travel':        'travel',
    'culture':       'culture society',
}

# ── Fetch helpers ─────────────────────────────────────────────────────────────

def _get(url, timeout=10):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read(600_000).decode('utf-8', errors='replace')

# ── RSS parser ────────────────────────────────────────────────────────────────

def _parse_rss(xml_text):
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return []
    articles = []
    for item in root.findall('.//item')[:25]:
        title   = unescape(item.findtext('title', ''))
        link    = item.findtext('link', '')
        desc    = unescape(re.sub(r'<[^>]+>', '', item.findtext('description', '')))
        pub     = item.findtext('pubDate', '')
        src_el  = item.find('source')
        source  = src_el.text.strip() if src_el is not None else ''
        # Google appends " - Source" to titles
        if source and title.endswith(f' - {source}'):
            title = title[:-(len(source) + 3)]
        if title and link:
            articles.append({
                'title':    title.strip(),
                'url':      link.strip(),
                'excerpt':  desc.strip()[:300],
                'source':   source,
                'pub_date': pub,
            })
    return articles

def _fetch_rss(query=None, category=None):
    base = 'https://news.google.com/rss'
    if query:
        q   = urllib.parse.quote(query)
        url = f'{base}/search?q={q}&hl=en-US&gl=US&ceid=US:en'
    elif category and category.lower() in CATEGORY_QUERIES:
        q   = urllib.parse.quote(CATEGORY_QUERIES[category.lower()])
        url = f'{base}/search?q={q}&hl=en-US&gl=US&ceid=US:en'
    else:
        url = f'{base}?hl=en-US&gl=US&ceid=US:en'
    return _parse_rss(_get(url))

# ── Article scraper (BeautifulSoup) ───────────────────────────────────────────

def _scrape_article(url):
    html = _get(url, timeout=10)

    if HAS_BS4:
        soup = BeautifulSoup(html, 'html.parser')

        def og(prop):
            tag = soup.find('meta', property=f'og:{prop}') or \
                  soup.find('meta', attrs={'name': f'og:{prop}'}) or \
                  soup.find('meta', attrs={'name': prop})
            return (tag.get('content') or '').strip() if tag else ''

        title   = og('title')  or (soup.find('h1').get_text(strip=True) if soup.find('h1') else '')
        excerpt = og('description')
        image   = og('image')
        site    = og('site_name')

        # Extract main article text — look for <article> first, then biggest <div>
        article_el = soup.find('article') or \
                     max(soup.find_all('div'), key=lambda d: len(d.get_text()), default=None)

        paragraphs = []
        if article_el:
            for p in article_el.find_all('p'):
                t = p.get_text(strip=True)
                if len(t) > 60:
                    paragraphs.append(t)

        # Fallback: all <p> tags
        if not paragraphs:
            for p in soup.find_all('p'):
                t = p.get_text(strip=True)
                if len(t) > 60:
                    paragraphs.append(t)

        content_text = ' '.join(paragraphs[:20])

    else:
        # Stdlib fallback
        def _meta(prop):
            m = re.search(
                rf'<meta[^>]+property=["\']og:{re.escape(prop)}["\'][^>]+content=["\']([^"\']+)["\']',
                html, re.I)
            if not m:
                m = re.search(
                    rf'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:{re.escape(prop)}["\']',
                    html, re.I)
            return unescape(m.group(1).strip()) if m else ''

        title        = _meta('title')
        excerpt      = _meta('description')
        image        = _meta('image')
        site         = _meta('site_name')
        paragraphs   = re.findall(r'<p[^>]*>([^<]{80,})</p>', html, re.I)
        content_text = ' '.join(unescape(p) for p in paragraphs[:15])

    # Build HTML content from scraped paragraphs
    if paragraphs:
        content_html = '\n'.join(f'<p>{p}</p>' for p in paragraphs[:20])
        content_html += f'\n<p><em>Source: <a href="{url}" target="_blank">{site or url}</a></em></p>'
    else:
        content_html = f'<p>{excerpt}</p>\n<p><em>Source: <a href="{url}" target="_blank">{site or url}</a></em></p>'

    return {
        'title':        title,
        'excerpt':      (excerpt or content_text[:200]).strip(),
        'cover_image':  image,
        'site_name':    site,
        'content_html': content_html,
        'source_url':   url,
        'parser':       'beautifulsoup4' if HAS_BS4 else 'stdlib',
    }


# ── Handler ───────────────────────────────────────────────────────────────────

class handler(BaseHTTPRequestHandler):
    def _cors(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET,OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type,Authorization')

    def _json(self, code, body):
        data = json.dumps(body).encode()
        self.send_response(code)
        self._cors()
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(data)

    def do_OPTIONS(self): self._json(200, {})

    def do_GET(self):
        if not verify_token(self.headers.get('Authorization', '')):
            return self._json(401, {'success': False, 'error': 'Unauthorized'})

        qs        = parse_qs(urlparse(self.path).query)
        query     = qs.get('q',        [None])[0]
        category  = qs.get('category', [None])[0]
        fetch_url = qs.get('fetch',    [None])[0]

        try:
            if fetch_url:
                meta = _scrape_article(urllib.parse.unquote(fetch_url))
                return self._json(200, {'success': True, 'meta': meta})

            articles = _fetch_rss(query=query, category=category)
            self._json(200, {'success': True, 'articles': articles, 'count': len(articles)})

        except Exception as e:
            self._json(500, {'success': False, 'error': str(e)})

    def log_message(self, *a): pass
