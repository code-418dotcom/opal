# Deploy to Azure Now - No CLI Required

Since Azure CLI is not installed, here are your deployment options:

## ✅ Option 1: Deploy via GitHub Actions (Recommended)

This is the easiest way - just push to GitHub and let Actions handle everything.

### Step 1: Create GitHub Repository

```bash
# Initialize git if not already done
git init
git add .
git commit -m "Ready for Azure deployment"

# Create a new repo on GitHub, then:
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git
git branch -M main
git push -u origin main
```

### Step 2: Create Azure Static Web App via Portal

1. Go to [Azure Portal](https://portal.azure.com)
2. Click "Create a resource" → Search "Static Web Apps"
3. Click "Create"
4. Fill in:
   - **Subscription**: Choose your subscription
   - **Resource Group**: Create new "opal-rg"
   - **Name**: opal-frontend
   - **Region**: West Europe (or your preferred)
   - **Deployment**: Choose "GitHub"
   - **Sign in to GitHub** and authorize
   - **Organization**: Your GitHub username
   - **Repository**: Your repo name
   - **Branch**: main
   - **Build Presets**: Custom
   - **App location**: `/frontend`
   - **Output location**: `dist`
5. Click "Review + Create" → "Create"

### Step 3: Configure Environment Variables

After deployment, add environment variables in Azure Portal:

1. Go to your Static Web App in Azure Portal
2. Click "Configuration" in left menu
3. Add these application settings:
   ```
   VITE_SUPABASE_URL=https://YOUR_PROJECT.supabase.co
   VITE_SUPABASE_ANON_KEY=YOUR_SUPABASE_ANON_KEY_HERE
   VITE_API_URL=http://localhost:8080
   VITE_API_KEY=dev_testkey123
   ```

   **Get your Supabase credentials from:** https://app.supabase.com/project/_/settings/api
4. Click "Save"

### Step 4: Wait for Deployment

GitHub Actions will automatically build and deploy. Check the Actions tab in your GitHub repo to monitor progress.

Your app will be live at: `https://opal-frontend-XXXXX.azurestaticapps.net`

---

## Option 2: Deploy via Netlify (Alternative)

Even faster for testing:

### Step 1: Build the frontend

```bash
cd frontend
npm run build
```

### Step 2: Deploy to Netlify

1. Go to [Netlify](https://app.netlify.com)
2. Sign up/login with GitHub
3. Click "Add new site" → "Deploy manually"
4. Drag and drop the `frontend/dist` folder
5. Your site will be live in seconds!

### Step 3: Configure Environment Variables

1. Go to Site settings → Environment variables
2. Add the same variables as above
3. Trigger a redeploy

---

## Option 3: Install Azure CLI and Deploy

If you want to use the deployment script:

### Install Azure CLI

**Ubuntu/Debian:**
```bash
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash
```

**macOS:**
```bash
brew install azure-cli
```

**Windows:**
Download from: https://aka.ms/installazurecliwindows

### Then Deploy

```bash
az login
./deploy-frontend-azure.sh
```

---

## Testing Locally First

Before deploying, test everything locally:

```bash
# Start frontend
cd frontend
npm run dev

# In another terminal, if you want to run the backend:
cd src/web_api
pip install -r requirements.txt
uvicorn web_api.main:app --reload --port 8080
```

Visit http://localhost:5173 and test:
1. Upload an image
2. Check job creation
3. Verify Supabase integration

---

## Quick Netlify Deploy (1 minute)

The absolute fastest way to get this live:

```bash
# Install Netlify CLI
npm install -g netlify-cli

# Deploy
cd frontend
npm run build
netlify deploy --prod --dir=dist
```

Follow the prompts, and you'll get a live URL immediately!

---

## What Gets Deployed

- ✅ Frontend React app
- ✅ Vite optimized production build
- ✅ Supabase integration (database, storage, edge functions)
- ✅ API integration ready

## Next Steps After Deployment

1. **Test the deployed site** - Upload images, create jobs
2. **Check Supabase Dashboard** - Monitor database and storage
3. **Configure custom domain** (optional)
4. **Set up monitoring** in Azure/Netlify
5. **Enable HTTPS** (automatic on both platforms)

Choose the option that works best for you and let me know if you need help with any step!
