"""
/api/ai-generate — POST: Generate article using Anthropic Claude
Vercel Python Serverless Function
"""
from http.server import BaseHTTPRequestHandler
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from _utils import verify_token, AIGenerateRequest


class handler(BaseHTTPRequestHandler):

    def _send(self, status: int, body: dict):
        data = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()
        self.wfile.write(data)

    def do_OPTIONS(self):
        self._send(200, {})

    def do_POST(self):
        auth = self.headers.get("Authorization", "")
        if not verify_token(auth):
            self._send(401, {"success": False, "error": "Unauthorized"})
            return

        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            self._send(500, {
                "success": False,
                "error": "ANTHROPIC_API_KEY not configured. Add it in Vercel Environment Variables."
            })
            return

        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length)) if length else {}

        topic = body.get("topic", "").strip()
        if not topic:
            self._send(400, {"success": False, "error": "topic is required"})
            return

        category  = body.get("category", "Technology")
        tone      = body.get("tone", "professional")
        length_   = body.get("length", "medium")
        keywords  = body.get("keywords", [])
        language  = body.get("language", "English")

        word_count = {"short": 400, "medium": 800, "long": 1500}.get(length_, 800)

        system_prompt = (
            f"You are a senior journalist and content strategist for NEXUS, "
            f"a prestigious digital media platform. You write compelling, "
            f"well-researched articles with a {tone} tone. "
            f"You always respond with valid JSON only — no markdown fences, no preamble."
        )

        kw_str = f"Keywords to include naturally: {', '.join(keywords)}" if keywords else ""

        user_prompt = f"""Write a complete {word_count}-word blog article about: "{topic}"

Category: {category}
Tone: {tone}
Language: {language}
{kw_str}

Return ONLY a JSON object:
{{
  "title": "Compelling article title",
  "excerpt": "2-3 sentence compelling summary (150 chars max)",
  "content": "Full HTML article using <h2>,<h3>,<p>,<ul>,<li>,<strong>,<em>,<blockquote>. Minimum {word_count} words.",
  "tags": ["tag1","tag2","tag3","tag4","tag5"],
  "seo_title": "SEO title (60 chars max)",
  "seo_description": "Meta description (155 chars max)",
  "cover_image_query": "Short 4-6 word Unsplash search query"
}}"""

        try:
            import urllib.request
            import urllib.error

            payload = json.dumps({
                "model": "claude-sonnet-4-20250514",
                "max_tokens": 4096,
                "system": system_prompt,
                "messages": [{"role": "user", "content": user_prompt}]
            }).encode()

            req = urllib.request.Request(
                "https://api.anthropic.com/v1/messages",
                data=payload,
                headers={
                    "Content-Type": "application/json",
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                },
                method="POST"
            )

            with urllib.request.urlopen(req, timeout=60) as resp:
                response_data = json.loads(resp.read().decode())

            text = response_data.get("content", [{}])[0].get("text", "")

            # Clean and parse JSON
            clean = text.strip()
            if clean.startswith("```"):
                clean = clean.split("```")[1]
                if clean.startswith("json"):
                    clean = clean[4:]
            clean = clean.strip().rstrip("```").strip()

            article = json.loads(clean)

            # Build Unsplash cover URL
            query = article.get("cover_image_query", topic).replace(" ", ",")
            article["cover_image"] = f"https://images.unsplash.com/featured/?{query}&w=1200&q=80"
            article["category"] = category

            self._send(200, {"success": True, "article": article})

        except urllib.error.HTTPError as e:
            err_body = e.read().decode()
            self._send(502, {"success": False, "error": f"Anthropic API error {e.code}: {err_body[:300]}"})
        except json.JSONDecodeError as e:
            self._send(500, {"success": False, "error": f"AI returned invalid JSON: {str(e)}"})
        except Exception as e:
            self._send(500, {"success": False, "error": str(e)})

    def log_message(self, *args):
        pass
