# Quickest Way to Deploy & Test (5 Minutes)

## 🚀 Fastest: Netlify Drag & Drop

Since Azure CLI is not installed, the quickest way to get your app live is Netlify's drag-and-drop:

### Step 1: Your Build is Ready ✅

The frontend is already built at `frontend/dist/`

### Step 2: Deploy (Literally 30 seconds)

1. **Go to**: https://app.netlify.com/drop
2. **Drag and drop** the `frontend/dist` folder onto the page
3. **Done!** You'll get a live URL instantly like: `https://random-name-123.netlify.app`

### Step 3: Configure Environment (2 minutes)

After deployment:

1. Click "Site settings" → "Environment variables"
2. Add these variables:

```
VITE_SUPABASE_URL=https://jbwbdfabuffiwdphzzon.supabase.co
VITE_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Impid2JkZmFidWZmaXdkcGh6em9uIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzEyMzI5ODgsImV4cCI6MjA4NjgwODk4OH0.UjUX0ft6k_E_H5twY8d3A1liMyKjgPpA1kAIDjU4__0
```

3. Click "Rebuild site"

### Step 4: Test

Visit your live URL and test:
- ✅ Upload an image
- ✅ Create a job
- ✅ Check job status
- ✅ Download results

---

## Alternative: GitHub → Azure (10 minutes)

If you prefer Azure and have GitHub:

### Quick Setup

```bash
# Create the deployment package
git init
git add .
git commit -m "Deploy OPAL to Azure"

# Create a repo on GitHub, then:
git remote add origin https://github.com/YOUR_USERNAME/opal-platform.git
git push -u origin main
```

### Deploy via Azure Portal

1. Go to https://portal.azure.com
2. Create "Static Web App"
3. Connect to your GitHub repo
4. Build settings:
   - App location: `/frontend`
   - Output location: `dist`
5. Azure will auto-deploy on every push

---

## What's Working Right Now

✅ **Frontend Build**: 247 KB optimized bundle
✅ **Supabase Backend**: Database, storage, edge functions ready
✅ **All Features**: Upload, job creation, processing, downloads
✅ **No Breaking Changes**: Everything builds successfully

---

## Current Architecture

```
Frontend (React + Vite)
    ↓
Supabase Edge Functions
    ↓
Supabase Database (PostgreSQL)
    ↓
Supabase Storage (Images)
```

Everything uses Supabase as the backend - no Azure backend services needed right now!

---

## Testing the Deployed App

Once live, test this workflow:

1. **Open the app** → You should see the upload interface
2. **Upload an image** → Click upload, select a file
3. **Create a job** → Click "Process Images"
4. **Monitor status** → Job status updates should appear
5. **View results** → Download processed images

All data flows through Supabase:
- Files → Supabase Storage
- Jobs → Supabase Database
- Processing → Supabase Edge Functions

---

## Files to Upload to Netlify

Just drag this folder to Netlify Drop:

```
frontend/dist/
```

That's it! The entire built application is in that folder.

---

## Need Help?

If you run into issues:

1. **Check Supabase Dashboard**: https://supabase.com/dashboard
   - Verify storage buckets exist
   - Check database tables
   - View edge function logs

2. **Browser Console**: Press F12 to see any errors

3. **Network Tab**: Check API calls to Supabase

---

## Ready to Deploy?

**Fastest path**: Open https://app.netlify.com/drop and drag `frontend/dist`

**GitHub + Azure**: Follow the GitHub setup above

Either way, you'll have a live, working app in under 10 minutes!
