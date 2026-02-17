# Frontend Deployment Fix

## The Issue

Azure Static Web Apps is configured to deploy from GitHub, so manual CLI deployments are being ignored/overridden.

## ✅ Solution: Use GitHub Actions

Your frontend will deploy automatically on every push to `main` branch.

### Method 1: Manually Trigger GitHub Actions (Recommended)

1. **Go to:** https://github.com/code-418dotcom/opal/actions/workflows/azure-static-web-apps-ambitious-smoke-04d5b1703.yml

2. **Click:** "Run workflow" button (top right)

3. **Select:** Branch = `main`

4. **Click:** Green "Run workflow" button

5. **Wait:** ~3-5 minutes for deployment

6. **Access:** https://ambitious-smoke-04d5b1703.1.azurestaticapps.net

### Method 2: Make a Small Change and Push

```bash
# Make any small change
echo "# Trigger deployment" >> README.md

# Commit and push
git add README.md
git commit -m "Trigger frontend deployment"
git push origin main
```

This will automatically trigger the GitHub Actions workflow.

### Method 3: Disable GitHub Integration (Not Recommended)

If you want to use manual deployments instead:

```bash
# Detach from GitHub
az staticwebapp disconnect -n opal-frontend-dev -g opal-dev-rg

# Then use the deployment script
powershell.exe -ExecutionPolicy Bypass -File deploy-frontend.ps1
```

## Why This Happened

- Azure Static Web Apps prioritizes GitHub deployments when connected to a repository
- Manual deployments via SWA CLI may be placed in a "preview" environment instead of production
- The GitHub Actions workflow has the environment variables configured correctly

## Recommended Setup

**Keep GitHub Actions enabled** - it provides:
- ✅ Automatic deployments on every push
- ✅ Environment variables configured in workflow
- ✅ Build caching for faster deployments
- ✅ Deployment history and rollback capabilities

## Quick Test

After GitHub Actions deployment completes:

```bash
# Check assets are accessible
curl -I https://ambitious-smoke-04d5b1703.1.azurestaticapps.net/assets/index-GqPfC8Pg.js

# Should return: HTTP/1.1 200 OK
```

## Current Workflow Status

Check here: https://github.com/code-418dotcom/opal/actions

Look for "Azure Static Web Apps CI/CD" workflow runs.

