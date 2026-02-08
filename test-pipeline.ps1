# Fixed Test Script - v3
$ErrorActionPreference = "Continue"

$WEB_URL = az containerapp show -g opal-dev-rg -n opal-web-api-dev --query "properties.configuration.ingress.fqdn" -o tsv

Write-Host "Testing OPAL Pipeline..." -ForegroundColor Cyan
Write-Host "API URL: https://$WEB_URL" -ForegroundColor Gray
Write-Host ""

# Step 1: Create Job
Write-Host "[1/5] Creating job..." -ForegroundColor Yellow
$response = curl "https://$WEB_URL/v1/jobs" -Method POST -ContentType "application/json" -Body '{"tenant_id":"test","brand_profile_id":"default","items":[{"filename":"test.png"}]}' -UseBasicParsing

$job = $response.Content | ConvertFrom-Json
$JOB_ID = $job.job_id
$ITEM_ID = $job.items[0].item_id

Write-Host "OK Job: $JOB_ID, Item: $ITEM_ID" -ForegroundColor Green

# Step 2: Get SAS URL
Write-Host ""
Write-Host "[2/5] Getting upload URL..." -ForegroundColor Yellow
$sasBody = "{`"tenant_id`":`"test`",`"job_id`":`"$JOB_ID`",`"item_id`":`"$ITEM_ID`",`"filename`":`"test.png`",`"content_type`":`"image/png`"}"
$response = curl "https://$WEB_URL/v1/uploads/sas" -Method POST -ContentType "application/json" -Body $sasBody -UseBasicParsing

$sas = $response.Content | ConvertFrom-Json
$UPLOAD_URL = $sas.upload_url

Write-Host "OK SAS URL obtained" -ForegroundColor Green

# Step 3: Upload Image
Write-Host ""
Write-Host "[3/5] Uploading test image..." -ForegroundColor Yellow

$bytes = [Convert]::FromBase64String("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==")
[IO.File]::WriteAllBytes("$PWD\test.png", $bytes)

curl $UPLOAD_URL -Method PUT -InFile test.png -Headers @{"x-ms-blob-type"="BlockBlob"} -UseBasicParsing | Out-Null

Write-Host "OK Image uploaded" -ForegroundColor Green

# Step 4: Complete Upload
Write-Host ""
Write-Host "[4/5] Triggering pipeline..." -ForegroundColor Yellow
$completeBody = "{`"tenant_id`":`"test`",`"job_id`":`"$JOB_ID`",`"item_id`":`"$ITEM_ID`",`"filename`":`"test.png`"}"

try {
    $completeResp = curl "https://$WEB_URL/v1/uploads/complete" -Method POST -ContentType "application/json" -Body $completeBody -UseBasicParsing
    Write-Host "OK Pipeline triggered" -ForegroundColor Green
} catch {
    Write-Host "WARN Upload complete returned error (checking logs needed)" -ForegroundColor Yellow
    Write-Host $_.Exception.Message -ForegroundColor DarkGray
}

Write-Host ""
Write-Host "Waiting 20 seconds..." -ForegroundColor Cyan
Start-Sleep -Seconds 20

# Step 5: Check Status (with tenant_id query parameter)
Write-Host ""
Write-Host "[5/5] Checking status..." -ForegroundColor Yellow

try {
    $response = curl "https://$WEB_URL/v1/jobs/$JOB_ID`?tenant_id=test" -UseBasicParsing
    $status = $response.Content | ConvertFrom-Json
    
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "  Job ID:     $JOB_ID" -ForegroundColor Gray
    Write-Host "  Item ID:    $ITEM_ID" -ForegroundColor Gray
    Write-Host "  Status:     $($status.items[0].status)" -ForegroundColor $(if ($status.items[0].status -eq "completed") {"Green"} elseif ($status.items[0].status -eq "processing") {"Yellow"} else {"Red"})
    
    if ($status.items[0].output_blob_path) {
        Write-Host "  Output:     $($status.items[0].output_blob_path)" -ForegroundColor Gray
    }
    
    if ($status.items[0].error_message) {
        Write-Host "  Error:      $($status.items[0].error_message)" -ForegroundColor Red
    }
    
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Full job details:" -ForegroundColor DarkGray
    $status | ConvertTo-Json -Depth 3
    
} catch {
    Write-Host "FAIL Could not get job status" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
}

Remove-Item test.png -ErrorAction SilentlyContinue