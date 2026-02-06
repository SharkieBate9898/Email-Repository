from __future__ import annotations

from datetime import datetime
from itertools import count
from typing import Any

from flask import Flask, redirect, render_template, request, url_for

app = Flask(__name__)

MESSAGE_ID = count(start=1)
MESSAGES: list[dict[str, Any]] = [
    {
        "id": next(MESSAGE_ID),
        "sender": "welcome@emailrepo.dev",
        "recipient": "you@emailrepo.dev",
        "subject": "Welcome to Email Repository",
        "body": "This starter message confirms your inbox is working.",
        "folder": "inbox",
        "created_at": datetime.utcnow(),
    },
    {
        "id": next(MESSAGE_ID),
        "sender": "you@emailrepo.dev",
        "recipient": "friend@example.com",
        "subject": "Hello from the new app",
        "body": "I just finished building this email web app.",
        "folder": "sent",
        "created_at": datetime.utcnow(),
    },
]


def _messages_in(folder: str) -> list[dict[str, Any]]:
    return sorted(
        [m for m in MESSAGES if m["folder"] == folder],
        key=lambda item: item["created_at"],
        reverse=True,
    )


def _get_message(message_id: int) -> dict[str, Any] | None:
    return next((m for m in MESSAGES if m["id"] == message_id), None)


@app.route("/")
def index() -> str:
    return render_template(
        "index.html",
        inbox_count=len(_messages_in("inbox")),
        sent_count=len(_messages_in("sent")),
        recent_messages=sorted(MESSAGES, key=lambda m: m["created_at"], reverse=True)[:5],
    )


@app.route("/inbox")
def inbox() -> str:
    return render_template("inbox.html", messages=_messages_in("inbox"), folder="Inbox")


@app.route("/sent")
def sent() -> str:
    return render_template("inbox.html", messages=_messages_in("sent"), folder="Sent")


@app.route("/message/<int:message_id>")
def message_detail(message_id: int) -> str:
    message = _get_message(message_id)
    if message is None:
        return render_template("not_found.html", message_id=message_id), 404
    return render_template("message_detail.html", message=message)


@app.route("/compose", methods=["GET", "POST"])
def compose() -> str:
    error = None
    if request.method == "POST":
        recipient = request.form.get("recipient", "").strip()
        subject = request.form.get("subject", "").strip()
        body = request.form.get("body", "").strip()

        if not recipient or not subject or not body:
            error = "All fields are required."
        else:
            MESSAGES.append(
                {
                    "id": next(MESSAGE_ID),
                    "sender": "you@emailrepo.dev",
                    "recipient": recipient,
                    "subject": subject,
                    "body": body,
                    "folder": "sent",
                    "created_at": datetime.utcnow(),
                }
            )
            return redirect(url_for("sent"))

    return render_template("compose.html", error=error)


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
