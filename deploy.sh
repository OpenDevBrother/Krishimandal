#!/bin/bash
set -e

echo "=== KrishiMandal EC2 Deploy Script ==="

# Install Docker (Amazon Linux 2023)
echo "Installing Docker..."
sudo yum update -y
sudo yum install -y docker
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker $USER

# Build and run
echo "Building Docker image..."
cd ~/app
docker build -t krishimandal .

# Stop existing container if running
docker stop krishimandal 2>/dev/null || true
docker rm krishimandal 2>/dev/null || true

echo "Starting container..."
docker run -d --name krishimandal -p 8000:8000 --restart unless-stopped krishimandal

# Seed database
echo "Seeding database..."
sudo docker exec krishimandal python -c "from src.seed_db import seed; seed()"

echo "=== Done! Backend running on port 8000 ==="
echo "Test: curl http://localhost:8000/docs"
