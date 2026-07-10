# LogMorph AI — Architecture

This document describes the architecture, data model, and key design decisions of LogMorph AI.

## Table of Contents

- [High-Level Architecture](#high-level-architecture)
- [Directory Structure](#directory-structure)
- [Backend Architecture](#backend-architecture)
  - [Application Entry Point](#application-entry-point)
  - [Layering](#layering)
  - [Configuration](#configuration)
  - [Database & Models](#database--models)
  - [Routers & API Surface](#routers--api-surface)
  - [Services](#services)
  - [Authentication & Authorization](#authentication--authorization)
  - [File Watching](#file-watching)
  - [AI Integration](#ai-integration)
- [Frontend Architecture](#frontend-architecture)
  - [Entry Points](#entry-points)
  - [State Management](#state-management)
  - [Routing](#routing)
  - [API Client](#api-client)
  - [UI System](#ui-system)
- [Desktop (Tauri) Integration](#desktop-tauri-integration)
- [Data Flow Examples](#data-flow-examples)
- [Deployment Topologies](#deployment-topologies)
- [Known Architectural Gaps](#known-architectural-gaps)

## High-Level Architecture

LogMorph AI follows a layered client-server architecture with an optional native desktop shell.

```
┌──────────────────────────────────────────────────────────────────────┐
│                              Clients                                  │
│  ┌─────────────────────────────┐    ┌─────────────────────────────┐  │
│  │   Browser (React + Vite)    │    │   Tauri Desktop (Rust)      │  │
│  │      http://localhost:3000  │    │      embeds same React SPA  │  │
│  └──────────────┬──────────────┘    └──────────────┬──────────────┘  │
└─────────────────┼──────────────────────────────────┼────────────────┘
                  │                                  │
                  │         HTTP /api/v1            │ spawns Python API
                  ▼                                  ▼
┌──────────────────────────────────────────────────────────────────────┐
│                         FastAPI Backend                               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐ │
│  │    Auth     │  │  Projects   │  │    Logs     │  │ Dashboard   │ │
│  ├─────────────┤  ├─────────────┤  ├─────────────┤  ├─────────────┤ │
│  │    AI       │  │  Parsers    │  │   Alerts    │  │  Settings   │ │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘ │
├──────────────────────────────────────────────────────────────────────┤
│  Services: AIService · ParserEngine · FileWatcherService · Security   │
├──────────────────────────────────────────────────────────────────────┤
│  SQLAlchemy ORM · SQLite (default) · Alembic migrations               │
└──────────────────────────────────────────────────────────────────────┘
```

The frontend is a standard React SPA that communicates with the backend via REST. The Tauri desktop wrapper bundles the same SPA and launches the Python backend as a child process.

## Directory Structure

```
logmorph-ai/
├── backend/                  # FastAPI Python backend
│   ├── app/
│   │   ├── main.py           # FastAPI app factory & startup
│   │   ├── config.py         # Pydantic settings
│   │   ├── database.py       # SQLAlchemy engine & session
│   │   ├── core/             # Security, dependencies, logging
│   │   ├── models/           # SQLAlchemy models
│   │   ├── routers/          # FastAPI route handlers
│   │   ├── schemas/          # Pydantic request/response models
│   │   └── services/         # Business logic services
│   ├── alembic/              # Database migrations
│   ├── requirements.txt
│   └── .venv/                # Python virtual environment
├── frontend/                 # React + TypeScript frontend
│   ├── src/
│   │   ├── main.tsx          # React entry point
│   │   ├── App.tsx           # Router & auth init
│   │   ├── pages/            # Page components
│   │   ├── components/       # Layout & UI primitives
│   │   ├── services/         # API client
│   │   ├── store/            # Zustand stores
│   │   ├── types/            # TypeScript types
│   │   └── lib/              # Utilities
│   ├── index.html
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   └── package.json
├── tauri/                    # Tauri desktop wrapper
│   ├── src/main.rs           # Rust entry point
│   ├── Cargo.toml
│   ├── tauri.conf.json
│   └── build.rs
├── Dockerfile
├── docker-compose.yml
├── .env.example
└── README.md
```

## Backend Architecture

### Application Entry Point

`backend/app/main.py` bootstraps the FastAPI application:

1. Creates SQLAlchemy tables via `Base.metadata.create_all()`.
2. Registers CORS middleware allowing all origins.
3. Mounts API routers under `/api/v1`.
4. Exposes health (`/api/health`) and info (`/api/info`) endpoints.
5. On `startup`, seeds a default admin user and default AI providers if the database is empty.
6. On `shutdown`, stops all file watchers.

### Layering

| Layer | Responsibility | Example Files |
|-------|----------------|---------------|
| Router | HTTP request/response handling | `app/routers/*.py` |
| Schema | Pydantic validation & serialization | `app/schemas/*.py` |
| Model | SQLAlchemy ORM entities | `app/models/*.py` |
| Service | Business logic & external integrations | `app/services/*.py` |
| Core | Cross-cutting concerns (security, deps, logging) | `app/core/*.py` |
| Config | Environment-based settings | `app/config.py` |
| Database | Engine, session, base class | `app/database.py` |

### Configuration

`backend/app/config.py` uses `pydantic-settings` to load environment variables from a `.env` file. Key settings include:

- `APP_NAME`, `VERSION`, `DEBUG`
- `DATABASE_URL`, `SECRET_KEY`, `ALGORITHM`
- Token expiry: `ACCESS_TOKEN_EXPIRE_MINUTES` (1 day), `REFRESH_TOKEN_EXPIRE_DAYS` (30 days)
- AI provider keys and endpoints
- File processing limits

### Database & Models

The default database is SQLite with WAL mode and foreign keys enabled. SQLAlchemy 2.x declarative models define the following entities:

#### Users & Access

- **User**: `id`, `username`, `email`, `full_name`, `hashed_password`, `role` (`admin` | `developer` | `viewer`), `is_active`, `is_superuser`, timestamps.

#### Projects & Environments

- **Project**: top-level grouping with owner, tags, status.
- **Environment**: belongs to a project; types include `development`, `qa`, `uat`, `staging`, `production`, `custom`.
- **LogSource**: points to a file system path, belongs to a project/environment, has watch settings, encoding, retention, parser template, and file pattern.

#### Logs

- **LogFile**: metadata about a scanned file (path, size, hash, parse status).
- **LogEntry**: individual log line with timestamp, severity, message, raw line, exception info, structured fields, bookmarks, notes, and AI summary.
- **LogTag**: tags attached to log entries.

#### Parsers, Searches, Alerts, AI

- **ParserTemplate**: reusable parsing templates (regex, JSON, CSV, delimiter, custom).
- **SavedSearch** / **SavedFilter**: saved query configurations.
- **AnalysisReport**: AI-generated reports with findings and charts.
- **ActivityLog**: audit trail of user actions.
- **AlertRule**: rule definitions with condition, severity, scope, cooldown, and delivery channels.
- **Notification**: generated alert notifications.
- **AIProvider**: configured AI backends.
- **AppSetting**: generic key/value application settings.

### Routers & API Surface

All routers are mounted under `/api/v1`:

| Router | Prefix | Key Capabilities |
|--------|--------|------------------|
| Auth | `/auth` | Register, login, refresh, me, user management (admin) |
| Projects | `/projects` | CRUD projects, environments, log sources |
| Logs | `/logs` | Scan, parse, search, bookmark, notes, stats, severity distribution, top exceptions |
| Dashboard | `/dashboard` | Stats, log volume, severity chart *(router currently missing)* |
| AI | `/ai` | Provider management, generate, chat, summarize, analyze exception |
| Parsers | `/parsers` | Parser template CRUD and test endpoint |
| Alerts | `/alerts` | Alert rules and notifications |
| Settings | `/settings` | Application settings CRUD |

### Services

#### AIService (`app/services/ai_service.py`)

A unified adapter for multiple LLM providers. It selects the active/default provider from the database and dispatches to the appropriate client:

- `openai`: `AsyncOpenAI`
- `azure`: `AsyncAzureOpenAI`
- `anthropic`: `AsyncAnthropic`
- `ollama`: direct HTTP to `/api/generate`
- `lmstudio`: OpenAI-compatible `/v1/chat/completions`
- `openrouter`: `/api/v1/chat/completions`

Built-in prompts handle log summarization and exception analysis.

#### ParserEngine (`app/services/parser_service.py`)

Parses individual log lines using templates. Supports:

- **regex**: named capture groups with field mapping
- **json**: JSON log field extraction
- **csv**: header-based parsing
- **delimiter**: custom delimiter splitting
- **custom**: fallback

Includes built-in templates for generic logs, JSON logs, syslog, nginx access logs, Django logs, and Spring Boot logs.

#### FileWatcherService (`app/services/watcher_service.py`)

Uses `watchdog` to monitor log source directories. Debounces rapid file changes (2 seconds) and notifies registered callbacks on create/modify/move events.

### Authentication & Authorization

- **Authentication**: OAuth2 Password Bearer flow with JWT access tokens and refresh tokens.
- **Password hashing**: bcrypt via `passlib`.
- **Current user**: `get_current_active_user` dependency validates the JWT and loads the user.
- **Authorization**: role-based dependency helpers:
  - `require_admin`: only `admin` or superuser
  - `require_developer`: `admin` or `developer`
  - `require_any`: any active role
- **Viewer restriction**: project listing filters to owned projects for viewers.

### File Watching

1. A log source is created with a file-system path and `auto_refresh` enabled.
2. `FileWatcherService.start_watching()` schedules a `watchdog.Observer` on the path.
3. On file creation/modification/move, the handler debounces and notifies callbacks.
4. On application shutdown, all observers are stopped.

> Note: The callback that re-scans/re-parses changed files is registered in the service but the full end-to-end automation (schedule parse after watch event) is not fully implemented.

### AI Integration

1. Users create/configure AI providers in Settings.
2. On startup, default providers for Ollama, OpenAI, and Anthropic are seeded.
3. AI endpoints accept a `provider_id` or fall back to the default enabled provider.
4. `AIService.generate()` dispatches to the provider-specific client and returns a normalized `AIResponse`.

## Frontend Architecture

### Entry Points

- `frontend/src/main.tsx`: creates the React root, renders `<App />`, imports Tailwind base styles.
- `frontend/src/App.tsx`: initializes auth state, sets up `BrowserRouter`, defines routes, and wraps protected routes.

### State Management

A hybrid state approach is used:

#### Client State — Zustand (persisted to localStorage)

- **authStore**: `user`, `token`, `refreshToken`, `isAuthenticated`, login/logout actions.
- **appStore**: theme, sidebar state, current project/environment.
- **searchStore**: search query, regex/case flags, severity filters, date range.

#### Server State — TanStack Query

Each page uses `useQuery`/`useMutation` for API calls with automatic caching, refetching, and loading states. Example: Dashboard polls `/dashboard/stats` every 30 seconds.

### Routing

`react-router-dom` v6 with the following routes:

| Path | Page | Access |
|------|------|--------|
| `/login` | LoginPage | Public |
| `/` | DashboardPage | Authenticated |
| `/projects` | ProjectsPage | Authenticated |
| `/logs` | LogViewerPage | Authenticated |
| `/analysis` | AnalysisPage | Authenticated |
| `/parsers` | ParsersPage | Authenticated |
| `/alerts` | AlertsPage | Authenticated |
| `/users` | UsersPage | Admin only |
| `/settings` | SettingsPage | Authenticated |

A custom `ProtectedRoute` component guards authenticated routes and enforces `adminOnly`.

### API Client

`frontend/src/services/api.ts` configures an Axios instance with:

- Base URL `/api/v1`
- Request interceptor injecting `Authorization: Bearer <token>` from localStorage
- Response interceptor redirecting to `/login` on 401

APIs are grouped into namespaces (`authApi`, `projectApi`, `logApi`, `dashboardApi`, `aiApi`, `parserApi`, `alertApi`, `settingsApi`).

During development, Vite proxies `/api` to `http://localhost:8000`.

### UI System

- **Styling**: Tailwind CSS with a custom shadcn/ui-inspired design system.
- **Dark mode**: CSS variables switch via a `.dark` class; state stored in `appStore`.
- **Components**: Custom primitives in `components/ui/` (button, card, dialog, tabs, badge, toast, etc.) built with `class-variance-authority` and `tailwind-merge`.
- **Icons**: `lucide-react`.
- **Charts**: `recharts` on the Dashboard page.

## Desktop (Tauri) Integration

The Tauri application wraps the same React frontend.

### Development Mode

- `beforeDevCommand` runs `npm run dev` in `frontend/`.
- Tauri webview loads `http://localhost:3000`.
- The frontend calls the backend via the Vite proxy to `localhost:8000`.

### Production Mode

- `beforeBuildCommand` runs `npm run build` → outputs to `frontend/dist`.
- `frontendDist` points to `../frontend/dist`.
- Tauri serves the built SPA via the custom protocol.

### Backend Launcher

`tauri/src/main.rs` spawns the Python backend on startup:

```rust
tokio::process::Command::new(python_path)
    .arg("-m").arg("uvicorn")
    .arg("app.main:app")
    .arg("--host").arg("127.0.0.1")
    .arg("--port").arg("8000")
    .current_dir(&backend_path)
    .spawn();
```

It expects a `backend/` directory next to the executable containing a Python interpreter.

## Data Flow Examples

### Ingesting a Log File

1. User creates a **Project** → **Environment** → **LogSource** with a directory path.
2. User clicks "Scan" → `POST /api/v1/logs/files/scan/{log_source_id}`.
3. Backend walks the directory, creates/updates `LogFile` records.
4. User clicks "Parse" → `POST /api/v1/logs/files/{log_file_id}/parse`.
5. Backend reads the file line-by-line, detects severity and timestamp, creates `LogEntry` records.

### Searching Logs

1. User selects project/environment/source/file and enters query/filters.
2. Frontend calls `GET /api/v1/logs/entries` with query parameters.
3. Backend builds a dynamic SQLAlchemy query with joins and filters.
4. Results are returned ordered by timestamp descending.

### AI Exception Analysis

1. User selects an exception in the Log Viewer.
2. Frontend calls `POST /api/v1/ai/analyze-exception`.
3. Backend `AIService` selects the active provider and dispatches a structured prompt.
4. AI response is returned and displayed in the UI.

## Deployment Topologies

### Local Development

- Backend on port `8000`
- Frontend dev server on port `3000` with Vite proxy

### Docker Single-Container

- One image based on `python:3.13-slim`
- Node.js installed to build frontend
- Backend serves API on port `8000`
- Volumes: `./data` for SQLite, `./logs` for log files

### Tauri Desktop

- Rust binary bundles the frontend
- Binary spawns Python backend from adjacent `backend/` directory
- Currently uses port `8000` for the embedded backend

## Known Architectural Gaps

1. **Tauri production API origin**: In a production Tauri build the frontend is served via the `tauri://` custom protocol, so relative `/api` calls will not reach the embedded Python backend on `http://localhost:8000`. The built frontend should be served as static files from FastAPI (same origin) or the API base URL should be configured explicitly for Tauri builds.
2. **Docker static files**: The built frontend is not served by FastAPI inside the Docker container.
3. **Alert scheduling**: Alert rules are stored but not evaluated on a schedule; delivery channels are defined but not invoked.
4. **AI key security**: Provider API keys are stored in the database as plain text.
