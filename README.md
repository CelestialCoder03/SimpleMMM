# SimpleMMM

[English](README.md) | [中文](README_CN.md)

A modern, open-source web application for Marketing Mix Modeling (MMM). Upload your marketing data, configure models, train with multiple regression techniques, and visualize results — all through an intuitive UI.

## Features

**Modeling**
- Multiple model types: OLS, Ridge, Bayesian (PyMC), ElasticNet
- Data transformations: Adstock (geometric, Weibull), Saturation (Hill, logistic)
- Flexible constraints: coefficient bounds, sign constraints, contribution limits
- Multi-granularity: national, regional, city, channel-level modeling
- Hierarchical models with constraint/prior inheritance
- Budget optimization and scenario analysis

**Frontend**
- React 19 + TypeScript + Vite
- Step-by-step model configuration wizard
- Interactive visualizations with ECharts (decomposition, contributions, response curves)
- English and Simplified Chinese (i18n)
- Dark/light mode with system preference detection

**Backend**
- Async model training with Celery + Redis
- Data exploration: summary statistics, correlations, distributions, time series preview
- Export: CSV, Excel, JSON, HTML reports
- RESTful API with OpenAPI documentation

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI, Python 3.11+, SQLAlchemy, Celery |
| Frontend | React 19, TypeScript, Vite, TailwindCSS, shadcn/ui, ECharts |
| State | Zustand (client), TanStack Query (server) |
| Database | PostgreSQL, Redis |
| Modeling | scikit-learn, PyMC, NumPy, Pandas |
| Deployment | Docker Compose, Nginx |

## Quick Start

### Docker Compose (Recommended)

```bash
git clone https://github.com/CelestialCoder03/SimpleMMM.git
cd SimpleMMM

# Start all services (API, frontend, PostgreSQL, Redis, Celery worker, Nginx)
cd docker
docker compose up -d

# Access the application
# App:      http://localhost
# API docs: http://localhost/api/docs
```

### Local Development

**Prerequisites:** Python 3.11+ with [uv](https://docs.astral.sh/uv/), Node.js 22+, PostgreSQL, Redis

**1. Start infrastructure:**

```bash
# Option A: Use Docker for database services only
cd docker && docker compose up -d db redis

# Option B: Install locally (macOS)
brew install postgresql@16 redis
brew services start postgresql@16 redis
createdb mmm
```

**2. Configure environment:**

```bash
cp .env.example .env
# Edit .env as needed — defaults work for local development
```

**3. Backend:**

```bash
cd backend
uv sync --dev
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --port 8000

# In a separate terminal — start Celery worker
uv run celery -A app.workers.celery_app worker -l info
```

**4. Frontend:**

```bash
cd frontend
npm install
npm run dev
```

**5. Open the app:**

- Frontend: http://localhost:3000
- API docs: http://localhost:8000/api/v1/docs

## Project Structure

```
SimpleMMM/
├── backend/           # FastAPI backend
│   ├── app/
│   │   ├── api/       # REST endpoints
│   │   ├── models/    # SQLAlchemy models
│   │   ├── schemas/   # Pydantic schemas
│   │   ├── services/  # Business logic & modeling engine
│   │   └── workers/   # Celery tasks
│   └── migrations/    # Alembic migrations
├── frontend/          # React frontend
│   └── src/
│       ├── api/       # API client
│       ├── components/# UI components
│       ├── pages/     # Page components
│       ├── stores/    # Zustand stores
│       └── i18n/      # Translations
├── docker/            # Docker Compose configuration
│   ├── docker-compose.yml
│   └── nginx/
└── docs/              # Documentation
```

## Documentation

- [Modeling Specification](docs/modeling-specification.md) — supported models, transformations, constraints
- [API Specification](docs/api-specification.md) — REST API endpoints and usage

## License

[MIT](LICENSE)
