#!/bin/bash
# SSL Certificate Renewal Script for Docker Deployment
# Place this script in your project directory and add to crontab

set -e

PROJECT_DIR="/home/build/programming/website/bildup_projects/chat-service-global"  # Updated path
cd "$PROJECT_DIR"

echo "Starting SSL certificate renewal process..."

# Check if certificates need renewal (within 30 days)
if docker run --rm \
    -v $(pwd)/certbot/conf:/etc/letsencrypt \
    certbot/certbot certificates | grep -q "VALID: [0-2][0-9] day"; then
    
    echo "Certificates expiring soon, renewing..."
    
    # Stop nginx temporarily
    docker-compose -f docker-compose.dev.yml stop nginx
    
    # Stop any conflicting services on port 80
    SERVICES_ON_80=$(docker ps --format "table {{.Names}}\t{{.Ports}}" | grep ":80->" | awk '{print $1}' | tr '\n' ' ')
    if [ ! -z "$SERVICES_ON_80" ]; then
      echo "Temporarily stopping services on port 80: $SERVICES_ON_80"
      for service in $SERVICES_ON_80; do
        docker stop $service
      done
    fi
    
    # Renew certificates using standalone mode
    docker run --rm \
        -p 80:80 \
        -v $(pwd)/certbot/conf:/etc/letsencrypt \
        certbot/certbot renew --quiet
    
    # Restart the services we stopped
    if [ ! -z "$SERVICES_ON_80" ]; then
      echo "Restarting services: $SERVICES_ON_80"
      for service in $SERVICES_ON_80; do
        docker start $service
      done
    fi
    
    # Start nginx again
    docker-compose -f docker-compose.dev.yml start nginx
    
    echo "SSL certificates renewed successfully!"
    
    # Optional: Restart nginx to pick up new certificates
    docker-compose -f docker-compose.dev.yml restart nginx
    
else
    echo "Certificates are still valid, no renewal needed."
fi

echo "SSL renewal check completed."