# OPAL Frontend

Modern web interface for the OPAL AI Image Processing Platform.

## Features

- **Upload Interface**: Drag & drop image uploads with progress tracking
- **Job Monitor**: Real-time job status monitoring with auto-refresh
- **Debug Console**: Interactive command console for API testing
- **Results Gallery**: View and download processed images

## Quick Start

1. **Install Dependencies**:
   ```bash
   npm install
   ```

2. **Configure Environment**:
   Create `.env` file:
   ```env
   VITE_API_URL=http://localhost:8080
   VITE_API_KEY=dev_testkey123
   ```

3. **Start Development Server**:
   ```bash
   npm run dev
   ```

   The app will be available at `http://localhost:5173`

## Tech Stack

- React 18 + TypeScript
- Vite (Build tool)
- TanStack Query (Data fetching)
- Lucide React (Icons)

## Available Commands

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run preview` - Preview production build

## Configuration

Set these in `.env`:
- `VITE_API_URL` - Backend API endpoint
- `VITE_API_KEY` - Authentication key (format: `{tenant}_key`)
