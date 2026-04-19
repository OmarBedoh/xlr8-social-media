"""
poster.py — social media posting engine
Reads the content queue and posts to Threads, Instagram, Facebook.
Fetches images from Pexels for Instagram posts.
"""

import time
import requests
from datetime import datetime

from config import (
    THREADS_USER_ID, THREADS_ACCESS_TOKEN,
    META_PAGE_ID, META_PAGE_TOKEN, META_IG_ACCOUNT_ID,
    PEXELS_API_KEY,
)
from tools import log, get_all_queued, mark_posted, already_posted_today


# ===== PEXELS IMAGE FETCH =====

def get_pexels_image(topic):
    """Fetch a portrait-oriented gym image from Pexels. Returns URL or None."""
    if not PEXELS_API_KEY:
        log("Pexels key not set — no image")
        return None
    try:
        query = f"gym fitness strength training {topic}"[:100]
        r = requests.get(
            "https://api.pexels.com/v1/search",
            headers={"Authorization": PEXELS_API_KEY},
            params={"query": query, "per_page": 5, "orientation": "portrait"},
            timeout=15,
        )
        r.raise_for_status()
        photos = r.json().get("photos", [])
        if not photos:
            log(f"No Pexels results for: {query[:50]}")
            return None
        # Use portrait format — taller image, better for Instagram
        url = photos[0]["src"].get("portrait") or photos[0]["src"]["large2x"]
        log(f"Pexels image: {url[:70]}...")
        return url
    except Exception as e:
        log(f"Pexels error: {e}")
        return None


# ===== THREADS (Meta Graph API) =====

def post_to_threads(caption, image_url=None):
    """
    Post to Threads via the Threads API (graph.threads.net).
    Supports text-only or image + text posts.
    Max caption length: 500 characters.
    """
    if not all([THREADS_USER_ID, THREADS_ACCESS_TOKEN]):
        log("Threads credentials not configured — skipping")
        return {"success": False, "error": "missing credentials", "platform": "threads"}

    try:
        base = f"https://graph.threads.net/v1.0/{THREADS_USER_ID}"
        text = caption[:500]

        # Step 1: Create media container
        container_data = {
            "text":         text,
            "access_token": THREADS_ACCESS_TOKEN,
        }
        if image_url:
            container_data["media_type"] = "IMAGE"
            container_data["image_url"]  = image_url
        else:
            container_data["media_type"] = "TEXT"

        r1 = requests.post(
            f"{base}/threads",
            data=container_data,
            timeout=30,
        )
        r1.raise_for_status()
        container_id = r1.json().get("id")
        if not container_id:
            log(f"Threads container creation failed: {r1.text}")
            return {"success": False, "error": r1.text, "platform": "threads"}

        # Step 2: Publish (wait briefly for server processing)
        time.sleep(5)
        r2 = requests.post(
            f"{base}/threads_publish",
            data={
                "creation_id":  container_id,
                "access_token": THREADS_ACCESS_TOKEN,
            },
            timeout=30,
        )
        r2.raise_for_status()
        post_id = r2.json().get("id")
        log(f"Posted to Threads — post ID: {post_id}")
        return {"success": True, "id": str(post_id), "platform": "threads"}

    except Exception as e:
        log(f"Threads post failed: {e}")
        return {"success": False, "error": str(e), "platform": "threads"}


# ===== INSTAGRAM (Meta Graph API) =====

def post_to_instagram(caption, hashtags="", image_url=None):
    """
    Post a single-image post to Instagram via Meta Graph API.
    Requires: META_IG_ACCOUNT_ID, META_PAGE_TOKEN, and a public image URL.
    """
    if not all([META_PAGE_TOKEN, META_IG_ACCOUNT_ID]):
        log("Instagram credentials not configured — skipping")
        return {"success": False, "error": "missing credentials", "platform": "instagram"}

    if not image_url:
        log("Instagram requires an image URL — skipping")
        return {"success": False, "error": "no image url", "platform": "instagram"}

    full_caption = f"{caption}\n\n{hashtags}".strip() if hashtags else caption

    try:
        base = f"https://graph.facebook.com/v19.0/{META_IG_ACCOUNT_ID}"

        # Step 1: Create media container
        # NOTE: Use data= (POST body) not params= (URL query) — captions are too long for URLs
        r1 = requests.post(
            f"{base}/media",
            data={
                "image_url":    image_url,
                "caption":      full_caption,
                "access_token": META_PAGE_TOKEN,
            },
            timeout=30,
        )
        r1.raise_for_status()
        container_id = r1.json().get("id")
        if not container_id:
            log(f"IG container creation failed: {r1.text}")
            return {"success": False, "error": r1.text, "platform": "instagram"}

        # Step 2: Wait for Instagram to process the container, then publish
        time.sleep(5)
        r2 = requests.post(
            f"{base}/media_publish",
            data={
                "creation_id":  container_id,
                "access_token": META_PAGE_TOKEN,
            },
            timeout=30,
        )
        r2.raise_for_status()
        post_id = r2.json().get("id")
        log(f"Posted to Instagram — post ID: {post_id}")
        return {"success": True, "id": str(post_id), "platform": "instagram"}

    except Exception as e:
        log(f"Instagram post failed: {e}")
        return {"success": False, "error": str(e), "platform": "instagram"}


# ===== FACEBOOK (Meta Graph API) =====

def post_to_facebook(caption, hashtags="", image_url=None):
    """Post to a Facebook Page via Graph API."""
    if not all([META_PAGE_TOKEN, META_PAGE_ID]):
        log("Facebook credentials not configured — skipping")
        return {"success": False, "error": "missing credentials", "platform": "facebook"}

    full_caption = f"{caption}\n\n{hashtags}".strip() if hashtags else caption

    try:
        endpoint = f"https://graph.facebook.com/v19.0/{META_PAGE_ID}/"

        # NOTE: Use data= (POST body) not params= (URL query) — captions are too long for URLs
        # Use /feed for all posts (photos endpoint requires pages_manage_posts scope that
        # is often missing from Graph Explorer tokens). Pass image as "link" for preview.
        post_data = {
            "message":      full_caption,
            "access_token": META_PAGE_TOKEN,
        }
        if image_url:
            post_data["link"] = image_url

        r = requests.post(
            endpoint + "feed",
            data=post_data,
            timeout=30,
        )

        r.raise_for_status()
        post_id = r.json().get("id") or r.json().get("post_id")
        log(f"Posted to Facebook — post ID: {post_id}")
        return {"success": True, "id": str(post_id), "platform": "facebook"}

    except Exception as e:
        log(f"Facebook post failed: {e}")
        return {"success": False, "error": str(e), "platform": "facebook"}


# ===== MAIN POSTING ENGINE =====

def post_platform(platform, data):
    """Route a queued item to the correct platform poster."""
    caption  = data.get("caption", "")
    hashtags = data.get("hashtags", "")
    topic    = data.get("extra", {}).get("topic", "fitness strength training")

    if platform == "threads":
        full = f"{caption}\n\n{hashtags}".strip() if hashtags else caption
        image_url = get_pexels_image(topic)
        return post_to_threads(full, image_url)

    elif platform == "instagram":
        image_url = get_pexels_image(topic)
        return post_to_instagram(caption, hashtags, image_url)

    elif platform == "facebook":
        image_url = get_pexels_image(topic)
        return post_to_facebook(caption, hashtags, image_url)

    else:
        log(f"Unknown platform: {platform}")
        return {"success": False, "error": f"unknown platform: {platform}"}


def post_daily():
    """
    Post one item per platform from the queue.
    Called once per day at the scheduled time.
    """
    print("\n" + "=" * 52)
    print(f"  DAILY POST — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 52)

    log("=== Daily post triggered ===")

    platforms = ["threads", "instagram", "facebook"]
    posted_any = False

    for platform in platforms:
        items = get_all_queued(platform=platform)
        if not items:
            log(f"Queue empty for {platform} — nothing to post")
            continue

        filepath, data = items[0]   # oldest item first
        topic = data.get("extra", {}).get("topic", "")
        log(f"Posting to {platform}: {topic}")

        result = post_platform(platform, data)
        mark_posted(filepath, result)

        if result.get("success"):
            log(f"SUCCESS [{platform}]: {topic}")
            posted_any = True
        else:
            log(f"FAILED [{platform}]: {result.get('error')}")

    if not posted_any:
        log("=== No posts published today ===")
    else:
        log("=== Daily post complete ===")

    return posted_any


if __name__ == "__main__":
    post_daily()
