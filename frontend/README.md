# MMM Platform Frontend

React-based frontend for the Marketing Mix Modeling Platform.

## Tech Stack

- **Framework**: React 19 + TypeScript
- **Build Tool**: Vite 7
- **Styling**: TailwindCSS + shadcn/ui
- **State Management**: Zustand (client) + TanStack Query (server)
- **Routing**: React Router v7
- **Charts**: Apache ECharts (echarts-for-react)
- **Forms**: React Hook Form + Zod
- **i18n**: react-i18next (English / 简体中文)

## Getting Started

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

## Project Structure

```
src/
├── api/              # API client and services
│   ├── client.ts     # Axios instance
│   └── services/     # Domain services (auth, projects, etc.)
├── components/
│   ├── common/       # Shared components (ErrorBoundary, Skeleton)
│   ├── features/     # Feature components (auth, datasets)
│   ├── layout/       # Layout components (Sidebar, Header)
│   └── ui/           # shadcn/ui primitives
├── hooks/            # Custom React hooks
├── i18n/             # Internationalization
│   └── locales/      # Translation files (en.json, zh-CN.json)
├── lib/              # Utility functions
├── pages/            # Page components
├── stores/           # Zustand stores
└── types/            # TypeScript definitions
```

## Key Features

### Pages
- **Dashboard**: Overview with stats and recent projects
- **Projects**: List, create, and manage projects
- **Datasets**: Upload and preview data files
- **Model Config**: 5-step wizard for model setup
- **Training**: Real-time training progress
- **Results**: Interactive charts and metrics

### i18n Support
Language switching is available in the user menu. Supported languages:
- English (en)
- Simplified Chinese (zh-CN)

To add translations, edit files in `src/i18n/locales/`.

### Theme
Supports light/dark mode with system preference detection. Toggle in user menu.

## Environment Variables

```env
VITE_API_URL=/api/v1    # API base URL (proxied in dev)
```

## Docker

```bash
# Build image
docker build -t mmm-frontend .

# Run container
docker run -p 80:80 mmm-frontend
```

## Development Notes

- API requests are proxied to `http://localhost:8000` in development
- Production builds serve static files via nginx with SPA routing
- Use `@/` path alias for imports from `src/`
