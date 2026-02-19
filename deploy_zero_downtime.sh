#!/bin/bash
# deploy-zero-downtime.sh
cd /home/exedev/bookmarko

echo "🔄 Pulling latest code..."
git pull

echo "🏗️   Building new images..."
docker compose build

echo "🔄 Rolling update..."
docker compose up -d --no-deps  --remove-orphans  --build
# Wait for health check
sleep 5

#docker compose up -d --no-deps --build
# Wait for health check
#sleep 5

echo "🧹 Cleaning up old images..."
docker image prune -f

echo "✅ Deployment complete!"
docker compose ps
