# Foundation

Shared foundation package for PropertyOps applications. Provides common authentication, API clients, templates, and utilities used across all PropertyOps apps.

## Installation

### For Development
```bash
pip install -e /path/to/foundation
```

### From GitHub
```bash
pip install git+https://github.com/yourusername/foundation.git@v0.1.0
```

## Structure

```
foundation/
├── auth/           # Microsoft SSO authentication
├── clients/        # API clients (QuickBooks, Snowflake, Teams, Email)
├── services/       # Shared business logic
├── utils/          # Utility functions
├── templates/      # Shared Jinja2 templates
│   ├── layouts/    # Base layouts
│   ├── components/ # Reusable components (navbar, footer, etc.)
│   └── emails/     # Email templates
└── static/         # Shared CSS, JS, images
```

## Usage

### Authentication
```python
from foundation.auth import MicrosoftAuth, login_required

auth = MicrosoftAuth()

@app.route('/protected')
@login_required
def protected_route():
    return "You're authenticated!"
```

### API Clients
```python
from foundation.clients import QuickBooks, Snowflake, CompanyMailer

# QuickBooks
qb = QuickBooks()
invoices = qb.get_invoices()

# Snowflake
sf = Snowflake()
data = sf.query("SELECT * FROM table")

# Email
mailer = CompanyMailer()
mailer.send(to="user@example.com", subject="Hello", template="welcome.html")
```

### Templates
```python
from flask import Flask
import foundation

app = Flask(__name__)

# Add foundation templates to Jinja search path
import os
foundation_templates = os.path.join(
    os.path.dirname(foundation.__file__), 
    'templates'
)
app.jinja_loader.searchpath.append(foundation_templates)
```

Then in your app templates:
```html
{% extends "base.html" %}

{% block content %}
  <h1>Your App Content</h1>
{% endblock %}
```

## Development

### Setup
```bash
git clone https://github.com/yourusername/foundation.git
cd foundation
python -m venv venv
source venv/bin/activate  # or .\venv\Scripts\activate on Windows
pip install -e .
```

### Testing
```bash
pytest tests/
```

## Versioning

This package uses semantic versioning. When making changes:

1. Update version in `setup.py`
2. Tag the release: `git tag v0.1.1`
3. Push tags: `git push origin v0.1.1`
4. Apps will pick up the new version on next deployment

## License

Internal use only - PropertyOps
