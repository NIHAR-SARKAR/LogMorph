# LogMorph AI

AI-powered log management and analysis platform for developers, DevOps engineers, and support teams.

<p align="center">
  <img src="logmorph-logo.png" alt="LogMorph Logo" width="256" />
</p>


## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Architecture at a Glance](#architecture-at-a-glance)
- [Technology Stack](#technology-stack)
- [Prerequisites](#prerequisites)
- [Installation & Quick Start](#installation--quick-start)
  - [Local Development](#local-development)
  - [Docker Deployment](#docker-deployment)
  - [Desktop (Tauri)](#desktop-tauri)
- [Configuration](#configuration)
- [API Documentation](#api-documentation)
- [Default Credentials](#default-credentials)
- [Development Workflow](#development-workflow)
- [Deployment Notes](#deployment-notes)
- [Known Issues & Limitations](#known-issues--limitations)
- [License](#license)

## Overview

LogMorph AI is a full-stack log management platform that helps teams aggregate, search, analyze, and monitor log files across multiple projects and environments. It combines a FastAPI backend, a React + TypeScript frontend, and an optional Tauri-based desktop wrapper. The application supports AI-assisted log analysis through multiple providers (OpenAI, Anthropic, Azure OpenAI, Ollama, LM Studio, OpenRouter) and can run entirely offline using a local Ollama instance.

## Features

- **Multi-Project Support**: Organize logs across unlimited projects, environments (dev, QA, staging, production), and log sources.
- **Log Ingestion**: Scan directories or single files; supports `.log` and `.txt` files with recursive scanning and file-pattern filtering.
- **Real-time Monitoring**: Watch configured directories for new or modified log files using `watchdog`.
- **Advanced Search**: Full-text search, regex support, severity filtering, date-range filtering, and saved searches.
- **Custom Parsers**: Visual parser builder supporting regex, JSON, CSV, delimiter, and custom formats; includes built-in templates for generic logs, syslog, nginx, Django, and Spring Boot.
- **AI Analysis**: Summarize logs, analyze exceptions, and chat with AI about your log data.
- **Alert Rules**: Define rules for errors, thresholds, patterns, and more; notify via desktop, email, Slack, Teams, or Discord webhooks.
- **Dashboard**: Visualize log volume, error trends, severity distribution, and top exceptions.
- **Role-Based Access Control**: Admin, Developer, and Viewer roles with JWT authentication.
- **Offline First**: Works completely offline with local AI via Ollama.

## Architecture at a Glance

```
┌─────────────────────────────────────────────────────────────┐
│                     Client Layer                            │
│  ┌─────────────────────┐      ┌─────────────────────────┐  │
│  │  React + Vite SPA   │      │  Tauri Desktop Wrapper  │  │
│  │   (port 3000 dev)   │      │   (Rust + WebView)      │  │
│  └──────────┬──────────┘      └───────────┬─────────────┘  │
└─────────────┼─────────────────────────────┼───────────────┘
              │                             │
              │  HTTP /api/v1               │ spawns Python backend
              ▼                             ▼
┌─────────────────────────────────────────────────────────────┐
│                   FastAPI Backend (port 8000)               │
│  Auth · Projects · Logs · AI · Parsers · Alerts · Settings  │
├─────────────────────────────────────────────────────────────┤
│              SQLAlchemy 2.x ORM · SQLite DB                 │
│         Watchdog file watcher · APScheduler                 │
└─────────────────────────────────────────────────────────────┘
```

For a detailed architecture document, see [ARCHITECTURE.md](./ARCHITECTURE.md).

## Technology Stack

### Backend

| Technology | Purpose |
|------------|---------|
| Python 3.13+ | Runtime |
| FastAPI 0.111 | Web framework & OpenAPI docs |
| SQLAlchemy 2.0.31 | ORM |
| SQLite | Default database (WAL mode enabled) |
| Pydantic v2 | Request/response validation |
| Alembic | Database migrations |
| python-jose + passlib | JWT & bcrypt password hashing |
| Watchdog | Directory monitoring |
| APScheduler | Background jobs |
| httpx | Async HTTP for AI providers |
| openai / anthropic / ollama | Official AI SDKs |
| pandas / numpy | Data processing |
| Rich | Logging output |

### Frontend

| Technology | Purpose |
|------------|---------|
| React 18 | UI library |
| TypeScript 5.5 | Type safety |
| Vite 5 | Build tool & dev server |
| Tailwind CSS 3 | Styling |
| TanStack Query 5 | Server-state & caching |
| Zustand 4 | Client-state |
| React Router 6 | Routing |
| Axios | HTTP client |
| Recharts | Charts |
| Radix UI primitives | Accessible base components |
| class-variance-authority / clsx / tailwind-merge | Component styling utilities |

### Desktop

| Technology | Purpose |
|------------|---------|
| Tauri 2.0.0-beta | Rust-based desktop wrapper |
| Tokio | Async runtime for backend launcher |

## Prerequisites

- **Backend**: Python 3.13 or higher
- **Frontend**: Node.js 18+ and npm
- **Desktop**: Rust toolchain + Cargo
- **Docker** (optional): Docker Engine 20.10+ and Docker Compose 2.0+

## Installation & Quick Start

### Local Development

1. **Clone the repository**

   ```bash
   git clone <repository-url>
   cd LogMorph-ai
   ```

2. **Backend setup**

   ```bash
   cd backend
   python -m venv .venv
   # Linux/macOS:
   source .venv/bin/activate
   # Windows:
   # .venv\Scripts\activate

   pip install -r requirements.txt
   uvicorn app.main:app --reload --port 8000
   ```

   The backend will be available at `http://localhost:8000`.

3. **Frontend setup** (in a new terminal)

   ```bash
   cd frontend
   npm install
   npm run dev
   ```

   The frontend dev server runs at `http://localhost:3000` and proxies `/api` requests to the backend at `http://localhost:8000`.

4. **Open the app** in your browser at `http://localhost:3000`.

### Docker Deployment

A single-container deployment is provided. It builds the frontend and serves the FastAPI backend on port `8000`.

```bash
docker-compose up -d --build
```

Access the application at `http://localhost:8000`.

> **Note**: The current `Dockerfile` builds the frontend but does not mount the built `frontend/dist` as static files in FastAPI. If you need the web UI served from the same container, verify that `backend/app/main.py` registers `StaticFiles` for `../frontend/dist`.

### Desktop (Tauri)

```bash
cd tauri
cargo tauri dev
```

This starts the Vite dev server and opens the app in a native window. Tauri also spawns the Python backend from the executable directory.

> **Known limitation**: The Tauri backend launcher currently starts the Python API on port `8000`, while the frontend dev proxy points to `8000`. For a production Tauri build, additional API origin configuration is required.

## Configuration

Create a `.env` file in the project root (or in `backend/`). Use `.env.example` as a template:

```bash
# Database
DATABASE_URL=sqlite:///./LogMorph.db

# Security
SECRET_KEY=your-super-secret-key-change-in-production

# AI Providers (optional)
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
AZURE_OPENAI_KEY=
AZURE_OPENAI_ENDPOINT=
OPENROUTER_API_KEY=
OLLAMA_HOST=http://localhost:11434
LM_STUDIO_HOST=http://localhost:1234
```

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | Yes | SQLite connection string |
| `SECRET_KEY` | Yes | JWT signing secret |
| `OPENAI_API_KEY` | No | OpenAI API key |
| `ANTHROPIC_API_KEY` | No | Anthropic API key |
| `AZURE_OPENAI_KEY` | No | Azure OpenAI key |
| `AZURE_OPENAI_ENDPOINT` | No | Azure OpenAI endpoint |
| `OPENROUTER_API_KEY` | No | OpenRouter API key |
| `OLLAMA_HOST` | No | Ollama base URL |
| `LM_STUDIO_HOST` | No | LM Studio base URL |

## API Documentation

Once the backend is running, interactive API documentation is available at:

- **Swagger UI**: `http://localhost:8000/api/docs`
- **ReDoc**: `http://localhost:8000/api/redoc`
- **OpenAPI JSON**: `http://localhost:8000/api/openapi.json`
- **Health Check**: `http://localhost:8000/api/health`
- **App Info**: `http://localhost:8000/api/info`

## Default Credentials

On first startup, the backend seeds a default administrator account:

- **Username**: `admin`
- **Password**: `admin123`
- **Email**: `admin@LogMorph.ai`
- **Role**: Admin / Superuser

Change this password immediately in production.

## Development Workflow

### Backend

```bash
cd backend
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
uvicorn app.main:app --reload --port 8000
```

Run database migrations with Alembic:

```bash
cd backend
alembic upgrade head
```

### Frontend

```bash
cd frontend
npm install
npm run dev      # development
npm run build    # production build
npm run preview  # preview production build
```

### Tauri

```bash
cd tauri
cargo tauri dev
```

## Deployment Notes

- **Secret key**: Always change `SECRET_KEY` from the placeholder in production.
- **Database**: SQLite is the default and works well for single-instance deployments. For high-availability or multi-instance deployments, configure a server database (PostgreSQL/MySQL) by updating `DATABASE_URL` and SQLAlchemy connection args.
- **Persistent volumes**: The Docker Compose file mounts `./data` for the SQLite database and `./logs` for log files.
- **CORS**: The backend currently allows all origins (`["*"]`) for development. Restrict this in production.
- **AI providers**: API keys are stored in the database as plain text in the current implementation. Encrypt sensitive fields before production use.
- **Tauri production build**: Ensure the `tauri/icons/` directory exists and configure the backend API origin correctly.

## Known Issues & Limitations

- **Tauri production API origin**: In a production Tauri build the bundled frontend is served via the `tauri://` custom protocol, so relative `/api` calls will not reach the embedded Python backend on `http://localhost:8000`. Serve the built frontend as static files from FastAPI (same origin) or configure the API base URL explicitly for Tauri builds.
- **Frontend static files in Docker**: The built frontend assets are not currently served by FastAPI in the Docker image.
- **AI provider keys**: Stored unencrypted in the database.
- **Alert rule execution**: Alert rules are persisted but the evaluation/notification scheduler is not fully wired in the current codebase.

## License

MIT
