# API Specification

## Base URL

```
Development: http://localhost:8000/api/v1
Production:  https://api.mmm.example.com/v1
```

## Authentication

All protected endpoints require Bearer token:
```
Authorization: Bearer <jwt_token>
```

---

## Endpoints Overview

| Category | Endpoint | Methods |
|----------|----------|---------|
| Auth | `/auth/*` | POST |
| Users | `/users/*` | GET, PUT |
| Projects | `/projects/*` | GET, POST, PUT, DELETE |
| Datasets | `/datasets/*` | GET, POST, DELETE |
| Models | `/models/*` | GET, POST, DELETE |
| Visualizations | `/visualizations/*` | GET, POST |
| Exports | `/exports/*` | GET, POST |
| Scenarios | `/scenarios/*` | GET, POST, PUT, DELETE |

---

## 1. Authentication

### POST `/auth/register`
Register a new user.

### POST `/auth/login`
Authenticate and receive JWT tokens.

### POST `/auth/refresh`
Refresh access token.

### POST `/auth/logout`
Invalidate tokens.

---

## 2. Projects

### GET `/projects`
List user's projects.

### POST `/projects`
Create a new project.

### GET `/projects/{project_id}`
Get project details.

### PUT `/projects/{project_id}`
Update project.

### DELETE `/projects/{project_id}`
Delete project and all associated data.

---

## 3. Datasets

### POST `/projects/{project_id}/datasets`
Upload a new dataset (CSV/Excel).

### GET `/projects/{project_id}/datasets`
List datasets in project.

### GET `/datasets/{dataset_id}`
Get dataset details with column statistics.

### GET `/datasets/{dataset_id}/preview`
Get data preview with pagination.

### DELETE `/datasets/{dataset_id}`
Delete dataset.

---

## 4. Model Training

### POST `/projects/{project_id}/models`
Create and train a new model.

**Key Request Fields:**
- `model_type`: "ols" | "ridge" | "elasticnet" | "bayesian"
- `target_variable`: Target column name
- `features`: Feature configuration with transformations
- `granularity`: National/regional/channel settings
- `constraints`: Coefficient and contribution constraints
- `priors`: Prior distributions (Bayesian only)

### GET `/models/{model_id}/status`
Check training status and progress.

### GET `/projects/{project_id}/models`
List models in project.

### GET `/models/{model_id}`
Get model details, metrics, and results.

### DELETE `/models/{model_id}`
Delete model.

---

## 5. Model Results

### GET `/models/{model_id}/coefficients`
Get coefficient estimates with confidence intervals.

### GET `/models/{model_id}/contributions`
Get contribution analysis by variable.

### GET `/models/{model_id}/decomposition`
Get time series decomposition data.

### GET `/models/{model_id}/response-curves`
Get response curves for each variable.

### GET `/models/{model_id}/diagnostics`
Get model diagnostics (VIF, R-hat, ESS).

---

## 6. Visualizations (pyecharts)

### GET `/models/{model_id}/charts/decomposition`
Generate decomposition stacked area chart.

**Query Parameters:**
- `chart_type`: "stacked_area" | "stacked_bar"
- `theme`: "light" | "dark"

### GET `/models/{model_id}/charts/actual-vs-fitted`
Generate actual vs fitted line chart.

### GET `/models/{model_id}/charts/waterfall`
Generate contribution waterfall chart.

### GET `/models/{model_id}/charts/response-curves`
Generate response curve charts.

### GET `/models/{model_id}/charts/coefficients`
Generate interactive coefficients table.

**Response:** JSON with pyecharts options for rendering.

---

## 7. Exports

### POST `/models/{model_id}/exports/html`
Generate HTML report with interactive charts.

**Response:** `202 Accepted` with task_id

### GET `/exports/{task_id}/download`
Download generated export file.

### POST `/models/{model_id}/exports/pdf`
Generate PDF report.

### POST `/models/{model_id}/exports/excel`
Generate Excel file with decomposition data.

**Excel Sheets:**
- Summary (metrics)
- Coefficients
- Decomposition (time series)
- Contributions
- Response Curves

---

## 8. Scenarios

### POST `/models/{model_id}/scenarios`
Create a what-if scenario.

### GET `/models/{model_id}/scenarios`
List scenarios for a model.

### GET `/scenarios/{scenario_id}`
Get scenario details and results.

### PUT `/scenarios/{scenario_id}`
Update scenario parameters.

### DELETE `/scenarios/{scenario_id}`
Delete scenario.

---

## Common Response Codes

| Code | Description |
|------|-------------|
| 200 | Success |
| 201 | Created |
| 202 | Accepted (async task started) |
| 400 | Bad Request |
| 401 | Unauthorized |
| 403 | Forbidden |
| 404 | Not Found |
| 422 | Validation Error |
| 500 | Internal Server Error |
