"""
GET /api/news                -> all enabled sources
GET /api/news?q=TOPIC        -> keyword search
GET /api/news?category=X     -> category filter
GET /api/news?source_id=ID   -> single source
GET /api/news?fetch=URL      -> scrape full article (body + images + links + author)
Auth: Bearer required.
"""
import sys, os, json, re, urllib.request, urllib.parse
import xml.etree.ElementTree as ET
from html import unescape
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs, urljoin
import asyncio

sys.path.insert(0, os.path.dirname(__file__))
from _utils import verify_token, kv_get

try:
    from bs4 import BeautifulSoup, NavigableString, Tag
    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False

KV_SETTINGS_KEY = "nexus:scrape-settings"

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

HEADERS = {
    "User-Agent":      "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept":          "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

CAT_KEYWORDS = {
    "Technology":    ["tech","ai","software","hardware","apple","google","microsoft","meta","nvidia","robot","startup","app","cyber","internet","chip","smartphone","openai","algorithm","cloud","electric vehicle","tesla","coding","developer","iphone","android","samsung"],
    "Science":       ["science","research","study","nasa","space","climate","physics","biology","genome","vaccine","asteroid","planet","fossil","experiment","discovery","quantum","ocean","species","evolution","astronomy"],
    "Business":      ["economy","market","stock","finance","trade","gdp","inflation","bank","invest","merger","revenue","profit","ipo","fund","dollar","recession","interest rate","wall street","nasdaq"],
    "Health":        ["health","medical","disease","cancer","covid","drug","hospital","surgery","mental","nutrition","fitness","obesity","diabetes","fda","who","pandemic","therapy","vaccine","treatment","pharmaceutical"],
    "Politics":      ["election","government","president","congress","senate","parliament","law","policy","democrat","republican","minister","vote","political","diplomacy","sanction","war","nato","united nations","white house","kremlin"],
    "Sports":        ["football","soccer","basketball","tennis","golf","nba","nfl","fifa","olympics","championship","league","match","tournament","player","coach","stadium","formula 1","f1","cricket","rugby","boxing","mma"],
    "Entertainment": ["movie","film","music","celebrity","award","oscar","grammy","netflix","hollywood","actor","singer","album","concert","tv","show","series","streaming","box office","spotify","disney","marvel","gaming"],
    "Travel":        ["travel","tourism","hotel","flight","airline","destination","resort","visa","passport","vacation","trip","cruise","airport"],
    "Culture":       ["culture","art","museum","book","literature","fashion","food","cuisine","history","religion","tradition","society","education","language","design"],
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
            cfg.setdefault("sites", DEFAULTS["sites"])
            cfg.setdefault("default_category", "")
            return cfg
    except Exception:
        pass
    return dict(DEFAULTS)

def _fetch(url, timeout=14):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read(1_000_000).decode("utf-8", errors="replace"), r.url

def _infer_category(text):
    t = text.lower()
    scores = {cat: sum(1 for kw in kws if kw in t) for cat, kws in CAT_KEYWORDS.items()}
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else ""

def _clean_title(title, source=""):
    for sep in [" | ", " - ", " :: ", " — ", " – "]:
        if source and title.endswith(sep + source):
            title = title[:-(len(sep) + len(source))]
            break
    if title == title.upper() and len(title) > 10:
        title = title.title()
    return title.strip()

def _excerpt(text, n=260):
    text = (text or "").strip()
    if len(text) <= n: return text
    cut = text[:n]
    last = max(cut.rfind(". "), cut.rfind("! "), cut.rfind("? "))
    if last > n * 0.6: return cut[:last+1].strip()
    ls = cut.rfind(" ")
    return (cut[:ls] + "…") if ls > 0 else cut

def _matches(article, q):
    if not q: return True
    t = (article.get("title","") + " " + article.get("excerpt","")).lower()
    return all(w in t for w in q.lower().split())

# ── RSS parser ─────────────────────────────────────────────────────────────────
def _parse_rss(xml_text, source_name="", default_category="", max_items=20):
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return []
    ns = {
        "atom":  "http://www.w3.org/2005/Atom",
        "dc":    "http://purl.org/dc/elements/1.1/",
        "media": "http://search.yahoo.com/mrss/",
    }
    items    = root.findall(".//item") or root.findall(".//atom:entry", ns)
    articles = []
    for item in items[:max_items]:
        title  = unescape(item.findtext("title","") or item.findtext("atom:title","",ns))
        link   = item.findtext("link","") or ""
        desc   = item.findtext("description","") or item.findtext("atom:summary","",ns) or ""
        desc   = unescape(re.sub(r"<[^>]+>","",desc))
        pub    = item.findtext("pubDate","") or item.findtext("atom:published","",ns) or ""
        author = (item.findtext("dc:creator","",ns) or item.findtext("author","") or
                  item.findtext("atom:author/atom:name","",ns) or "")
        src_el = item.find("source")
        source = src_el.text.strip() if src_el is not None and src_el.text else source_name
        if not link:
            lel = item.find("atom:link", ns)
            if lel is not None: link = lel.get("href","")
        # thumbnail
        thumb = ""
        for mt in ["media:thumbnail","media:content"]:
            el = item.find(mt, ns)
            if el is not None:
                thumb = el.get("url","")
                if thumb: break
        if not thumb:
            enc = item.find("enclosure")
            if enc is not None and "image" in (enc.get("type","") or ""):
                thumb = enc.get("url","")
        rss_cats = [unescape(e.text or "").strip() for e in item.findall("category") if e.text]
        title    = _clean_title(title, source)
        if not title or not link: continue
        if default_category:
            category = default_category
        elif rss_cats:
            category = _infer_category(" ".join(rss_cats)) or rss_cats[0].title()
        else:
            category = _infer_category(title + " " + desc)
        tags = list({t.lower().replace(" ","-") for t in rss_cats[:4] if t})
        if source and source.lower().replace(" ","-") not in tags:
            tags.append(source.lower().replace(" ","-"))
        articles.append({
            "title":    title,
            "url":      link.strip(),
            "excerpt":  _excerpt(desc),
            "source":   source,
            "author":   author.strip(),
            "thumb":    thumb,
            "pub_date": pub,
            "category": category,
            "tags":     tags,
        })
    return articles

def _fetch_rss(url, source_name="", default_category="", max_items=20):
    xml, _ = _fetch(url)
    return _parse_rss(xml, source_name=source_name, default_category=default_category, max_items=max_items)

# ── Full article scraper ───────────────────────────────────────────────────────
JUNK_CLASSES = re.compile(
    r"ad[-_]|promo|related|recommend|newsletter|subscribe|social[-_]share|"
    r"comment|sidebar|breadcrumb|cookie|popup|share[-_]bar|tag[-_]list|"
    r"author[-_]bio|read[-_]more|more[-_]stories|footer|nav[-_]",
    re.I
)
JUNK_TAGS = {"script","style","nav","header","footer","aside","form","button",
             "noscript","iframe[^youtube]","svg","figure.ad"}

SKIP_SRC = {"1x1","pixel","tracking","spacer","logo","icon","avatar",
            "placeholder","blank","transparent","data:image"}

def _good_src(img, base):
    """Return absolute, usable image src or ''."""
    src = (img.get("src") or img.get("data-src") or img.get("data-lazy-src") or
           img.get("data-original") or img.get("data-lazy") or img.get("data-srcset","").split()[0] or "")
    if not src: return ""
    src = urljoin(base, src)
    if not src.startswith("http"): return ""
    sl = src.lower()
    if any(p in sl for p in SKIP_SRC): return ""
    try:
        w, h = int(img.get("width",0) or 0), int(img.get("height",0) or 0)
        if (w and w < 60) or (h and h < 60): return ""
    except Exception:
        pass
    return src

def _scrape_full(url):
    html, final_url = _fetch(url, timeout=16)
    url      = final_url
    base     = "{0.scheme}://{0.netloc}".format(urlparse(url))
    domain   = urlparse(url).netloc

    # ── stdlib fallback ────────────────────────────────────────────────────────
    if not HAS_BS4:
        def _og(p):
            m = re.search(r'<meta[^>]+(?:property|name)=["\']og:' + p + r'["\'][^>]+content=["\']([^"\']+)', html, re.I)
            if not m:
                m = re.search(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+(?:property|name)=["\']og:' + p + r'"', html, re.I)
            return unescape(m.group(1).strip()) if m else ""
        title   = _og("title")
        excerpt = _og("description")
        image   = _og("image")
        site    = _og("site_name")
        paras   = re.findall(r"<p[^>]*>([^<]{80,})</p>", html, re.I)
        body    = "\n".join("<p>" + unescape(p) + "</p>" for p in paras[:25])
        body   += '\n<hr/>\n<p style="font-size:.85em;color:#64748b">Source: <a href="{}" target="_blank">{}</a></p>'.format(url, site or domain)
        return {"title": _clean_title(title, site), "excerpt": _excerpt(excerpt),
                "cover_image": image, "site_name": site, "author": "",
                "content_html": body, "source_url": url,
                "category": _infer_category(title+" "+excerpt), "tags": []}

    soup = BeautifulSoup(html, "html.parser")

    # ── OG meta ────────────────────────────────────────────────────────────────
    def og(prop):
        t = (soup.find("meta", property="og:"+prop) or
             soup.find("meta", attrs={"name":"og:"+prop}) or
             soup.find("meta", attrs={"name":"twitter:"+prop}))
        return (t.get("content") or "").strip() if t else ""

    og_title   = og("title") or (soup.find("h1").get_text(strip=True) if soup.find("h1") else "")
    og_excerpt = og("description")
    og_image   = og("image")
    og_site    = og("site_name")

    # ── Author ─────────────────────────────────────────────────────────────────
    author = ""
    # 1. JSON-LD (BBC, Guardian, Reuters, TechCrunch all use this)
    for sc in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(sc.string or "")
            for item in (data if isinstance(data, list) else [data]):
                if item.get("@type") in ("NewsArticle","Article","BlogPosting","ReportageNewsArticle"):
                    a = item.get("author") or item.get("creator") or {}
                    if isinstance(a, list): a = a[0]
                    author = (a.get("name","") if isinstance(a, dict) else str(a)).strip()
                    if author: break
            if author: break
        except Exception:
            pass
    # 2. Byline CSS
    if not author:
        for attrs in [
            {"class": re.compile(r"\bauthor\b|\bbyline\b|\bwriter\b|\bcontributor\b|\bby[-_]line\b", re.I)},
            {"rel": "author"}, {"itemprop": "author"},
        ]:
            el = soup.find(attrs=attrs)
            if el:
                t = re.sub(r"^[Bb]y[\s:–]+","", el.get_text(strip=True))
                if 2 < len(t) < 80: author = t.strip(); break
    # 3. meta author
    if not author:
        m = soup.find("meta", attrs={"name":"author"})
        if m: author = (m.get("content") or "").strip()

    # ── Find article container ─────────────────────────────────────────────────
    container = None
    for cand in [
        soup.find("article"),
        soup.find(attrs={"itemprop": "articleBody"}),
        soup.find(class_=re.compile(r"\barticle[-_]?body\b|\bcontent[-_]?body\b|\bstory[-_]?body\b|\bpost[-_]?content\b", re.I)),
        soup.find(class_=re.compile(r"\barticle\b|\bstory\b|\bpost\b|\bcontent\b", re.I)),
        soup.find("main"),
        soup.body,
    ]:
        if cand:
            container = cand
            break

    # Decompose noise
    if container:
        for t in container.find_all(["script","style","nav","header","footer","aside","form","button","noscript","svg"]):
            t.decompose()
        for t in container.find_all(class_=JUNK_CLASSES):
            t.decompose()
        for t in container.find_all(id=JUNK_CLASSES):
            t.decompose()

    # ── Inline serialiser — preserves links, bold, italic, images ─────────────
    def _inline(node):
        """Render inner content keeping <a>, <strong>, <em>, inline <img>."""
        parts = []
        for child in node.children:
            if isinstance(child, NavigableString):
                parts.append(str(child))
            elif isinstance(child, Tag):
                n = child.name
                if n == "a":
                    href = urljoin(base, child.get("href",""))
                    text = child.get_text()
                    if href.startswith("http") and text.strip():
                        parts.append('<a href="{}" target="_blank" rel="noopener">{}</a>'.format(href, text))
                    else:
                        parts.append(child.get_text())
                elif n in ("strong","b"):
                    parts.append("<strong>{}</strong>".format(child.get_text()))
                elif n in ("em","i"):
                    parts.append("<em>{}</em>".format(child.get_text()))
                elif n == "span":
                    parts.append(_inline(child))
                elif n == "br":
                    parts.append("<br/>")
                elif n == "img":
                    src = _good_src(child, base)
                    if src:
                        alt = (child.get("alt","") or "").replace('"',"&quot;")
                        parts.append('<img src="{}" alt="{}" style="max-width:100%;height:auto;border-radius:6px;margin:.5rem 0;display:block"/>'.format(src, alt))
                else:
                    parts.append(child.get_text())
        return "".join(parts).strip()

    # ── DOM walker ─────────────────────────────────────────────────────────────
    parts = []

    def walk(node):
        if not isinstance(node, Tag):
            return
        n = node.name

        if n == "p":
            inner = _inline(node)
            plain = node.get_text(strip=True)
            if len(plain) >= 40:          # keep meaningful paragraphs
                parts.append("<p>{}</p>".format(inner))

        elif n in ("h2","h3","h4","h5"):
            text = node.get_text(strip=True)
            if text and len(text) < 200:
                ht = "h2" if n in ("h2","h3") else "h3"
                parts.append("<{0}>{1}</{0}>".format(ht, text))

        elif n == "blockquote":
            inner = _inline(node)
            if inner:
                parts.append('<blockquote style="border-left:4px solid #e2e8f0;padding:.5rem 1rem;margin:1rem 0;color:#64748b">{}</blockquote>'.format(inner))

        elif n == "figure":
            img = node.find("img")
            if img:
                src = _good_src(img, base)
                if src:
                    alt = (img.get("alt","") or "").replace('"',"&quot;")
                    cap_el  = node.find("figcaption")
                    caption = cap_el.get_text(strip=True) if cap_el else ""
                    img_tag = '<img src="{}" alt="{}" style="max-width:100%;height:auto;border-radius:8px;display:block"/>'.format(src, alt)
                    if caption:
                        parts.append('<figure style="margin:1.5rem 0">{}<figcaption style="font-size:.85em;color:#64748b;margin-top:.4rem;font-style:italic">{}</figcaption></figure>'.format(img_tag, caption))
                    else:
                        parts.append('<figure style="margin:1.5rem 0">{}</figure>'.format(img_tag))

        elif n == "img":
            src = _good_src(node, base)
            if src:
                alt = (node.get("alt","") or "").replace('"',"&quot;")
                parts.append('<img src="{}" alt="{}" style="max-width:100%;height:auto;border-radius:8px;display:block;margin:1rem 0"/>'.format(src, alt))

        elif n == "iframe":
            src = node.get("src","")
            if src and any(x in src for x in ["youtube.com/embed","youtu.be","vimeo.com/video","player."]):
                parts.append(
                    '<div style="position:relative;padding-bottom:56.25%;height:0;overflow:hidden;margin:1.5rem 0">'
                    '<iframe src="{}" style="position:absolute;top:0;left:0;width:100%;height:100%;border:0" '
                    'allowfullscreen loading="lazy"></iframe></div>'.format(src))

        elif n == "video":
            se  = node.find("source")
            src = (se.get("src","") if se else node.get("src",""))
            if src:
                src = urljoin(base, src)
                parts.append('<video controls style="max-width:100%;margin:1rem 0"><source src="{}"></video>'.format(src))

        elif n in ("ul","ol"):
            items = []
            for li in node.find_all("li", recursive=False):
                inner = _inline(li)
                if li.get_text(strip=True):
                    items.append("<li>{}</li>".format(inner))
            if items:
                parts.append("<{0}>{1}</{0}>".format(n, "".join(items)))

        elif n in ("div","section","main"):
            for child in node.children:
                walk(child)

    if container:
        for child in container.children:
            walk(child)

    # Fallback if nothing extracted
    if not parts and container:
        for p in container.find_all("p"):
            t = p.get_text(strip=True)
            if len(t) >= 40:
                parts.append("<p>{}</p>".format(t))

    # ── Attribution footer ─────────────────────────────────────────────────────
    author_part = ' &middot; by <strong>{}</strong>'.format(author) if author else ""
    content_html = "\n".join(parts)
    content_html += (
        '\n<hr style="margin:2.5rem 0;border:none;border-top:1px solid #e2e8f0"/>'
        '\n<p style="font-size:.85em;color:#64748b">Originally published at '
        '<a href="{url}" target="_blank" rel="noopener">{site}</a>{author}</p>'.format(
            url=url, site=og_site or domain, author=author_part)
    )

    # Cover image fallback — first content image
    if not og_image:
        m = re.search(r'<img[^>]+src="(https?://[^"]+)"', content_html)
        if m: og_image = m.group(1)

    smart_exc = _excerpt(og_excerpt)
    category  = _infer_category((og_title or "") + " " + smart_exc)
    tags      = [kw for kws in CAT_KEYWORDS.values() for kw in kws if kw in (og_title or "").lower()][:5]
    if og_site: tags.append(og_site.lower().replace(" ","-"))

    return {
        "title":        _clean_title(og_title or "", og_site or ""),
        "excerpt":      smart_exc,
        "cover_image":  og_image,
        "site_name":    og_site,
        "author":       author,
        "content_html": content_html,
        "source_url":   url,
        "category":     category,
        "tags":         list(dict.fromkeys(tags))[:6],
    }

# ── Handler ────────────────────────────────────────────────────────────────────
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
        if not verify_token(self.headers.get("Authorization","")):
            return self._json(401, {"success": False, "error": "Unauthorized"})

        qs        = parse_qs(urlparse(self.path).query)
        query     = qs.get("q",         [None])[0]
        category  = qs.get("category",  [None])[0]
        fetch_url = qs.get("fetch",     [None])[0]
        source_id = qs.get("source_id", [None])[0]

        try:
            cfg   = _load_settings()
            sites = cfg.get("sites", DEFAULTS["sites"])

            # ── Scrape full article ────────────────────────────────────────
            if fetch_url:
                meta = _scrape_full(urllib.parse.unquote(fetch_url))
                return self._json(200, {"success": True, "meta": meta})

            # ── Single source ──────────────────────────────────────────────
            if source_id:
                site = next((s for s in sites if s["id"] == source_id), None)
                if not site:
                    return self._json(404, {"success": False, "error": "Source not found"})
                arts = _fetch_rss(site["rss_url"], source_name=site["name"],
                                  default_category=site.get("category",""))
                return self._json(200, {"success": True, "articles": arts,
                                        "count": len(arts), "source": site["name"]})

            # ── All enabled ────────────────────────────────────────────────
            all_articles, errors = [], []
            for site in sites:
                if not site.get("enabled"): continue
                try:
                    arts = _fetch_rss(site["rss_url"], source_name=site["name"],
                                      default_category=site.get("category", cfg.get("default_category","")))
                    all_articles.extend(arts)
                except Exception as e:
                    errors.append({"source": site["name"], "error": str(e)})

            # Keyword filter
            if query:
                all_articles = [a for a in all_articles if _matches(a, query)]
            # Category filter
            if category and category.lower() not in ("all",""):
                all_articles = [a for a in all_articles if a.get("category","").lower() == category.lower()]

            # Sort newest first
            def _ts(a):
                try:
                    from email.utils import parsedate_to_datetime
                    return parsedate_to_datetime(a["pub_date"]).timestamp()
                except Exception:
                    return 0
            all_articles.sort(key=_ts, reverse=True)

            # Deduplicate by title
            seen, unique = set(), []
            for a in all_articles:
                k = a["title"].lower()[:60]
                if k not in seen:
                    seen.add(k)
                    unique.append(a)

            self._json(200, {"success": True, "articles": unique,
                             "count": len(unique), "errors": errors})
        except Exception as e:
            self._json(500, {"success": False, "error": str(e)})

    def log_message(self, *a): pass