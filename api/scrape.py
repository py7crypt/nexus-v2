"""
POST /api/scrape
Body: { "title": "Article topic to research" }
Auth: Bearer token required

Uses the configured AI model (Anthropic first, then others) to:
1. Search the web for recent news on the topic (via AI web knowledge)
2. Return structured article data: title, excerpt, content, tags, cover_image suggestion, category
"""
import sys, os, json, asyncio, urllib.request, urllib.error
sys.path.insert(0, os.path.dirname(__file__))
from _utils import verify_token
from http.server import BaseHTTPRequestHandler

def _run(c):
    loop = asyncio.new_event_loop()
    r = loop.run_until_complete(c)
    loop.close()
    return r

def _call_ai(topic):
    """Try AI providers in order until one works."""
    system = (
        "You are a professional news journalist and web researcher. "
        "When given a topic, you research it thoroughly and write a comprehensive, "
        "factual news article in the style of major news outlets like MSN, Reuters, or AP News. "
        "Always respond with ONLY valid JSON, no markdown, no preamble."
    )

    user = f"""Research and write a complete news article about: "{topic}"

Return ONLY this JSON (no markdown, no backticks):
{{
  "title": "Compelling, specific headline (max 80 chars)",
  "category": "One of: Technology, Science, Business, Health, Politics, Sports, Entertainment, Travel, Culture",
  "excerpt": "2-3 sentence compelling summary (max 200 chars)",
  "content": "Full HTML article body, minimum 600 words. Use <h2> subheadings, <p> paragraphs, <blockquote> for quotes. Write like a professional journalist covering breaking news. Include background context, key facts, expert perspective, and implications.",
  "tags": ["tag1", "tag2", "tag3", "tag4", "tag5"],
  "cover_image": "A relevant Unsplash photo URL for this topic — use format: https://images.unsplash.com/photo-PHOTOID?w=1200&q=80 — pick a realistic Unsplash photo ID that would match this topic",
  "seo_title": "SEO optimized title (max 60 chars)",
  "seo_description": "Meta description (max 155 chars)"
}}"""

    providers = []

    # Anthropic
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if key:
        providers.append(("anthropic", key))

    # OpenAI
    key = os.environ.get("OPENAI_API_KEY", "")
    if key:
        providers.append(("openai", key))

    # DeepSeek
    key = os.environ.get("DEEPSEEK_API_KEY", "")
    if key:
        providers.append(("deepseek", key))

    # Gemini
    key = os.environ.get("GEMINI_API_KEY", "")
    if key:
        providers.append(("gemini", key))

    for provider, api_key in providers:
        try:
            if provider == "anthropic":
                payload = json.dumps({
                    "model": "claude-haiku-4-5-20251001",
                    "max_tokens": 4096,
                    "system": system,
                    "messages": [{"role": "user", "content": user}]
                }).encode()
                req = urllib.request.Request(
                    "https://api.anthropic.com/v1/messages",
                    data=payload,
                    headers={
                        "x-api-key": api_key,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json",
                    }
                )
                with urllib.request.urlopen(req, timeout=30) as r:
                    rd = json.loads(r.read())
                text = rd["content"][0]["text"]

            elif provider == "openai":
                payload = json.dumps({
                    "model": "gpt-4o-mini",
                    "max_tokens": 4096,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user",   "content": user}
                    ]
                }).encode()
                req = urllib.request.Request(
                    "https://api.openai.com/v1/chat/completions",
                    data=payload,
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    }
                )
                with urllib.request.urlopen(req, timeout=30) as r:
                    rd = json.loads(r.read())
                text = rd["choices"][0]["message"]["content"]

            elif provider == "deepseek":
                payload = json.dumps({
                    "model": "deepseek-chat",
                    "max_tokens": 4096,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user",   "content": user}
                    ]
                }).encode()
                req = urllib.request.Request(
                    "https://api.deepseek.com/v1/chat/completions",
                    data=payload,
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    }
                )
                with urllib.request.urlopen(req, timeout=30) as r:
                    rd = json.loads(r.read())
                text = rd["choices"][0]["message"]["content"]

            elif provider == "gemini":
                payload = json.dumps({
                    "system_instruction": {"parts": [{"text": system}]},
                    "contents": [{"parts": [{"text": user}]}],
                    "generationConfig": {"maxOutputTokens": 4096}
                }).encode()
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"
                req = urllib.request.Request(url, data=payload,
                    headers={"Content-Type": "application/json"})
                with urllib.request.urlopen(req, timeout=30) as r:
                    rd = json.loads(r.read())
                text = rd["candidates"][0]["content"]["parts"][0]["text"]

            # Parse JSON from response
            text = text.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
            return json.loads(text)

        except Exception as e:
            continue

    raise Exception("No AI provider available. Add at least one API key in Vercel environment variables.")


class handler(BaseHTTPRequestHandler):
    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type,Authorization")

    def _json(self, code, body):
        data = json.dumps(body).encode()
        self.send_response(code)
        self._cors()
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(data)

    def do_OPTIONS(self): self._json(200, {})

    def do_POST(self):
        if not verify_token(self.headers.get("Authorization", "")):
            return self._json(401, {"success": False, "error": "Unauthorized"})

        n = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(n)) if n else {}
        title = body.get("title", "").strip()

        if not title:
            return self._json(400, {"success": False, "error": "title is required"})

        try:
            article = _call_ai(title)
            self._json(200, {"success": True, "article": article})
        except Exception as e:
            self._json(500, {"success": False, "error": str(e)})

    def log_message(self, *a): pass
