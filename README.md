# Lead Outreach Assistant

This prototype scans a list of business websites, scores them for SEO, design, and
viewability, and drafts a human-sounding outreach email when the scores are low.
A background worker runs continuously after you click **Start Assistant** and
stops when you click **Stop Assistant**.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Visit `http://localhost:5000` and use the toggle button to start or stop the
assistant.

## Email setup (send to yourself)

Configure these environment variables before starting the server:

```bash
export TARGET_EMAIL="you@example.com"
export SMTP_HOST="smtp.gmail.com"
export SMTP_PORT="587"
export SMTP_USERNAME="your.email@gmail.com"
export SMTP_PASSWORD="your-app-password"
export SMTP_USE_TLS="true"
export EMAIL_FROM="Your Name <your.email@gmail.com>"
```

> **Note:** For Gmail, you'll need an App Password. The assistant will log a
> message instead of sending emails if the SMTP settings are missing.

## Customize what gets scanned

Update the `BUSINESSES` list in `app.py` with the business types and URLs you
want the assistant to evaluate. Use the UI fields to set the target location
and industry that should be referenced in the outreach email.

## Controls

- `SCAN_INTERVAL_SECONDS` (default: 300) controls how long the worker sleeps
  between scan cycles.
