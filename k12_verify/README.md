# K12 Verify - SheerID Teacher Verification Tool

A standalone web application for K12 teacher verification using SheerID.

## Features

- Web UI - Clean 2-column interface with live logs
- REST API - Full API for integration  
- Real-time Updates - WebSocket for live verification progress
- SQLite Database - Fast teacher data storage
- Docker Support - Easy VPS deployment

## Quick Start (Local)

### 1. Install Dependencies

```bash
cd k12_verify
pip install -r requirements.txt
playwright install chromium
```

### 2. Migrate Teacher Data

```bash
python -m app.db.migrate
```

### 3. Run Server

```bash
python run.py
```

Open http://localhost:8000 in your browser.

---

## VPS Deployment

### Option 1: Docker (Recommended)

```bash
# Clone/Upload project to VPS
cd k12_verify

# Build and run with Docker Compose
docker-compose up -d

# View logs
docker-compose logs -f
```

### Option 2: Docker Manual

```bash
# Build image
docker build -t k12-verify .

# Run container
docker run -d -p 8000:8000 --name k12-verify k12-verify
```

### Option 3: Direct Python

```bash
# Install dependencies
pip install -r requirements.txt
playwright install chromium --with-deps

# Run with gunicorn (production)
pip install gunicorn
gunicorn -w 4 -k uvicorn.workers.UvicornWorker app.main:app --bind 0.0.0.0:8000
```

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Web UI |
| POST | `/api/verify` | Start verification |
| GET | `/api/status/{task_id}` | Check status |
| GET | `/api/teachers` | List teachers |
| GET | `/api/stats` | Dashboard stats |
| WS | `/api/ws/verify/{task_id}` | Real-time log stream |
| GET | `/health` | Health check |
| GET | `/docs` | API documentation (Swagger) |

---

## Project Structure

```
k12_verify/
├── run.py              # Entry point
├── requirements.txt    # Python dependencies
├── Dockerfile          # Docker image
├── docker-compose.yml  # Docker Compose config
├── .env.example        # Environment template
├── .gitignore          # Git ignore
│
├── app/
│   ├── main.py         # FastAPI app
│   ├── config.py       # Settings
│   ├── api/
│   │   ├── routes.py   # API endpoints
│   │   └── schemas.py  # Pydantic models
│   ├── core/
│   │   ├── verifier.py      # Cookie verification
│   │   └── document_gen.py  # Document generation
│   ├── db/
│   │   ├── database.py # SQLite connection
│   │   ├── models.py   # SQLAlchemy models
│   │   ├── crud.py     # CRUD operations
│   │   └── migrate.py  # JSON to SQLite migration
│   └── templates/
│       └── index.html  # Web UI
│
├── doc_templates/      # Document HTML templates
│   ├── nyc_doe/
│   ├── miami_dade/
│   └── springfield_high/
│
└── data/
    └── k12_verify.db   # SQLite database
```

---

## Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
# Server
HOST=0.0.0.0
PORT=8000

# Database
DATABASE_URL=sqlite:///./data/k12_verify.db

# Playwright
PLAYWRIGHT_HEADLESS=true

# Logging
LOG_LEVEL=INFO
```

---

## Usage

1. Go to http://localhost:8000 (or your VPS IP:8000)
2. Paste cookies from EditThisCookie extension
3. Click **Start Verification**
4. Watch real-time progress in the log panel

---

## Troubleshooting

### Playwright browser not found
```bash
playwright install chromium --with-deps
```

### Permission denied on data folder
```bash
chmod 755 data/
```

### Port already in use
```bash
# Change PORT in .env or docker-compose.yml
PORT=8001
```

---

## License

MIT
