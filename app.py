import os
import threading
import time
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
LOGS = []
LOG_LOCK = threading.Lock()


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


def generate_email(business, scores):
    issues = ", ".join(scores["issues"]) if scores["issues"] else "a few quick wins"
    subject = f"Quick website wins for {business['name']}"
    body = (
        f"Hi {business['name']} team,\n\n"
        f"I was reviewing local {business['category']} sites and took a quick look at {business['url']}. "
        f"I noticed {issues}. Right now the site scored about {scores['seo']}/100 for SEO, "
        f"{scores['design']}/100 for design, and {scores['viewability']}/100 for viewability.\n\n"
        "If you want, I can share a short, human-friendly audit with screenshots and a priority list of fixes. "
        "No pressure—just happy to help if you want to improve rankings and conversions.\n\n"
        "Would you like me to send that over?\n\n"
        "Best,\n"
        "Your Name"
    )
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

            scores = analyze_site(business["url"])
            low_scores = [
                name
                for name, value in scores.items()
                if name in {"seo", "design", "viewability"} and value < 60
            ]

            if low_scores and target_email:
                subject, body = generate_email(business, scores)
                send_email(target_email, subject, body)
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
    return jsonify({"running": RUN_STATE["running"]})


@app.route("/logs")
def logs():
    with LOG_LOCK:
        return jsonify({"logs": list(LOGS)})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
