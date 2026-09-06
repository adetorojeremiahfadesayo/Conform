# CONFORM — Google Cloud Run Deployment Script (PowerShell)
#
# Builds the multi-stage Docker container and deploys to Google Cloud Run.

$ErrorActionPreference = "Stop"

$ProjectId = $env:GOOGLE_CLOUD_PROJECT
if (-not $ProjectId) {
    $ProjectId = (gcloud config get-value project 2>$null).Trim()
}

if (-not $ProjectId) {
    Write-Error "Please set GOOGLE_CLOUD_PROJECT or configure gcloud project: gcloud config set project <PROJECT_ID>"
    exit 1
}

$Region = $env:GOOGLE_CLOUD_REGION
if (-not $Region) { $Region = "us-central1" }
$ServiceName = "conform"
$Image = "gcr.io/$ProjectId/${ServiceName}:latest"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " Deploying CONFORM to Google Cloud Run" -ForegroundColor Cyan
Write-Host " Project: $ProjectId"
Write-Host " Region:  $Region"
Write-Host " Service: $ServiceName"
Write-Host " Image:   $Image"
Write-Host "============================================================" -ForegroundColor Cyan

# 1. Build and push container image using Cloud Build
Write-Host "--> Building container image via Google Cloud Build..." -ForegroundColor Yellow
gcloud builds submit --tag $Image .

# Load .env if present
if (Test-Path ".env") {
    Get-Content ".env" | ForEach-Object {
        $line = $_.Trim()
        if ($line -and -not $line.StartsWith("#") -and $line.Contains("=")) {
            $parts = $line.Split("=", 2)
            $name = $parts[0].Trim()
            $val = $parts[1].Trim()
            if (-not [System.Environment]::GetEnvironmentVariable($name)) {
                [System.Environment]::SetEnvironmentVariable($name, $val)
            }
        }
    }
}

$EnvVarsList = @(
    "GOOGLE_CLOUD_PROJECT=$ProjectId",
    "GOOGLE_CLOUD_REGION=$Region",
    "BUILD_BUDGET_USD=10.00"
)
if ($env:CLICKHOUSE_HOST) { $EnvVarsList += "CLICKHOUSE_HOST=$($env:CLICKHOUSE_HOST)" }
if ($env:CLICKHOUSE_PORT) { $EnvVarsList += "CLICKHOUSE_PORT=$($env:CLICKHOUSE_PORT)" }
if ($env:CLICKHOUSE_USER) { $EnvVarsList += "CLICKHOUSE_USER=$($env:CLICKHOUSE_USER)" }
if ($env:CLICKHOUSE_PASSWORD) { $EnvVarsList += "CLICKHOUSE_PASSWORD=$($env:CLICKHOUSE_PASSWORD)" }
if ($env:CLICKHOUSE_DATABASE) { $EnvVarsList += "CLICKHOUSE_DATABASE=$($env:CLICKHOUSE_DATABASE)" }
$EnvVarsString = $EnvVarsList -join ","

# 2. Deploy to Cloud Run
Write-Host "--> Deploying service to Cloud Run..." -ForegroundColor Yellow
gcloud run deploy $ServiceName `
  --image $Image `
  --platform managed `
  --region $Region `
  --allow-unauthenticated `
  --port 8080 `
  --memory 2Gi `
  --cpu 2 `
  --timeout 300 `
  --set-env-vars "$EnvVarsString"

# 3. Get the live URL
$ServiceUrl = (gcloud run services describe $ServiceName --platform managed --region $Region --format 'value(status.url)').Trim()

Write-Host "============================================================" -ForegroundColor Green
Write-Host " Deployment Complete!" -ForegroundColor Green
Write-Host " Live Hosted Application URL: $ServiceUrl" -ForegroundColor Green
Write-Host " Use this URL for your Devpost submission form." -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
