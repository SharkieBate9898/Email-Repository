# Email Repository Web App

A complete Flask-based email-style web app with:

- Dashboard home page
- Inbox + Sent folders
- Message detail view
- Compose form with validation

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Then open: `http://localhost:5000`

## Run tests

```bash
pip install pytest
pytest -q
```
