# ⚡ OPAL Platform

**AI-Powered Image Processing Platform** with background removal, lifestyle scene generation, and upscaling.

## 🚀 Features

- **Drag & Drop Upload** - Modern web interface
- **Background Removal** - Multiple providers (local/API)
- **Lifestyle Scene Generation** - AI-generated product scenes
- **Image Upscaling** - 2x enhancement with Real-ESRGAN
- **Real-time Monitoring** - Track job progress
- **Debug Console** - Interactive API testing
- **Multi-tenant** - Secure tenant isolation
- **Scalable** - Async processing with workers

## 📦 Tech Stack

### Frontend
- React 18 + TypeScript
- Vite (Lightning-fast builds)
- TanStack Query (Data fetching)
- Professional dark theme

### Backend
- FastAPI (Python 3.11+)
- Supabase (Database + Storage)
- SQLAlchemy (ORM)
- Docker (Containerization)

### AI/ML
- Rembg (Background removal)
- FAL.AI / Replicate (Image generation)
- Real-ESRGAN (Upscaling)

## 🎯 Quick Start

### Prerequisites

1. **Supabase Account** - [Create free account](https://supabase.com)
2. **Node.js 18+** - For frontend
3. **Python 3.11+** - For backend (or use Docker)
4. **Docker** (optional) - For containerized deployment

### 1. Clone Repository

```bash
git clone https://github.com/yourusername/opal-platform.git
cd opal-platform
```

### 2. Set Up Supabase

1. Create a new Supabase project
2. The database schema is already created! ✅
3. Get your credentials from Settings → API:
   - Project URL
   - Service Role Key
   - Anon Key

### 3. Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your Supabase credentials
nano .env
```

**Minimum required:**
```env
DATABASE_URL=postgresql://postgres:[password]@db.[project].supabase.co:5432/postgres
SUPABASE_URL=https://[project].supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
SUPABASE_ANON_KEY=your-anon-key
API_KEYS=dev_testkey123
```

### 4. Start Backend (Docker Compose)

```bash
# Start all backend services
docker-compose up -d

# View logs
docker-compose logs -f
```

Services:
- **Web API** - http://localhost:8080
- **Orchestrator** - Background worker
- **Export Worker** - Background worker

### 5. Start Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend: http://localhost:5173

### 6. Test It!

1. Open http://localhost:5173
2. Go to **Upload** tab
3. Drag & drop images
4. Click **Upload & Process**
5. Monitor progress in **Monitor** tab
6. View results in **Results** tab

## 📚 Documentation

- **[Frontend Guide](FRONTEND-GUIDE.md)** - Frontend usage and development
- **[Backend Deployment](BACKEND-DEPLOYMENT.md)** - Deploy to Railway, Render, Fly.io, etc.
- **[Deployment Fixes](DEPLOYMENT-FIXES.md)** - Troubleshooting deployment issues
- **[Code Review Fixes](CODE-REVIEW-FIXES.md)** - Security improvements and fixes
- **[Environment Config](.env.example)** - All configuration options

## 🏗️ Architecture

```
Frontend (React)
    ↓ HTTPS
Web API (FastAPI)
    ↓ Database Queue
Orchestrator Worker
    ↓ Supabase Storage
Results → Gallery
```

### Data Flow

1. **Upload** - Frontend → Web API → Supabase Storage
2. **Process** - Web API → Queue → Orchestrator
3. **AI Pipeline** - Orchestrator:
   - Remove background
   - Generate lifestyle scene
   - Composite product
   - Upscale image
4. **Store** - Results → Supabase Storage
5. **View** - Frontend → Results Gallery

## 🚢 Deployment

### Frontend (Static)

**Netlify (Recommended):**
```bash
# Already configured via netlify.toml
git push origin main
```

**Vercel:**
```bash
# Already configured via vercel.json
git push origin main
```

**Manual:**
```bash
cd frontend
npm run build
# Upload dist/ folder to any static host
```

### Backend (Docker)

**Railway (Recommended):**
```bash
railway login
railway init
railway up
```

**Render:**
- Connect GitHub repo
- Configure services from dashboard
- Automatic deployment

**Fly.io:**
```bash
fly launch
fly deploy
```

**Google Cloud Run:**
```bash
gcloud run deploy opal-web-api --source .
```

See **[BACKEND-DEPLOYMENT.md](BACKEND-DEPLOYMENT.md)** for detailed instructions.

## 🔧 Development

### Run Backend Locally (without Docker)

```bash
# Install dependencies
pip install -r src/web_api/requirements.txt

# Run web API
cd src/web_api
python -m uvicorn web_api.main:app --reload --port 8080

# Run orchestrator (separate terminal)
cd src/orchestrator
python -m orchestrator.worker

# Run export worker (separate terminal)
cd src/export_worker
python -m export_worker.worker
```

### Run Frontend

```bash
cd frontend
npm run dev
```

### Run Tests

```bash
# Backend tests (coming soon)
pytest

# Frontend tests (coming soon)
npm test
```

## 🎨 Configuration

### AI Providers

**Background Removal:**
- `rembg` - Local, free (default)
- `remove.bg` - Paid API, high quality
- `azure-vision` - Azure Computer Vision

**Image Generation:**
- `fal` - FAL.AI (recommended)
- `replicate` - Replicate API
- `huggingface` - Hugging Face

**Upscaling:**
- `realesrgan` - Local, free (default)
- `fal` - FAL.AI upscaling
- `replicate` - Replicate upscaling

### Storage Backends

- `supabase` - Supabase Storage (default)
- `azure` - Azure Blob Storage (legacy)

### Queue Backends

- `database` - PostgreSQL-based queue (default)
- `azure` - Azure Service Bus (legacy)

## 🔐 Security

✅ **API Key Authentication** - X-API-Key header required
✅ **Tenant Isolation** - Multi-tenant data separation
✅ **Input Validation** - Prevents path traversal and injection
✅ **RLS Enabled** - Row-level security on Supabase
✅ **Signed URLs** - Secure file uploads/downloads
✅ **Rate Limiting** - (Configure in production)

See **[CODE-REVIEW-FIXES.md](CODE-REVIEW-FIXES.md)** for security details.

## 📊 Monitoring

### Health Check

```bash
curl http://localhost:8080/healthz
```

### Database Queries

```sql
-- Check recent jobs
SELECT * FROM jobs ORDER BY created_at DESC LIMIT 10;

-- Check queue status
SELECT queue_name, status, COUNT(*)
FROM job_queue
GROUP BY queue_name, status;
```

### Logs

```bash
# Docker Compose
docker-compose logs -f web-api

# Railway
railway logs

# Cloud Run
gcloud logging read "resource.type=cloud_run_revision"
```

## 💰 Cost Estimates

### Development (Free)
- Supabase Free Tier
- Local development
- **Total: $0/month**

### Production (Low Traffic)
- Supabase Free Tier or $25/month
- Railway/Render: $10-20/month
- **Total: $10-45/month**

### Production (Medium Traffic)
- Supabase Pro: $25/month
- Railway/Cloud Run: $30-50/month
- **Total: $55-75/month**

## 🐛 Troubleshooting

### Frontend can't connect to backend

1. Check `VITE_API_URL` in frontend/.env
2. Verify backend is running
3. Check CORS settings
4. Verify API key is correct

### Backend database errors

1. Verify DATABASE_URL is correct
2. Check Supabase project is active
3. Ensure migrations ran successfully
4. Check RLS policies

### Workers not processing

1. Verify orchestrator is running
2. Check environment variables
3. Ensure job was enqueued
4. View worker logs for errors

### Upload fails

1. Check Supabase Storage buckets exist
2. Verify SUPABASE_SERVICE_ROLE_KEY
3. Check file size limits
4. Review browser console errors

See **[DEPLOYMENT-FIXES.md](DEPLOYMENT-FIXES.md)** for more troubleshooting.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 📄 License

UNLICENSED - Private use only

## 🙏 Acknowledgments

- FastAPI for the excellent web framework
- Supabase for the amazing backend platform
- Real-ESRGAN for image upscaling
- Rembg for background removal

---

## 📝 Version History

### v0.2.1 (Current)
- ✅ Supabase integration
- ✅ Frontend deployment fixes
- ✅ Security improvements
- ✅ Comprehensive documentation

### v0.2.0
- Initial Azure-based implementation
- Multi-service architecture
- AI pipeline implementation

---

**Built with ⚡ by the OPAL Team**

For questions or support, check the documentation or open an issue.

🌟 **Star this repo if you find it useful!**
