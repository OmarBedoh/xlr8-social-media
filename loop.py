"""
loop.py — master scheduler
# -*- coding: utf-8 -*-
Turn on your PC, run this once, and the system runs itself.

Schedule:
  Every 30 minutes  → agent.run()  (generate content into queue)
  Every day at 8AM  → poster.post_daily()  (post from queue to all platforms)
"""

import sys
import time
from datetime import datetime, date

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from agent  import run  as run_agent
from poster import post_daily
from tools  import log, get_queue_count
from config import POST_HOUR, POST_MINUTE, AGENT_INTERVAL_MINUTES

# ===== STARTUP =====
print()
print("=" * 46)
print("   PT BUSINESS OS -- STARTING UP")
print("=" * 46)
print(f"  Agent runs every {AGENT_INTERVAL_MINUTES} min")
print(f"  Daily post fires at {POST_HOUR:02d}:{POST_MINUTE:02d}")
print()

log("=== System started ===")

# If queue is empty at startup (e.g. fresh cloud container), generate immediately
if get_queue_count() == 0:
    log("Queue empty on startup — running agent immediately to fill it")
    try:
        run_agent()
    except Exception as e:
        log(f"Startup agent run failed: {e}")

last_agent_run  = datetime.now()   # treat startup agent run as first run
last_post_date  = None             # date of last daily post

while True:
    now   = datetime.now()
    today = date.today()

    # ── DAILY POST (8AM or later if PC was off at 8AM) ────────────────
    past_post_time = (now.hour > POST_HOUR) or (now.hour == POST_HOUR and now.minute >= POST_MINUTE)
    if past_post_time and last_post_date != today:
        log(f"Daily post window reached ({now.strftime('%H:%M')})")
        try:
            post_daily()
        except Exception as e:
            log(f"Daily post crashed: {e}")
        last_post_date = today

    # ── AGENT RUN (every N minutes) ────────────────────────────────────
    elapsed = (
        (now - last_agent_run).total_seconds()
        if last_agent_run else float("inf")
    )

    if elapsed >= AGENT_INTERVAL_MINUTES * 60:
        try:
            run_agent()
        except Exception as e:
            log(f"Agent run crashed: {e}")
            print(f"  Agent error: {e}")
        last_agent_run = now

    # ── SLEEP 60s BETWEEN CHECKS ───────────────────────────────────────
    time.sleep(60)
