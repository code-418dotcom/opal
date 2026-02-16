# OPAL Frontend - Quick Start Guide

## Overview

The OPAL frontend is a modern React-based web application that provides a comprehensive interface for uploading images, monitoring processing jobs, debugging API interactions, and viewing results.

## Features

### 🚀 Upload Interface
- Drag & drop image upload
- Multi-file selection
- Real-time upload progress
- Automatic job creation and enqueueing

### 📊 Job Monitor
- Real-time job status tracking
- Auto-refresh every 3 seconds
- Progress visualization
- Item-level status details
- Error message display

### 🐛 Debug Console
- Interactive command interface
- API health checks
- Job inspection
- Request/response logging
- Copy logs to clipboard

### 🖼️ Results Gallery
- View completed images
- Download processed results
- View input/output paths
- Grid layout for multiple images

## Getting Started

### 1. Navigate to Frontend Directory

```bash
cd frontend
```

### 2. Install Dependencies

```bash
npm install
```

### 3. Configure Environment

Create a `.env` file in the `frontend/` directory:

```env
VITE_API_URL=http://localhost:8080
VITE_API_KEY=dev_testkey123
```

**Important**: Update `VITE_API_KEY` to match your backend's configured API key.

### 4. Start Development Server

```bash
npm run dev
```

The application will be available at: **http://localhost:5173**

## Usage Guide

### Uploading Images

1. Navigate to the **Upload** tab
2. Drag and drop images or click to browse
3. Select one or more image files (JPG, PNG, WebP)
4. Review selected files in the list
5. Click **"Upload & Process"**
6. Monitor upload progress
7. Job ID will be displayed upon successful upload

### Monitoring Jobs

1. Navigate to the **Monitor** tab
2. Enter a Job ID (auto-populated from uploads)
3. View overall progress bar
4. Check individual item statuses:
   - 🕐 **Created** - Job item created
   - 📤 **Uploaded** - File uploaded to storage
   - ⚙️ **Processing** - AI processing in progress
   - ✅ **Completed** - Processing finished
   - ❌ **Failed** - Processing encountered error
5. Enable **"Auto-refresh"** for real-time updates

### Using Debug Console

Run commands by typing and pressing Enter:

**Available Commands:**
- `health` - Check API connectivity and health
- `job <job_id>` - Fetch and display job details
- `clear` - Clear console logs
- `help` - Show available commands

**Example:**
```
health
job_abc123xyz789
```

### Viewing Results

1. Navigate to the **Results** tab
2. Enter a Job ID
3. View completed images in gallery
4. Click **"View"** to open in new tab
5. Click **"Download"** to save locally

## Architecture

### Component Structure

```
App.tsx                     # Main app with tab navigation
├── UploadSection.tsx       # File upload interface
├── JobMonitor.tsx          # Job status monitoring
├── DebugConsole.tsx        # Interactive debug console
└── ResultsGallery.tsx      # Results viewer
```

### Data Flow

1. **Upload**: Files → SAS URL → Azure Storage → Mark Complete → Enqueue
2. **Monitor**: Poll API → Display Status → Auto-refresh
3. **Debug**: Command → API Request → Log Response
4. **Results**: Job ID → Fetch Items → Display Completed

### API Integration

The frontend uses an API client (`api.ts`) that:
- Adds `X-API-Key` header to all requests
- Handles authentication
- Manages errors
- Types responses

**Endpoints Used:**
- `POST /v1/jobs` - Create job
- `GET /v1/jobs/{id}` - Get job status
- `POST /v1/uploads/sas` - Get SAS upload URL
- `POST /v1/uploads/complete` - Mark upload complete
- `POST /v1/jobs/{id}/enqueue` - Start processing
- `GET /healthz` - Health check

## Design System

### Color Palette

- **Primary Blue**: `#2563eb` - Actions, links, active states
- **Success Green**: `#10b981` - Completed, success messages
- **Warning Orange**: `#f59e0b` - Partial, warnings
- **Error Red**: `#ef4444` - Failed, errors
- **Dark Slate**: `#0f172a` - Background
- **Slate**: `#1e293b` - Surface elements

### Typography

- **Font Family**: Inter, system-ui, sans-serif
- **Headings**: 700 weight, 1.25rem-1.875rem
- **Body**: 400 weight, 0.875rem-1rem
- **Code**: Fira Code, monospace

### Spacing

Uses 8px base unit spacing system:
- 0.5rem = 8px
- 1rem = 16px
- 1.5rem = 24px
- 2rem = 32px

## Configuration

### Backend Connection

Update `.env` to point to your backend:

```env
VITE_API_URL=https://your-backend-url.com
```

### Authentication

Set your API key (must match backend configuration):

```env
VITE_API_KEY=your_tenant_keystring
```

**API Key Format**: `{tenant_id}_{random_string}`

Example: `acme_abc123`, `dev_testkey123`

The tenant ID prefix is extracted and used for tenant isolation.

## Development

### Hot Reload

Vite provides instant hot module replacement. Save any file to see changes immediately.

### TypeScript

TypeScript is enabled by default. Types are defined in `types.ts`.

### Linting

```bash
npm run lint
```

### Building

```bash
npm run build
```

Outputs to `dist/` directory.

### Preview Production Build

```bash
npm run preview
```

## Troubleshooting

### "Failed to fetch" Errors

**Cause**: Cannot connect to backend API

**Solutions**:
1. Check `VITE_API_URL` in `.env`
2. Ensure backend is running
3. Verify CORS is enabled on backend
4. Check network tab in browser DevTools

### Authentication Errors (401/403)

**Cause**: Invalid or missing API key

**Solutions**:
1. Check `VITE_API_KEY` in `.env`
2. Verify key matches backend configuration
3. Ensure key format: `tenant_key`
4. Restart dev server after changing `.env`

### Upload Failures

**Possible Causes**:
- File too large
- Unsupported file type
- Network timeout
- Invalid SAS URL

**Debug Steps**:
1. Check browser console for errors
2. Use Debug Console to test `health` endpoint
3. Verify file type is image (JPG, PNG, WebP)
4. Check backend logs

### Images Not Displaying

**Note**: The frontend currently shows placeholders. Actual image previews require:
1. SAS URLs for blob access
2. Direct blob URL generation
3. Image loading component

## Best Practices

### API Keys

- Never commit `.env` files to Git
- Use different keys per environment
- Rotate keys regularly

### Error Handling

- Check Debug Console for API errors
- Review browser console for client errors
- Monitor backend logs for processing errors

### Performance

- Enable auto-refresh only when needed
- Clear large file selections before new uploads
- Use job IDs instead of polling all jobs

## Next Steps

1. **Start the backend** (see main README)
2. **Configure environment** variables
3. **Run frontend** development server
4. **Upload test images** to verify pipeline
5. **Monitor processing** in real-time
6. **View results** when completed

## Support

For issues or questions:
1. Check this guide
2. Review `CODE-REVIEW-FIXES.md` for backend security
3. Inspect browser DevTools console
4. Check backend API logs

## Version

Frontend v1.0.0 for OPAL Platform v0.2
