"""
Pushover push notifications for highly-relevant NEW jobs.

Called by scrape_jobs.save_jobs_output() with each run's new_jobs. It is a
no-op unless BOTH PUSHOVER_TOKEN and PUSHOVER_USER env vars are set (so local
runs and forks without Pushover are unaffected). It dedupes against
notified.json so the same role is never pushed twice — across sources or runs.

"Highly relevant" = a posting that either
  • touches a priority topic (microplastics, ecotoxicology, endocrine-disrupting
    chemicals, R/Shiny — mirrors STAR_TERMS in triage.html), or
  • scores >= NOTIFY_MIN_FIT (default 75) on a compact port of the dashboard's
    resume-fit model.

Set up (GitHub → Settings → Secrets and variables → Actions):
  PUSHOVER_TOKEN   your Pushover application/API token
  PUSHOVER_USER    your Pushover user key
Optional: NOTIFY_MIN_FIT (default 75) — lower to get more (less selective) pings.
"""

import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
NOTIFIED_PATH = os.path.join(SCRIPT_DIR, "notified.json")
PUSHOVER_URL = "https://api.pushover.net/1/messages.json"
MAX_PUSHES_PER_RUN = 8     # cap individual pings; the rest get one summary
NOTIFIED_KEEP = 600        # remember this many recent jobs to avoid repeats

# Priority-topic stars — keep in sync with STAR_TERMS in triage.html.
STAR_TERMS = [
    ("microplastics", re.compile(r'microplastic|nanoplastic|microfiber', re.I)),
    ("ecotoxicology", re.compile(r'ecotoxicolog', re.I)),
    ("endocrine-disrupting chemicals", re.compile(r'endocrine[\s-]?disrupt|\bedcs?\b', re.I)),
    ("R/Shiny", re.compile(r'\brshiny\b|\br[\s-]?shiny\b|shiny\s*(?:app|dashboard|server)|\bshiny\b', re.I)),
]

# Compact resume-fit (port of FIT_TERMS in triage.html). Title counts x3.
FIT_TERMS = [
    (re.compile(r'microplastic|nanoplastic|plastic pollution', re.I), 12),
    (re.compile(r'ecotoxicolog', re.I), 12),
    (re.compile(r'risk assess|human health risk|ecological risk', re.I), 11),
    (re.compile(r'\bexposure\b|exposure assess', re.I), 10),
    (re.compile(r'\bqsar\b|read-across', re.I), 11),
    (re.compile(r'\bpfas\b|perfluoro|per- and polyfluoro', re.I), 10),
    (re.compile(r'toxicolog', re.I), 8),
    (re.compile(r'pharmacokinetic|toxicokinetic|\bpbpk\b', re.I), 8),
    (re.compile(r'dose.response|benchmark dose', re.I), 7),
    (re.compile(r'computational tox|new approach method|\bnam\b|in vitro', re.I), 8),
    (re.compile(r'drinking water|water quality', re.I), 7),
    (re.compile(r'hazard assess', re.I), 6),
    (re.compile(r'endocrine', re.I), 5),
    (re.compile(r'environmental health|environmental chemist', re.I), 4),
    (re.compile(r'cheminformatic|chemical safety|chemical risk', re.I), 5),
]


def _min_fit() -> int:
    try:
        return int(os.environ.get("NOTIFY_MIN_FIT", "75"))
    except ValueError:
        return 75


def _stars(text: str) -> list:
    return [name for name, rx in STAR_TERMS if rx.search(text)]


def _fit(title: str, body: str) -> int:
    score = 0
    for rx, w in FIT_TERMS:
        if rx.search(title):
            score += w * 3
        elif rx.search(body):
            score += w
    return max(0, min(100, round(score * 1.6)))


def relevance(job: dict) -> tuple[bool, list, int]:
    title = job.get("title", "") or ""
    body = f"{job.get('company', '')} {job.get('description', '')}"
    stars = _stars(f"{title} {body}")
    fit = _fit(title, body)
    return (bool(stars) or fit >= _min_fit()), stars, fit


def _identity(job: dict) -> str:
    co = re.sub(r'[^a-z0-9]', '', (job.get("company", "") or "").lower())
    ti = re.sub(r'[^a-z0-9]', '', (job.get("title", "") or "").lower())
    return f"{co}|{ti}"


def _load_notified() -> dict:
    try:
        with open(NOTIFIED_PATH) as f:
            data = json.load(f)
            data.setdefault("ids", [])
            return data
    except (FileNotFoundError, json.JSONDecodeError):
        return {"ids": []}


def _save_notified(data: dict):
    data["ids"] = data["ids"][-NOTIFIED_KEEP:]
    with open(NOTIFIED_PATH, "w") as f:
        json.dump(data, f)


def send_pushover(token: str, user: str, *, title: str, message: str,
                  url: str = "", url_title: str = "", priority: int = 0) -> bool:
    body = {"token": token, "user": user, "title": title[:250],
            "message": message[:1024], "priority": priority}
    if url:
        body["url"] = url
        body["url_title"] = url_title or "View posting"
    data = urllib.parse.urlencode(body).encode()
    try:
        with urllib.request.urlopen(urllib.request.Request(PUSHOVER_URL, data=data), timeout=15) as r:
            return 200 <= r.status < 300
    except urllib.error.HTTPError as e:
        # Pushover returns a JSON body with the specific error (bad token/user…).
        try:
            detail = e.read().decode("utf-8", "ignore")
        except Exception:
            detail = ""
        print(f"  ⚠️  Pushover HTTP {e.code}: {detail[:300]}")
        return False
    except Exception as e:
        print(f"  ⚠️  Pushover send failed: {e}")
        return False


def notify_new_jobs(new_jobs: list, source_label: str = ""):
    """Push the highly-relevant, not-yet-notified entries of new_jobs."""
    token = os.environ.get("PUSHOVER_TOKEN")
    user = os.environ.get("PUSHOVER_USER")
    if not token or not user:
        return  # notifications disabled — no creds

    notified = _load_notified()
    seen = set(notified["ids"])
    picks = []
    for job in new_jobs:
        ident = _identity(job)
        if ident in seen:
            continue
        relevant, stars, fit = relevance(job)
        if not relevant:
            continue
        seen.add(ident)
        notified["ids"].append(ident)
        picks.append((job, stars, fit))

    if not picks:
        _save_notified(notified)
        return

    # Starred first, then highest fit.
    picks.sort(key=lambda p: (-len(p[1]), -p[2]))
    sent = 0
    for job, stars, fit in picks[:MAX_PUSHES_PER_RUN]:
        tag = ("★ " + ", ".join(stars)) if stars else f"fit {fit}/100"
        msg = f"{job.get('company', '?')} — {job.get('location', '')}\n{tag}"
        if job.get("salary"):
            msg += f" · {job['salary']}"
        send_pushover(
            token, user,
            title=f"🧪 {job.get('title', 'New role')}",
            message=msg,
            url=job.get("url", ""), url_title="Open posting",
            priority=1 if stars else 0,   # priority topics ping with high priority
        )
        sent += 1

    extra = len(picks) - sent
    if extra > 0:
        send_pushover(token, user, title="🧪 More relevant roles",
                      message=f"+{extra} more relevant new role(s) — open the dashboard.")
    print(f"  📲 Pushover: notified {sent} relevant role(s)"
          + (f" (+{extra} summarized)" if extra else ""))
    _save_notified(notified)


def send_test() -> bool:
    """Send a single test push to verify the Pushover setup end-to-end.
    Returns True on success. Prints a clear diagnosis on failure."""
    token = os.environ.get("PUSHOVER_TOKEN")
    user = os.environ.get("PUSHOVER_USER")
    print(f"PUSHOVER_TOKEN: {'(set)' if token else '(MISSING)'}")
    print(f"PUSHOVER_USER:  {'(set)' if user else '(MISSING)'}")
    if not token or not user:
        print("\n❌ Both PUSHOVER_TOKEN and PUSHOVER_USER must be set.\n"
              "   • Locally:  PUSHOVER_TOKEN=… PUSHOVER_USER=… python notify.py --test\n"
              "   • On GitHub: add them as Actions secrets, then run the "
              "'Test Pushover Notification' workflow.")
        return False
    ok = send_pushover(
        token, user,
        title="🧪 Job_Scraper — test notification",
        message=("Pushover is wired up correctly. You'll get pings like this for "
                 "highly-relevant new roles: microplastics, ecotoxicology, "
                 "endocrine-disrupting chemicals, R/Shiny, or a high resume-fit score."),
        url="https://scottcoffin.github.io/Job_Scraper/triage.html",
        url_title="Open dashboard",
        priority=0,
    )
    print("\n✅ Test notification sent — check your phone." if ok
          else "\n❌ Send failed (see the error above — usually a wrong token or user key).")
    return ok


if __name__ == "__main__":
    # `python notify.py` or `python notify.py --test` → send a test push.
    import sys
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # let emoji print on Windows too
    except Exception:
        pass
    raise SystemExit(0 if send_test() else 1)
