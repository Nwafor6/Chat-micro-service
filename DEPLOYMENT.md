# Chat Microservice Deployment Update

## Summary of Changes

This deployment has been updated to be a standalone, generic chat microservice with the following improvements:

### 1. Project Naming
- Changed from "BildupAI Chat Service" to "Global Chat Service" / "Chat Microservice"
- Updated all references from `bildupai_chat` to `chat-micro-service`
- Docker image name: `nwafor6/chat-micro-service:dev`

### 2. Docker Infrastructure Changes
- **Added Nginx container** for reverse proxy and SSL termination
- **Removed PostgreSQL container** - now uses external production database
- **Updated Redis container** to use port 6381 (was 6380) to avoid conflicts
- **Environment variables built into Docker image** instead of external .env files

### 3. Port Allocation (to avoid conflicts with existing services)
- **Application**: Internal port 8080 (no external mapping)
- **Nginx**: Port 8003 (HTTP) and 443 (HTTPS)
- **Redis**: Port 6381 (was 6380)

### 4. SSL/TLS Configuration
- **Automated SSL certificate generation** using Let's Encrypt
- **SSL certificates managed by Certbot** and copied to Docker volumes
- **HTTPS redirect** configured in Nginx
- **Domain**: `chat.valcertra.com`

### 5. Environment Variable Management
- Environment variables are now **built directly into the Docker image**
- Sensitive values (DATABASE_URL, JWT_SECRET_KEY) passed via docker-compose environment
- No more .env files being created during deployment

### 6. Security Improvements
- **Rate limiting** for API endpoints and WebSocket connections
- **Security headers** configured in Nginx
- **SSL/TLS best practices** implemented

## Deployment Process

1. **Docker Build & Push** - Updated image names
2. **Docker Installation** - Ensures Docker is available on server
3. **Nginx Setup** - Installs Nginx system-wide for initial SSL setup
4. **SSL Certificate** - Automated Let's Encrypt certificate generation
5. **Environment Setup** - Creates SSL directories and copies certificates
6. **Docker Deployment** - Starts Redis, Web, and Nginx containers
7. **Database Migrations** - Runs Alembic migrations against production DB
8. **Health Checks** - Tests application health through Nginx

## Service URLs

- **Main Service**: https://chat.valcertra.com
- **Health Check**: https://chat.valcertra.com/health
- **WebSocket Docs**: https://chat.valcertra.com/api/v1/docs/websockets
- **API Docs**: https://chat.valcertra.com/docs (dev/staging only)

## Container Architecture

```
Internet → Nginx (Port 8003/443) → FastAPI (Port 8080)
                                  ↓
                              Redis (Port 6381)
                                  ↓
                          External PostgreSQL DB
```

## Key Benefits

1. **Standalone deployment** - No conflicts with existing services
2. **Production-ready SSL** - Automated certificate management
3. **Scalable architecture** - Nginx reverse proxy for load balancing
4. **Secure configuration** - Rate limiting, security headers, HTTPS
5. **Clean environment management** - No external config files
6. **Independent Redis** - Separate Redis instance for this service