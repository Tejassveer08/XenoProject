# Deploy Xeno Validation Platform
Write-Host "Starting Xeno Validation Platform..." -ForegroundColor Cyan

docker info 2>$null | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Docker is not running. Please start Docker Desktop and retry." -ForegroundColor Red
    exit 1
}

Set-Location $PSScriptRoot
docker compose up --build -d

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "Platform deployed successfully!" -ForegroundColor Green
    Write-Host "  Web UI:      http://localhost:3000"
    Write-Host "  API Docs:    http://localhost:8000/docs"
    Write-Host "  MinIO:       http://localhost:9001 (minioadmin / minioadmin123)"
    Write-Host ""
    Write-Host "  Demo login:  demo@example.com / demo1234"
}
