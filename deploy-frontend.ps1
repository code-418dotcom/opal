# OPAL Frontend Deployment Script for Azure Static Web Apps
# Run this in PowerShell to deploy your frontend

Write-Host "=== OPAL Frontend Deployment ===" -ForegroundColor Cyan
Write-Host ""

# Step 1: Build the frontend
Write-Host "Step 1: Building frontend with Azure configuration..." -ForegroundColor Yellow
Set-Location frontend

# Check if .env.production exists
if (-Not (Test-Path ".env.production")) {
    Write-Host "Creating .env.production..." -ForegroundColor Yellow
    @"
VITE_BACKEND_TYPE=azure
VITE_API_URL=https://opal-web-api-dev.victoriousmoss-91bcd75e.westeurope.azurecontainerapps.io
VITE_API_KEY=dev_testkey123
"@ | Out-File -FilePath ".env.production" -Encoding utf8
}

# Build
npm run build
if ($LASTEXITCODE -ne 0) {
    Write-Host "Build failed!" -ForegroundColor Red
    exit 1
}

Write-Host "Build completed successfully!" -ForegroundColor Green
Write-Host ""

# Step 2: Get deployment token
Write-Host "Step 2: Getting deployment token..." -ForegroundColor Yellow
$deployToken = az staticwebapp secrets list --name opal-frontend-dev --resource-group opal-dev-rg --query "properties.apiKey" -o tsv

if ([string]::IsNullOrEmpty($deployToken)) {
    Write-Host "Failed to get deployment token!" -ForegroundColor Red
    exit 1
}

Write-Host "Token retrieved!" -ForegroundColor Green
Write-Host ""

# Step 3: Deploy
Write-Host "Step 3: Deploying to Azure Static Web Apps..." -ForegroundColor Yellow
Write-Host "This may take 2-3 minutes..." -ForegroundColor Gray

npx @azure/static-web-apps-cli deploy ./dist `
    --deployment-token $deployToken `
    --env production

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "====================================" -ForegroundColor Green
    Write-Host "Deployment Successful!" -ForegroundColor Green
    Write-Host "====================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Your frontend is now live at:" -ForegroundColor Cyan
    Write-Host "https://ambitious-smoke-04d5b1703.1.azurestaticapps.net" -ForegroundColor White
    Write-Host ""
    Write-Host "Wait 30-60 seconds, then refresh the page (Ctrl+Shift+R for hard refresh)" -ForegroundColor Yellow
} else {
    Write-Host ""
    Write-Host "Deployment failed!" -ForegroundColor Red
    Write-Host "Check the error messages above" -ForegroundColor Red
}

Set-Location ..
