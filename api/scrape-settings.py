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
        {"id": "bbc-news",      "name": "BBC News",       "rss_url": "https://feeds.bbci.co.uk/news/rss.xml",                "enabled": True,  "category": ""},
        {"id": "reuters",       "name": "Reuters",        "rss_url": "https://feeds.reuters.com/reuters/topNews",             "enabled": True,  "category": ""},
        {"id": "ap-news",       "name": "AP News",        "rss_url": "https://feeds.apnews.com/apnews/topnews",               "enabled": True,  "category": ""},
        {"id": "aljazeera",     "name": "Al Jazeera",     "rss_url": "https://www.aljazeera.com/xml/rss/all.xml",             "enabled": True,  "category": ""},
        {"id": "the-guardian",  "name": "The Guardian",   "rss_url": "https://www.theguardian.com/world/rss",                "enabled": True,  "category": ""},
        {"id": "techcrunch",    "name": "TechCrunch",     "rss_url": "https://techcrunch.com/feed/",                          "enabled": True,  "category": "Technology"},
        {"id": "the-verge",     "name": "The Verge",      "rss_url": "https://www.theverge.com/rss/index.xml",               "enabled": True,  "category": "Technology"},
        {"id": "wired",         "name": "Wired",          "rss_url": "https://www.wired.com/feed/rss",                        "enabled": False, "category": "Technology"},
        {"id": "ars-technica",  "name": "Ars Technica",   "rss_url": "https://feeds.arstechnica.com/arstechnica/index",       "enabled": False, "category": "Technology"},
        {"id": "nasa",          "name": "NASA",           "rss_url": "https://www.nasa.gov/rss/dyn/breaking_news.rss",        "enabled": False, "category": "Science"},
        {"id": "sci-american",  "name": "Scientific American", "rss_url": "https://www.scientificamerican.com/platform/morgue/rss/sciam-news-feed.xml", "enabled": False, "category": "Science"},
        {"id": "nature",        "name": "Nature",         "rss_url": "https://www.nature.com/nature.rss",                    "enabled": False, "category": "Science"},
        {"id": "bbc-business",  "name": "BBC Business",   "rss_url": "https://feeds.bbci.co.uk/news/business/rss.xml",        "enabled": False, "category": "Business"},
        {"id": "bbc-sport",     "name": "BBC Sport",      "rss_url": "https://feeds.bbci.co.uk/sport/rss.xml",               "enabled": False, "category": "Sports"},
        {"id": "espn",          "name": "ESPN",           "rss_url": "https://www.espn.com/espn/rss/news",                   "enabled": False, "category": "Sports"},
        {"id": "variety",       "name": "Variety",        "rss_url": "https://variety.com/feed/",                            "enabled": False, "category": "Entertainment"},
        {"id": "bbc-health",    "name": "BBC Health",     "rss_url": "https://feeds.bbci.co.uk/news/health/rss.xml",          "enabled": False, "category": "Health"},
        {"id": "who",           "name": "WHO News",       "rss_url": "https://www.who.int/rss-feeds/news-english.xml",        "enabled": False, "category": "Health"},
    ],
    "max_per_source":      15,
    "default_category":    "",
    "content_min_chars":   60,
    "auto_excerpt_length": 200,
}