# Production CRM Mock API

This repository provides a FastAPI-based CRM mock service for data engineering testing.
It intentionally simulates messy production data instead of a clean demo schema.

## Project Overview

The API models a CRM that evolved over time and now contains realistic data quality problems:

- Versioned snapshots (`v1`, `v2`, `v3`) with temporal changes
- Inconsistent schemas across entities and versions
- Nulls, invalid values, casing drift, and mixed date formats
- Intentional limited orphans and stale sync artifacts

Use this project to test ingestion, validation, reconciliation, and schema evolution logic.

## Features

- FastAPI implementation for CRM entities and metadata
- Versioned datasets in `fastapi-crm-api/data/v1`, `v2`, `v3`
- Static reference data in `fastapi-crm-api/data/static`
- Cross-entity search endpoint
- Pagination helpers with realistic production quirks
- Event generation from inter-version differences

## Run Locally

1. Install dependencies:

```bash
cd fastapi-crm-api
python -m pip install -r requirements.txt
```

2. Start the API:

```bash
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

3. Open docs:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## API Endpoints

Core entities:

- `GET /customers`, `GET /customers/{id}`
- `GET /contacts`, `GET /contacts/{id}`
- `GET /leads`, `GET /leads/{id}`
- `GET /deals`, `GET /deals/{id}`
- `GET /activities`, `GET /activities/{id}`
- `GET /notes`
- `GET /companies`, `GET /companies/{id}`

Supporting endpoints:

- `GET /owners`
- `GET /pipeline-stages`
- `GET /sync-status`
- `GET /metadata`
- `GET /search?q=...`
- `GET /events`
- `GET /health`

Versioning is supported via `?version=v1|v2|v3`.

## Deployment (Render)

This repo includes a root Blueprint file at `render.yaml` configured to deploy the app from `fastapi-crm-api`.

- Runtime: Docker
- Health check path: `/health`
- Startup command (inside Docker):

```bash
uvicorn main:app --host 0.0.0.0 --port $PORT
```

The Dockerfile is located at `fastapi-crm-api/Dockerfile`.
