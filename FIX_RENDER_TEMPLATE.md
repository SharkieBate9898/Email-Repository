# Fix for `TypeError: render_template() missing 1 required positional argument: 'context'`

Your traceback shows this call in `app.py`:

```python
return render_template("index.html")
```

That signature is not Flask's `render_template`. It looks like the `render_template` function from Starlette/FastAPI templating (`Jinja2Templates`) where you must pass a context dictionary.

## What to change

If your app is Flask, make sure your import is:

```python
from flask import Flask, render_template
```

Then this is valid:

```python
return render_template("index.html")
```

If your app is using Starlette/FastAPI templates (`templates = Jinja2Templates(...)`), change the route return to:

```python
return templates.TemplateResponse(
    "index.html",
    {"request": request}
)
```

(or if you are intentionally calling a Starlette-style `render_template`, pass context explicitly):

```python
return render_template("index.html", {"request": request})
```

## Why this happened

A common cause is a name collision where a non-Flask `render_template` function was imported and shadowed Flask's `render_template`.

## Quick checklist

1. Check your imports at top of `app.py`.
2. Keep only one templating stack (Flask *or* FastAPI/Starlette style).
3. Restart the dev server after fixing imports.
