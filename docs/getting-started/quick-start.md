# Quick Start

This guide mirrors the shortest path to run LabFlow locally.

## Local Development

1. Create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2. Install dependencies:

```powershell
pip install -r requirements.txt
pip install -r dev-requirements.txt
```

3. Start the API server:

```powershell
uvicorn app.main:app --reload
```

API will be available at http://localhost:8000.

## Docker

```bash
# Copy environment file
cp .env.example .env

# Edit .env and set SECRET_KEY

# Start containers
docker-compose up -d
```

API docs: http://localhost:8000/docs
