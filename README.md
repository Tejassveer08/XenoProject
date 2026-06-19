# Xeno Transaction Data Validation Platform

A scalable web platform for validating transaction CSV datasets (orders, products, payments) with country-specific phone validation, date/time checks, referential integrity, and chunked processing for large files.

## Architecture

- **Frontend** (Next.js 14): Upload UI, job monitoring, result downloads
- **Backend** (FastAPI): REST API, JWT auth, presigned uploads, job orchestration
- **Worker** (Celery + Polars): Streaming CSV validation, output chunking
- **PostgreSQL**: Metadata, jobs, file tracking
- **Redis**: Celery message broker
- **MinIO**: S3-compatible object storage for uploads and outputs

## Quick Start (Docker)

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running

### Deploy

```bash
docker compose up --build -d
```

Wait ~2 minutes for all services to start, then open:

| Service | URL |
|---------|-----|
| **Web UI** | http://localhost:3000 |
| **API Docs** | http://localhost:8000/docs |
| **MinIO Console** | http://localhost:9001 (minioadmin / minioadmin123) |

### Demo Credentials

- Email: `demo@example.com`
- Password: `demo1234`

### Try a Sample Validation

1. Sign in at http://localhost:3000
2. Go to **Upload**
3. Upload `shared/samples/orders_sample.csv`
4. Select dataset type **Orders** and rule set **Default**
5. View results on the job detail page — download cleaned CSV and error report

## API Usage

Authenticate via login or API key header (`X-API-Key`).

```bash
# Login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"demo@example.com","password":"demo1234"}'

# Create upload session
curl -X POST http://localhost:8000/api/v1/upload-sessions \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"filename":"orders.csv","file_size":1024}'

# List rule sets
curl http://localhost:8000/api/v1/rule-sets
```

## Validation Features

- **Phone validation**: Country-specific rules (US, IN, SG, GB, AU) via `phonenumbers`
- **Date validation**: Multiple formats, future-date checks, cross-field date ordering
- **Data integrity**: Required fields, types, ranges, enums, uniqueness
- **Large files**: Chunked resumable uploads + Polars streaming + output splitting

## Project Structure

```
├── backend/          FastAPI application
├── worker/           Celery validation worker
├── frontend/         Next.js web UI
├── shared/
│   ├── rules/        Validation rule definitions (JSON)
│   └── samples/      Sample CSV datasets
└── docker-compose.yml
```

## Stopping

```bash
docker compose down
```

To remove all data volumes:

```bash
docker compose down -v
```

## Production Notes

- Change `JWT_SECRET` and database credentials in `docker-compose.yml`
- Use real AWS S3/GCS instead of MinIO
- Add TLS termination (nginx/ALB) in front of services
- Scale workers: `docker compose up --scale worker=4`
