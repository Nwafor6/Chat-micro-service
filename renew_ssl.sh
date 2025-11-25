#!/bin/bash
# SSL Certificate Renewal Script for Docker Deployment
# Place this script in your project directory and add to crontab

set -e

PROJECT_DIR="/path/to/your/chat-service"  # Update this path
cd "$PROJECT_DIR"

echo "Starting SSL certificate renewal process..."

# Check if certificates need renewal (within 30 days)
if docker run --rm \
    -v $(pwd)/certbot/conf:/etc/letsencrypt \
    certbot/certbot certificates | grep -q "VALID: [0-2][0-9] day"; then
    
    echo "Certificates expiring soon, renewing..."
    
    # Stop nginx temporarily
    docker-compose -f docker-compose.dev.yml stop nginx
    
    # Renew certificates
    docker run --rm \
        -v $(pwd)/certbot/conf:/etc/letsencrypt \
        -v $(pwd)/certbot/www:/var/www/certbot \
        certbot/certbot renew --quiet
    
    # Start nginx again
    docker-compose -f docker-compose.dev.yml start nginx
    
    echo "SSL certificates renewed successfully!"
    
    # Optional: Restart nginx to pick up new certificates
    docker-compose -f docker-compose.dev.yml restart nginx
    
else
    echo "Certificates are still valid, no renewal needed."
fi

echo "SSL renewal check completed."