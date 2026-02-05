import os
import threading
from datetime import datetime
from email.message import EmailMessage

import requests
from bs4 import BeautifulSoup
from flask import Flask, jsonify, render_template, request

app = Flask(__name__)

BUSINESSES = [
    {
        "name": "Riverbend Dental",
        "category": "Dental Practice",
        "url": "https://example.com",
    },
    {
        "name": "Oak City Landscaping",
        "category": "Landscaping",
        "url": "https://example.org",
    },
    {
        "name": "Brightside Fitness",
        "category": "Gym",
        "url": "https://example.net",
    },
]

RUN_STATE = {
    "running": False,
    "thread": None,
    "stop_event": threading.Event(),
}
SETTINGS = {
    "location": "your area",
    "industry": "local businesses",
    "email_subject_template": "Quick website wins for {business_name}",
    "email_body_template": (
        "Hi {business_name} team,\n\n"
        "I was looking at {industry} websites in {location} and came across {business_url}. "
        "I noticed {issues}. I ran a quick scan and the site landed around "
        "{seo_score}/100 for SEO, {design_score}/100 for design, and "
        "{viewability_score}/100 for viewability.\n\n"
        "If it's helpful, I can send over a short, plain-English audit with screenshots and a "
        "priority list of fixes. No pressure at all—just offering a hand if you want to lift "
        "rankings or conversions.\n\n"
        "Want me to send that over?\n\n"
        "Thanks,\n"
        "Your Name"
    ),
    "followup_subject_template": "Checking in about {business_name}'s website",
    "followup_body_template": (
        "Hi {business_name} team,\n\n"
        "Just following up on my earlier note about {business_url}. "
        "If you're open to it, I can send a quick audit with the top fixes. "
        "Totally fine if now isn't the right time.\n\n"
        "Best,\n"
        "Your Name"
    ),
}
LOGS = []
LOG_LOCK = threading.Lock()
CONTACTS = {}
CONTACT_LOCK = threading.Lock()
FOLLOWUP_AFTER_SECONDS = 86400


def log_event(message):
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    entry = f"[{timestamp}] {message}"
    with LOG_LOCK:
        LOGS.append(entry)
        if len(LOGS) > 200:
            LOGS.pop(0)


def score_seo(soup):
    score = 0
    issues = []
    title = soup.find("title")
    if title and title.text.strip():
        score += 30
    else:
        issues.append("missing a descriptive page title")

    description = soup.find("meta", attrs={"name": "description"})
    if description and description.get("content"):
        score += 30
    else:
        issues.append("missing a meta description")

    h1 = soup.find("h1")
    if h1 and h1.text.strip():
        score += 40
    else:
        issues.append("missing a clear H1 headline")

    return score, issues


def score_design(soup):
    score = 0
    issues = []
    stylesheets = soup.find_all("link", rel="stylesheet")
    if stylesheets:
        score += 50
    else:
        issues.append("no linked stylesheet was detected")

    images = soup.find_all("img")
    if images:
        score += 20
        missing_alt = [img for img in images if not img.get("alt")]
        if missing_alt:
            issues.append("some images are missing alt text")
        else:
            score += 10
    else:
        issues.append("no images were detected")

    if soup.find("nav"):
        score += 20
    else:
        issues.append("navigation structure could be improved")

    return min(score, 100), issues


def score_viewability(soup):
    score = 0
    issues = []
    viewport = soup.find("meta", attrs={"name": "viewport"})
    if viewport and viewport.get("content"):
        score += 50
    else:
        issues.append("missing a mobile viewport meta tag")

    if soup.find("main"):
        score += 20
    else:
        issues.append("missing a main content landmark")

    if soup.find("button") or soup.find("a"):
        score += 30
    else:
        issues.append("no clear call-to-action elements detected")

    return min(score, 100), issues


def analyze_site(url):
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
    except requests.RequestException as exc:
        log_event(f"Failed to fetch {url}: {exc}")
        return {
            "seo": 0,
            "design": 0,
            "viewability": 0,
            "issues": ["site could not be reached"],
        }

    soup = BeautifulSoup(response.text, "html.parser")
    seo_score, seo_issues = score_seo(soup)
    design_score, design_issues = score_design(soup)
    view_score, view_issues = score_viewability(soup)
    issues = seo_issues + design_issues + view_issues
    return {
        "seo": seo_score,
        "design": design_score,
        "viewability": view_score,
        "issues": issues,
    }


def render_template(template, context):
    class SafeDict(dict):
        def __missing__(self, key):
            return "{" + key + "}"

    return template.format_map(SafeDict(context))


def build_email_context(business, scores):
    issues = ", ".join(scores["issues"]) if scores["issues"] else "a few quick wins"
    return {
        "business_name": business["name"],
        "business_url": business["url"],
        "industry": SETTINGS["industry"],
        "location": SETTINGS["location"],
        "issues": issues,
        "seo_score": scores["seo"],
        "design_score": scores["design"],
        "viewability_score": scores["viewability"],
    }


def generate_email(business, scores):
    context = build_email_context(business, scores)
    subject = render_template(SETTINGS["email_subject_template"], context)
    body = render_template(SETTINGS["email_body_template"], context)
    return subject, body


def generate_followup_email(business, scores):
    context = build_email_context(business, scores)
    subject = render_template(SETTINGS["followup_subject_template"], context)
    body = render_template(SETTINGS["followup_body_template"], context)
    return subject, body


def send_email(to_email, subject, body):
    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USERNAME")
    smtp_password = os.getenv("SMTP_PASSWORD")
    smtp_use_tls = os.getenv("SMTP_USE_TLS", "true").lower() == "true"
    sender = os.getenv("EMAIL_FROM", smtp_user or "no-reply@example.com")

    if not (smtp_host and smtp_user and smtp_password):
        log_event("SMTP credentials not set. Email send skipped.")
        return False

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = sender
    message["To"] = to_email
    message.set_content(body)

    import smtplib

    with smtplib.SMTP(smtp_host, smtp_port) as smtp:
        if smtp_use_tls:
            smtp.starttls()
        smtp.login(smtp_user, smtp_password)
        smtp.send_message(message)

    log_event(f"Email sent to {to_email} with subject '{subject}'.")
    return True


def run_worker():
    log_event("Worker started.")
    target_email = os.getenv("TARGET_EMAIL")
    interval = int(os.getenv("SCAN_INTERVAL_SECONDS", "300"))

    while not RUN_STATE["stop_event"].is_set():
        for business in BUSINESSES:
            if RUN_STATE["stop_event"].is_set():
                break

            industry = SETTINGS["industry"].strip().lower()
            if industry and industry != "all" and industry not in business["category"].lower():
                log_event(
                    f"Skipping {business['name']} (category {business['category']}) "
                    f"because it does not match '{SETTINGS['industry']}'."
                )
                continue

            scores = analyze_site(business["url"])
            low_scores = [
                name
                for name, value in scores.items()
                if name in {"seo", "design", "viewability"} and value < 60
            ]

            if low_scores and target_email:
                now = datetime.utcnow()
                with CONTACT_LOCK:
                    contact = CONTACTS.get(business["name"])

                should_send = False
                send_followup = False

                if contact is None:
                    should_send = True
                elif contact.get("replied"):
                    log_event(f"Skipping {business['name']} because they replied already.")
                else:
                    last_sent = contact.get("last_sent")
                    if last_sent and (now - last_sent).total_seconds() >= FOLLOWUP_AFTER_SECONDS:
                        should_send = True
                        send_followup = True
                    else:
                        log_event(
                            f"Waiting to follow up with {business['name']} (last sent {last_sent})."
                        )

                if should_send:
                    if send_followup:
                        subject, body = generate_followup_email(business, scores)
                    else:
                        subject, body = generate_email(business, scores)

                    if send_email(target_email, subject, body):
                        with CONTACT_LOCK:
                            existing = CONTACTS.get(business["name"], {})
                            count = existing.get("count", 0) + 1
                            CONTACTS[business["name"]] = {
                                "name": business["name"],
                                "url": business["url"],
                                "count": count,
                                "first_sent": existing.get("first_sent", now),
                                "last_sent": now,
                                "replied": existing.get("replied", False),
                            }
            elif low_scores:
                log_event(
                    f"Low scores found for {business['name']} but TARGET_EMAIL is not set."
                )
            else:
                log_event(
                    f"{business['name']} looks healthy. Scores: SEO {scores['seo']}, "
                    f"Design {scores['design']}, Viewability {scores['viewability']}."
                )

        log_event(f"Sleeping for {interval} seconds before next scan.")
        RUN_STATE["stop_event"].wait(interval)

    log_event("Worker stopped.")


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/start", methods=["POST"])
def start():
    if RUN_STATE["running"]:
        return jsonify({"status": "already_running"})

    RUN_STATE["stop_event"].clear()
    thread = threading.Thread(target=run_worker, daemon=True)
    RUN_STATE["thread"] = thread
    RUN_STATE["running"] = True
    thread.start()
    return jsonify({"status": "started"})


@app.route("/stop", methods=["POST"])
def stop():
    if not RUN_STATE["running"]:
        return jsonify({"status": "not_running"})

    RUN_STATE["stop_event"].set()
    RUN_STATE["running"] = False
    return jsonify({"status": "stopping"})


@app.route("/status")
def status():
    return jsonify(
        {
            "running": RUN_STATE["running"],
            "settings": SETTINGS,
        }
    )


@app.route("/settings", methods=["POST"])
def update_settings():
    payload = request.get_json(silent=True) or {}
    for key in [
        "location",
        "industry",
        "email_subject_template",
        "email_body_template",
        "followup_subject_template",
        "followup_body_template",
    ]:
        if key in payload and (payload[key] or "").strip():
            SETTINGS[key] = payload[key].strip()

    log_event(
        f"Settings updated: location='{SETTINGS['location']}', "
        f"industry='{SETTINGS['industry']}'."
    )
    return jsonify({"status": "updated", **SETTINGS})


@app.route("/contacts")
def contacts():
    with CONTACT_LOCK:
        contacts_list = []
        for entry in CONTACTS.values():
            contacts_list.append(
                {
                    **entry,
                    "first_sent": entry["first_sent"].isoformat()
                    if entry.get("first_sent")
                    else None,
                    "last_sent": entry["last_sent"].isoformat()
                    if entry.get("last_sent")
                    else None,
                }
            )
    contacts_list.sort(key=lambda item: item["last_sent"] or "", reverse=True)
    return jsonify({"contacts": contacts_list})


@app.route("/contacts/reply", methods=["POST"])
def mark_replied():
    payload = request.get_json(silent=True) or {}
    name = (payload.get("name") or "").strip()
    if not name:
        return jsonify({"status": "missing_name"}), 400

    with CONTACT_LOCK:
        if name not in CONTACTS:
            return jsonify({"status": "not_found"}), 404
        CONTACTS[name]["replied"] = True

    log_event(f"Marked {name} as replied.")
    return jsonify({"status": "updated"})


@app.route("/logs")
def logs():
    with LOG_LOCK:
        return jsonify({"logs": list(LOGS)})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
