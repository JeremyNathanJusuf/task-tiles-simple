#!/bin/bash

# Task Tiles Development Environment Setup Script
echo "🚀 Setting up Task Tiles development environment..."

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "📝 Creating .env file..."
    cat > .env << EOF
# Backend Configuration
DATABASE_URL=sqlite:///data/task_tiles.db
PYTHONUNBUFFERED=1
PYTHONDONTWRITEBYTECODE=1

# Frontend Configuration
REACT_APP_API_URL=http://localhost:8000
CHOKIDAR_USEPOLLING=true

# Development Settings
NODE_ENV=development
EOF
    echo "✅ .env file created"
else
    echo "ℹ️  .env file already exists"
fi

# Check if Docker Compose is available
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker and Docker Compose first."
    exit 1
fi

# Build and start the development environment
echo "🔨 Building Docker containers..."
docker-compose -f docker-compose.dev.yml build

echo "🏃 Starting development environment..."
docker-compose -f docker-compose.dev.yml up -d

echo "⏳ Waiting for services to be ready..."
sleep 10

# Check if services are running
echo "🔍 Checking service status..."
docker-compose -f docker-compose.dev.yml ps

echo "🎉 Development environment is ready!"
echo ""
echo "📋 Access your application:"
echo "  - Frontend: http://localhost:3000"
echo "  - Backend API: http://localhost:8000"
echo "  - API Documentation: http://localhost:8000/docs"
echo ""
echo "🛠️  Development commands:"
echo "  - Stop services: docker-compose -f docker-compose.dev.yml down"
echo "  - View logs: docker-compose -f docker-compose.dev.yml logs -f"
echo "  - Rebuild: docker-compose -f docker-compose.dev.yml up --build"
echo ""
echo "Happy coding! 🚀" 