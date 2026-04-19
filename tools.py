"""
tools.py — vault operations, task management, content queue
All file operations are sandboxed to BASE_PATH.
"""

import os
import sys
import json
import glob
from datetime import datetime

# Force UTF-8 output on Windows so emoji in AI content doesn't crash prints
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
from config import (
    BASE_PATH, TASKS_PATH, LOGS_PATH,
    QUEUE_PATH, PUBLISHED_PATH, CONTENT_PATH, SYSTEMS_PATH
)

# ===== PATH SAFETY =====

def _safe(path):
    """Resolve path and ensure it stays inside BASE_PATH."""
    full = os.path.normpath(os.path.join(BASE_PATH, path))
    if not full.startswith(os.path.normpath(BASE_PATH)):
        raise ValueError(f"Path escape blocked: {path}")
    return full


# ===== BASIC FILE OPS =====

def write_file(path, content):
    full = _safe(path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8") as f:
        f.write(content)

def read_file(path):
    full = _safe(path)
    if not os.path.exists(full):
        return None
    with open(full, "r", encoding="utf-8") as f:
        return f.read()

def append_file(path, content):
    full = _safe(path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "a", encoding="utf-8") as f:
        f.write("\n" + content.rstrip() + "\n")


# ===== LOGGING =====

def log(message):
    today = datetime.now().strftime("%Y-%m-%d")
    ts    = datetime.now().strftime("%H:%M:%S")
    path  = os.path.join(LOGS_PATH, f"{today}.md")
    os.makedirs(LOGS_PATH, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(f"[{ts}] {message}\n")
    try:
        print(f"  {message}")
    except UnicodeEncodeError:
        safe = message.encode("ascii", errors="replace").decode("ascii")
        print(f"  {safe}")

def read_recent_logs(days=2):
    """Return last N days of log content for agent context."""
    files = sorted(glob.glob(os.path.join(LOGS_PATH, "*.md")), reverse=True)[:days]
    parts = []
    for f in files:
        with open(f, "r", encoding="utf-8") as fp:
            parts.append(f"=== {os.path.basename(f)} ===\n{fp.read()}")
    return "\n".join(parts) if parts else "No logs yet."


# ===== TASK SYSTEM =====

def _task_path(status):
    return os.path.join(TASKS_PATH, f"{status}.md")

def get_tasks():
    out = {}
    for status in ("todo", "doing", "done"):
        p = _task_path(status)
        out[status] = open(p, encoding="utf-8").read() if os.path.exists(p) else f"# {status.capitalize()}\n"
    return out

def add_task(text, status="todo"):
    path = _task_path(status)
    existing = open(path, encoding="utf-8").read() if os.path.exists(path) else ""
    # Dedup: skip if a very similar task is already there
    if text.lower()[:40] in existing.lower():
        return "duplicate — skipped"
    today = datetime.now().strftime("%Y-%m-%d")
    os.makedirs(TASKS_PATH, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(f"\n- [ ] [{today}] {text}")
    return f"added to {status}"

def mark_task_done(text):
    for status in ("todo", "doing"):
        path = _task_path(status)
        if not os.path.exists(path):
            continue
        content = open(path, encoding="utf-8").read()
        if text.lower()[:30] in content.lower():
            lines = [l for l in content.splitlines() if text.lower()[:30] not in l.lower()]
            with open(path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))
            ts = datetime.now().strftime("%Y-%m-%d %H:%M")
            done_path = _task_path("done")
            with open(done_path, "a", encoding="utf-8") as f:
                f.write(f"\n- [x] [{ts}] {text}")
            return "marked done"
    return "not found"


# ===== CONTENT QUEUE =====

def queue_post(platform, content_type, caption, hashtags="", extra=None):
    """Add a post to the publishing queue. Returns filename."""
    os.makedirs(QUEUE_PATH, exist_ok=True)
    ts       = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{ts}_{platform}_{content_type}.json"
    data = {
        "platform":  platform,
        "type":      content_type,
        "caption":   caption,
        "hashtags":  hashtags,
        "extra":     extra or {},
        "queued_at": datetime.now().isoformat(),
        "status":    "queued",
    }
    with open(os.path.join(QUEUE_PATH, filename), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    log(f"Queued [{platform}] {content_type}: {caption[:60]}...")
    return filename

def get_next_queued(platform=None):
    """Return (filepath, data) for oldest queued item, optionally filtered by platform."""
    files = sorted(glob.glob(os.path.join(QUEUE_PATH, "*.json")))
    for fp in files:
        with open(fp, encoding="utf-8") as f:
            data = json.load(f)
        if data.get("status") == "queued":
            if platform is None or data.get("platform") == platform:
                return fp, data
    return None, None

def get_all_queued(platform=None):
    """Return list of (filepath, data) for all queued items."""
    items = []
    files = sorted(glob.glob(os.path.join(QUEUE_PATH, "*.json")))
    for fp in files:
        with open(fp, encoding="utf-8") as f:
            data = json.load(f)
        if data.get("status") == "queued":
            if platform is None or data.get("platform") == platform:
                items.append((fp, data))
    return items

def mark_posted(filepath, result):
    """Move item from queue to published archive."""
    with open(filepath, encoding="utf-8") as f:
        data = json.load(f)
    data["status"]    = "posted" if result.get("success") else "failed"
    data["posted_at"] = datetime.now().isoformat()
    data["result"]    = result
    os.makedirs(PUBLISHED_PATH, exist_ok=True)
    dest = os.path.join(PUBLISHED_PATH, os.path.basename(filepath))
    with open(dest, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.remove(filepath)

def get_queue_count():
    return len(glob.glob(os.path.join(QUEUE_PATH, "*.json")))

def get_recent_published_topics(n=7):
    """Return list of recently posted captions (for dedup in agent prompt)."""
    files = sorted(glob.glob(os.path.join(PUBLISHED_PATH, "*.json")), reverse=True)[:n]
    topics = []
    for fp in files:
        with open(fp, encoding="utf-8") as f:
            d = json.load(f)
        extra = d.get("extra", {})
        topic = extra.get("topic") or d.get("caption", "")[:80]
        topics.append(f"[{d['platform']}] {topic}")
    return topics

def already_posted_today():
    """True if at least one post was published today."""
    today = datetime.now().strftime("%Y%m%d")
    files = glob.glob(os.path.join(PUBLISHED_PATH, f"{today}*.json"))
    return len(files) > 0
