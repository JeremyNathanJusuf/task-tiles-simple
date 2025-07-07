# Task Tiles Development Environment Setup Script for Windows
Write-Host "🚀 Setting up Task Tiles development environment..." -ForegroundColor Green

# Check if .env file exists
if (-not (Test-Path ".env")) {
    Write-Host "📝 Creating .env file..." -ForegroundColor Yellow
    @"
# Backend Configuration
DATABASE_URL=sqlite:///data/task_tiles.db
PYTHONUNBUFFERED=1
PYTHONDONTWRITEBYTECODE=1

# Frontend Configuration
REACT_APP_API_URL=http://localhost:8000
CHOKIDAR_USEPOLLING=true

# Development Settings
NODE_ENV=development
"@ | Out-File -FilePath ".env" -Encoding UTF8
    Write-Host "✅ .env file created" -ForegroundColor Green
} else {
    Write-Host "ℹ️  .env file already exists" -ForegroundColor Blue
}

# Check if Docker Compose is available
try {
    docker-compose --version | Out-Null
    Write-Host "✅ Docker Compose is available" -ForegroundColor Green
} catch {
    Write-Host "❌ Docker Compose is not installed. Please install Docker Desktop first." -ForegroundColor Red
    exit 1
}

# Build and start the development environment
Write-Host "🔨 Building Docker containers..." -ForegroundColor Yellow
docker-compose -f docker-compose.dev.yml build

Write-Host "🏃 Starting development environment..." -ForegroundColor Yellow
docker-compose -f docker-compose.dev.yml up -d

Write-Host "⏳ Waiting for services to be ready..." -ForegroundColor Yellow
Start-Sleep -Seconds 10

# Check if services are running
Write-Host "🔍 Checking service status..." -ForegroundColor Yellow
docker-compose -f docker-compose.dev.yml ps

Write-Host "🎉 Development environment is ready!" -ForegroundColor Green
Write-Host ""
Write-Host "📋 Access your application:" -ForegroundColor Cyan
Write-Host "  - Frontend: http://localhost:3000" -ForegroundColor White
Write-Host "  - Backend API: http://localhost:8000" -ForegroundColor White
Write-Host "  - API Documentation: http://localhost:8000/docs" -ForegroundColor White
Write-Host ""
Write-Host "🛠️  Development commands:" -ForegroundColor Cyan
Write-Host "  - Stop services: docker-compose -f docker-compose.dev.yml down" -ForegroundColor White
Write-Host "  - View logs: docker-compose -f docker-compose.dev.yml logs -f" -ForegroundColor White
Write-Host "  - Rebuild: docker-compose -f docker-compose.dev.yml up --build" -ForegroundColor White
Write-Host ""
Write-Host "Happy coding! 🚀" -ForegroundColor Green 