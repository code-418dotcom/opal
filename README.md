# OPAL Platform

AI-powered image processing platform for e-commerce product photography.

## Features

- **Background Removal** - Extract products from backgrounds using Azure ML
- **Lifestyle Scene Generation** - AI-generated product scenes
- **Image Upscaling** - 2x enhancement with Real-ESRGAN
- **Drag & Drop Upload** - Modern web interface with real-time progress
- **Job Monitoring** - Track processing status in real time
- **Multi-tenant** - Secure tenant isolation with API key auth

## Architecture

```
Frontend (React / Azure Static Web Apps)
    |
    | HTTPS
    v
Web API (FastAPI / Container App)
    |
    | Azure Service Bus queues
    v
+-------------------+-------------------+-------------------+
| bg-removal-worker | scene-worker      | upscale-worker    |
| (Azure ML)        | (Azure ML)        | (Real-ESRGAN)     |
+-------------------+-------------------+-------------------+
    |                   |                   |
    +-------------------+-------------------+
                        |
                   Azure Blob Storage
                   (raw / outputs / exports)
```

### Services (Azure Container Apps)

| Service              | Description                          |
|----------------------|--------------------------------------|
| `web-api`            | REST API (FastAPI) - job CRUD, uploads, downloads |
| `orchestrator`       | Reads `jobs` queue, dispatches to worker queues |
| `bg-removal-worker`  | Background removal via Azure ML endpoint |
| `scene-worker`       | Lifestyle scene generation via Azure ML |
| `upscale-worker`     | Image upscaling (Real-ESRGAN)        |
| `export-worker`      | Batch export / ZIP packaging         |
| `billing-service`    | Usage tracking and billing           |

### Infrastructure

- **Compute**: Azure Container Apps (7 microservices)
- **Queue**: Azure Service Bus (queues: `jobs`, `exports`, `bg-removal`, `scene-gen`, `upscale`)
- **Storage**: Azure Blob Storage (containers: `raw`, `outputs`, `exports`)
- **Database**: Azure PostgreSQL Flexible Server
- **Frontend**: Azure Static Web Apps
- **Container Registry**: Azure Container Registry
- **Auth**: Managed Identity (service-to-service), API keys (client-to-API)

## Tech Stack

### Backend
- Python 3.11+ / FastAPI
- SQLAlchemy ORM
- Azure Service Bus SDK
- Azure Blob Storage SDK
- Docker (per-service Dockerfiles)

### Frontend
- React 18 + TypeScript
- Vite
- TanStack Query

### AI/ML
- Azure ML endpoints (background removal, scene generation)
- Real-ESRGAN (upscaling)

## Quick Start (Local Development)

### Prerequisites

- Python 3.11+
- Node.js 18+
- Docker (optional, for containerized local run)
- A Supabase project (free tier works for local dev) **or** Azure credentials

### 1. Clone & Configure

```bash
git clone https://github.com/code-418dotcom/opal.git
cd opal
cp .env.example .env
# Edit .env with your credentials
```

### 2. Start Backend

```bash
# With Docker Compose (easiest)
docker-compose up -d

# Or run directly
pip install -r src/web_api/requirements.txt
cd src/web_api && python -m uvicorn web_api.main:app --reload --port 8080
```

### 3. Start Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173, upload images, and monitor processing.

## Production Deployment

Production runs on Azure. The CI/CD pipeline (`.github/workflows/build-deploy-dev.yml`) handles:

1. **Infrastructure**: Bicep templates provision all Azure resources
2. **Build**: Docker images built and pushed to ACR on `src/**` changes
3. **Deploy**: Container Apps updated with new image tags
4. **Frontend**: Static Web Apps deploy on push to `main`

OIDC is used for Azure auth in CI/CD (no stored credentials).

## Configuration

See [`.env.example`](.env.example) for all configuration options. Key settings:

- `STORAGE_BACKEND`: `azure` (production) or `supabase` (local dev)
- `QUEUE_BACKEND`: `azure` (production) or `database` (local dev)
- `AML_ENDPOINT_URL` / `AML_ENDPOINT_KEY`: Azure ML endpoint for AI processing

## Security

- API key authentication (`X-API-Key` header)
- Tenant isolation (multi-tenant data separation)
- Managed Identity for inter-service auth (no secrets in containers)
- Signed URLs for blob uploads/downloads
- Row-level security on database

## Monitoring

```bash
# Health check
curl https://<web-api-fqdn>/healthz

# Container Apps logs (Azure CLI)
az containerapp logs show -n opal-web-api-dev -g opal-dev-rg
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

UNLICENSED - Private use only
