#!/bin/bash

# Stop all running containers
echo "Stopping any running containers..."
docker compose down

# Remove old containers and volumes if they exist
echo "Removing old containers and volumes..."
docker compose rm -f
# docker volume prune -f

# Build and start the services
echo "Building and starting services..."
docker compose up --build -d

# Wait for services to be ready
echo "Waiting for services to be ready..."
sleep 10

# Check if services are running
echo "Checking service status..."
docker compose ps

echo "Application is running!"
echo "FastAPI backend available at: http://localhost:8000"
echo "Streamlit frontend available at: http://localhost:8501"
echo "Prometheus metrics at: http://localhost:9090"
