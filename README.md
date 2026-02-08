# URL Shortener Service

Lightweight URL shortening service built with FastAPI & SQLite.

## Features

- Create short URLs with custom codes
- Fast redirects with click tracking
- Update & delete URLs
- URL expiration support

## Quick Start

```bash
# Install dependencies
poetry install

# Run server
poetry run uvicorn src.main:app --reload

# Run tests
poetry run pytest
```

## API Docs

- Swagger UI: http://localhost:8000/docs

