#!/bin/bash

# Script to start both backend and frontend in development mode

echo "Starting Task Tiles Development Environment..."

# Initialize database if it doesn't exist
if [ ! -f "backend/data/task_tiles.db" ]; then
    echo "Initializing database..."
    cd backend && python init_db.py && cd ..
fi

# Start both services using concurrently
echo "Starting backend and frontend services..."
concurrently \
    --names "BACKEND,FRONTEND" \
    --prefix-colors "blue,green" \
    --kill-others \
    "cd backend && uvicorn main:app --host 0.0.0.0 --port 8000 --reload" \
    "cd frontend && npm start" 