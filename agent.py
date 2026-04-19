"""
agent.py — autonomous content generation agent
Reads memory → generates fitness content → queues for posting → updates tasks
"""

import re
import sys
import time
import subprocess
import requests
from datetime import datetime

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from config import (
    OLLAMA_URL, OLLAMA_MODEL, OLLAMA_TIMEOUT,
    GROQ_API_KEY,
    NICHE, TARGET_AUDIENCE, BRAND_VOICE, INSTAGRAM_HANDLE
)
from tools import (
    log, read_recent_logs,
    get_tasks, add_task,
    queue_post, get_queue_count, get_recent_published_topics,
    append_file
)


# ===== OLLAMA =====

def _is_ollama_running():
    try:
        r = requests.get("http://localhost:11434/api/tags", timeout=3)
        return r.status_code == 200
    except Exception:
        return False

def _start_ollama():
    """Try to start Ollama in the background."""
    import os, shutil
    exe = shutil.which("ollama") or r"C:\Users\omarb\AppData\Local\Programs\Ollama\ollama.exe"
    if not os.path.exists(exe):
        log("Ollama exe not found — cannot auto-start")
        return False
    try:
        subprocess.Popen(
            [exe, "serve"],
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        log("Ollama launched — waiting 10s for it to start...")
        time.sleep(10)
        return _is_ollama_running()
    except Exception as e:
        log(f"Could not start Ollama: {e}")
        return False

def call_ollama(prompt):
    if not _is_ollama_running():
        log("Ollama not running — attempting auto-start...")
        if not _start_ollama():
            log("Ollama unavailable — will try Groq fallback")
            return None
    try:
        log("Calling Ollama (llama3)...")
        r = requests.post(
            OLLAMA_URL,
            json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
            timeout=OLLAMA_TIMEOUT
        )
        r.raise_for_status()
        result = r.json().get("response", "").strip()
        if not result:
            log("Ollama returned empty response")
            return None
        log("Ollama responded OK")
        return result
    except requests.exceptions.Timeout:
        log(f"Ollama timed out after {OLLAMA_TIMEOUT}s")
        return None
    except Exception as e:
        log(f"Ollama error: {e}")
        return None


# ===== GROQ (free cloud AI — fallback when Ollama is offline) =====

def call_groq(prompt):
    """Use Groq's free API (llama3-70b) when Ollama is unavailable."""
    if not GROQ_API_KEY:
        log("No GROQ_API_KEY set — cannot use Groq fallback")
        return None
    try:
        log("Calling Groq (llama3-70b)...")
        r = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": "llama3-70b-8192",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.7,
                "max_tokens": 2000,
            },
            timeout=60,
        )
        r.raise_for_status()
        result = r.json()["choices"][0]["message"]["content"].strip()
        if not result:
            log("Groq returned empty response")
            return None
        log("Groq responded OK")
        return result
    except Exception as e:
        log(f"Groq error: {e}")
        return None


def call_ai(prompt):
    """Try Ollama first (free, local), fall back to Groq (free, cloud)."""
    result = call_ollama(prompt)
    if result:
        return result
    log("Ollama failed — falling back to Groq...")
    return call_groq(prompt)


# ===== BUILD CONTEXT (MEMORY) =====

def build_context():
    recent_logs   = read_recent_logs(days=2)
    tasks         = get_tasks()
    recent_topics = get_recent_published_topics(n=7)
    queue_count   = get_queue_count()

    avoid_block = ""
    if recent_topics:
        avoid_block = "AVOID these recently posted topics (do NOT repeat):\n" + "\n".join(f"  - {t}" for t in recent_topics)
    else:
        avoid_block = "No posts yet — pick any strong fitness topic."

    return f"""
DATE: {datetime.now().strftime('%A %d %B %Y, %H:%M')}
POSTS IN QUEUE: {queue_count} (target: keep 3-5 queued ahead)

RECENT ACTIVITY (last 2 days):
{recent_logs[:1500]}

CURRENT TASKS:
Todo:
{tasks['todo'][:400]}
Doing:
{tasks['doing'][:200]}

{avoid_block}
"""


# ===== BUILD PROMPT =====

TOPIC_IDEAS = """
Pick ONE topic from this list (or a variation of it) that has NOT been recently posted:
- Strength training beats cardio for fat loss (cite mechanism, not just claim)
- Why most men eat too little protein in a deficit
- The 3x/week full-body programme that busy men actually stick to
- Why bro splits fail for fat loss
- How to lose fat without losing muscle (body recomp)
- Progressive overload explained simply
- The truth about metabolism and age
- Sleep as the most underrated fat loss tool
- How to set up a calorie deficit without crash dieting
- The GLP-1 / Ozempic muscle-loss problem and why lifting fixes it
- What online coaching actually looks like (behind the scenes)
- The 0.5-1% bodyweight/week fat loss rule and why it works
- Cardio vs walking: which is better for fat loss
- Why scale weight fluctuates and how to read it properly
- The fastest way to improve body composition in 90 days
"""

def build_prompt(context):
    return f"""You are an autonomous content operator for a fitness coaching brand.

BRAND CONTEXT:
Niche: {NICHE}
Audience: {TARGET_AUDIENCE}
Voice: {BRAND_VOICE}
Instagram handle: {INSTAGRAM_HANDLE}

SYSTEM CONTEXT:
{context}

TOPIC IDEAS:
{TOPIC_IDEAS}

YOUR TASK:
Generate ONE complete piece of content for today. Choose a topic not in the "AVOID" list above.

RULES:
- Sound human, never robotic or AI-like
- Be specific — use numbers, mechanisms, real examples
- No filler phrases ("It's important to...", "In today's world...", "As a fitness coach...")
- Write like you're talking to a friend who's frustrated they can't lose fat
- Every post must have a specific CTA (DM keyword, save, follow)

OUTPUT FORMAT — use these tags EXACTLY, no other text outside them:

[TOPIC]
One-line topic (e.g. "Why strength training beats cardio for fat loss")
[/TOPIC]

[IG_CAPTION]
Full Instagram caption. Structure:
- Line 1: Bold hook (no hashtags, no emojis yet — just the line)
- 2-3 short paragraphs of value
- Blank line
- CTA (e.g. DM me "LEAN" for X)
- Blank line
- 5-8 relevant hashtags on the last line
[/IG_CAPTION]

[X_POST]
Twitter/X version — max 280 characters. Hook + value + CTA. No hashtags needed.
[/X_POST]

[SLIDE_OUTLINE]
7-slide carousel outline (Slide 1: hook, Slides 2-6: content, Slide 7: CTA).
One bullet per slide, max 15 words each.
[/SLIDE_OUTLINE]

[NEW_TASK]
One specific action task to add to the todo list (e.g. "Research progressive overload study links for next post")
[/NEW_TASK]

[SYSTEM_NOTE]
One short observation about what content angle to push next or what's working.
[/SYSTEM_NOTE]
"""


# ===== PARSE OUTPUT =====

def extract(text, tag):
    """Extract content between [TAG] and [/TAG].
    Also handles Ollama mangling [TAG] → **TAG** or ***TAG*** in markdown output.
    """
    # Normalize: **TAG** or ***TAG*** → [TAG]  (handles opening tags only — closing stays [/TAG])
    normalized = re.sub(r'\*+(' + re.escape(tag) + r')\*+', r'[\1]', text, flags=re.I)
    m = re.search(rf'\[{tag}\](.*?)\[/{tag}\]', normalized, re.S | re.I)
    return m.group(1).strip() if m else None


def parse_and_act(output):
    if not output:
        log("No output to parse — skipping")
        return

    topic        = extract(output, "TOPIC")
    ig_caption   = extract(output, "IG_CAPTION")
    x_post       = extract(output, "X_POST")
    slide_outline = extract(output, "SLIDE_OUTLINE")
    new_task     = extract(output, "NEW_TASK")
    system_note  = extract(output, "SYSTEM_NOTE")

    if not topic or not ig_caption:
        log("Parse failed — missing TOPIC or IG_CAPTION in output")
        log(f"Raw output sample: {output[:300]}")
        return

    # --- Queue Instagram post ---
    # Extract hashtags from end of caption (lines starting with #)
    caption_lines = ig_caption.strip().splitlines()
    hashtag_lines = [l for l in caption_lines if l.strip().startswith("#")]
    body_lines    = [l for l in caption_lines if not l.strip().startswith("#")]
    caption_body  = "\n".join(body_lines).strip()
    hashtags      = " ".join(hashtag_lines).strip()

    queue_post(
        platform="instagram",
        content_type="carousel",
        caption=caption_body,
        hashtags=hashtags,
        extra={"topic": topic, "slide_outline": slide_outline or ""},
    )

    # --- Queue X post ---
    if x_post:
        queue_post(
            platform="x",
            content_type="tweet",
            caption=x_post[:280],
            hashtags="",
            extra={"topic": topic},
        )

    # --- Queue Facebook post (same content as Instagram) ---
    queue_post(
        platform="facebook",
        content_type="post",
        caption=caption_body,
        hashtags=hashtags,
        extra={"topic": topic},
    )

    # --- Save slide outline to content folder ---
    if slide_outline:
        today = datetime.now().strftime("%Y%m%d_%H%M%S")
        append_file(
            f"content/slides/{today}_slides.md",
            f"# {topic}\n\n{slide_outline}"
        )

    # --- Update tasks ---
    if new_task:
        result = add_task(new_task)
        log(f"Task [{result}]: {new_task}")

    # --- Save system note ---
    if system_note:
        today_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        append_file("systems/system_updates.md", f"\n[{today_str}] {system_note}")

    log(f"Generated: {topic}")
    log(f"Queue now has {get_queue_count()} posts")


# ===== MAIN =====

def run():
    print("\n" + "=" * 52)
    print(f"  AGENT — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 52)

    log("=== Agent run started ===")

    try:
        context = build_context()
        prompt  = build_prompt(context)
        output  = call_ai(prompt)   # tries Ollama, falls back to Groq

        if output:
            parse_and_act(output)
            log("=== Agent run complete ===")
        else:
            log("=== Agent run failed (no AI output — Ollama and Groq both unavailable) ===")

    except Exception as e:
        log(f"=== Agent crashed: {e} ===")
        raise


if __name__ == "__main__":
    run()
