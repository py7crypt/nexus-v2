"""
Shared utilities for NEXUS API
- In-memory store (dev) / Vercel KV via HTTP (prod)
- JWT auth helpers
- Pydantic models
"""
import os
import json
import time
import uuid
import hashlib
from datetime import datetime, timezone
from typing import Optional, List, Any

from pydantic import BaseModel, Field


# ─── MODELS ────────────────────────────────────────────────────────────────

class ArticleCreate(BaseModel):
    title: str
    content: str
    excerpt: Optional[str] = ""
    category: str
    author: Optional[str] = "NEXUS Editorial"
    tags: Optional[List[str]] = []
    status: Optional[str] = "published"  # published | draft
    cover_image: Optional[str] = ""
    seo_title: Optional[str] = ""
    seo_description: Optional[str] = ""


class ArticleUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    excerpt: Optional[str] = None
    category: Optional[str] = None
    author: Optional[str] = None
    tags: Optional[List[str]] = None
    status: Optional[str] = None
    cover_image: Optional[str] = None
    seo_title: Optional[str] = None
    seo_description: Optional[str] = None


class AIGenerateRequest(BaseModel):
    topic: str
    category: Optional[str] = "Technology"
    tone: Optional[str] = "professional"
    length: Optional[str] = "medium"   # short | medium | long
    keywords: Optional[List[str]] = []
    language: Optional[str] = "English"
    generate_seo: Optional[bool] = True


class LoginRequest(BaseModel):
    username: str
    password: str


# ─── AUTH ──────────────────────────────────────────────────────────────────

ADMIN_SECRET = os.environ.get("ADMIN_SECRET", "nexus-admin-2025")
ADMIN_USER   = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASS   = os.environ.get("ADMIN_PASSWORD", "nexus2025")


def verify_token(authorization: str) -> bool:
    if not authorization:
        return False
    parts = authorization.split(" ")
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return False
    return parts[1] == ADMIN_SECRET


def verify_password(username: str, password: str) -> bool:
    return username == ADMIN_USER and password == ADMIN_PASS


# ─── STORAGE ───────────────────────────────────────────────────────────────
# Uses Vercel KV (Upstash Redis REST API) if env vars present,
# otherwise falls back to module-level in-memory dict (dev / demo).

_mem: dict = {}       # key → value
_lists: dict = {}     # key → list of values


def _kv_url() -> Optional[str]:
    return os.environ.get("KV_REST_API_URL")


def _kv_token() -> Optional[str]:
    return os.environ.get("KV_REST_API_TOKEN")


async def kv_get(key: str) -> Optional[Any]:
    url = _kv_url()
    if url:
        import httpx
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"{url}/get/{key}",
                headers={"Authorization": f"Bearer {_kv_token()}"},
                timeout=5,
            )
            data = r.json()
            return data.get("result")
    return _mem.get(key)


async def kv_set(key: str, value: Any) -> None:
    serialized = json.dumps(value) if not isinstance(value, str) else value
    url = _kv_url()
    if url:
        import httpx
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{url}/set/{key}",
                headers={"Authorization": f"Bearer {_kv_token()}"},
                json={"value": serialized},
                timeout=5,
            )
    else:
        _mem[key] = serialized


async def kv_del(key: str) -> None:
    url = _kv_url()
    if url:
        import httpx
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{url}/del/{key}",
                headers={"Authorization": f"Bearer {_kv_token()}"},
                timeout=5,
            )
    else:
        _mem.pop(key, None)


async def kv_lpush(key: str, value: str) -> None:
    url = _kv_url()
    if url:
        import httpx
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{url}/lpush/{key}",
                headers={"Authorization": f"Bearer {_kv_token()}"},
                json={"value": value},
                timeout=5,
            )
    else:
        if key not in _lists:
            _lists[key] = []
        _lists[key].insert(0, value)


async def kv_lrange(key: str, start: int = 0, end: int = -1) -> List[str]:
    url = _kv_url()
    if url:
        import httpx
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"{url}/lrange/{key}/{start}/{end}",
                headers={"Authorization": f"Bearer {_kv_token()}"},
                timeout=5,
            )
            data = r.json()
            return data.get("result", [])
    lst = _lists.get(key, [])
    if end == -1:
        return lst[start:]
    return lst[start:end + 1]


async def kv_lrem(key: str, value: str) -> None:
    url = _kv_url()
    if url:
        import httpx
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{url}/lrem/{key}/0/{value}",
                headers={"Authorization": f"Bearer {_kv_token()}"},
                timeout=5,
            )
    else:
        if key in _lists:
            _lists[key] = [v for v in _lists[key] if v != value]


# ─── ARTICLE HELPERS ───────────────────────────────────────────────────────

def make_slug(title: str, article_id: str) -> str:
    base = title.lower()
    base = "".join(c if c.isalnum() or c in " -" else "" for c in base)
    base = "-".join(base.split())[:80]
    return f"{base}-{article_id[:6]}"


async def get_all_articles(
    category: Optional[str] = None,
    status: Optional[str] = "published",
    limit: int = 20,
    offset: int = 0,
) -> tuple[List[dict], int]:
    ids = await kv_lrange("article:ids", 0, -1)
    articles = []
    for aid in ids:
        raw = await kv_get(f"article:{aid}")
        if raw:
            a = json.loads(raw) if isinstance(raw, str) else raw
            articles.append(a)

    if status and status != "all":
        articles = [a for a in articles if a.get("status") == status]
    if category:
        articles = [a for a in articles if a.get("category") == category]

    articles.sort(key=lambda a: a.get("created_at", ""), reverse=True)
    total = len(articles)
    return articles[offset: offset + limit], total


async def create_article(data: ArticleCreate) -> dict:
    article_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    article = {
        "id": article_id,
        "slug": make_slug(data.title, article_id),
        "title": data.title,
        "content": data.content,
        "excerpt": data.excerpt or data.content.replace("<", " <").replace(">", "> ")[:200],
        "category": data.category,
        "author": data.author or "NEXUS Editorial",
        "tags": data.tags or [],
        "status": data.status or "published",
        "cover_image": data.cover_image or "",
        "seo_title": data.seo_title or data.title,
        "seo_description": data.seo_description or data.excerpt or "",
        "views": 0,
        "created_at": now,
        "updated_at": now,
    }

    await kv_set(f"article:{article_id}", json.dumps(article))
    await kv_lpush("article:ids", article_id)
    return article
