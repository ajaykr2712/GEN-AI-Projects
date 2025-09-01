# Deployment Guide

## Overview

This guide covers different deployment options for the AI Customer Service Assistant system.

## Prerequisites

- Docker & Docker Compose (recommended)
- Python 3.8+ (for manual deployment)
- Node.js 16+ (for manual deployment)
- PostgreSQL 12+ (for production)
- Redis (for caching)

## Quick Start with Docker

### 1. Clone and Setup
```bash
git clone <repository-url>
cd ai-customer-service
```

### 2. Environment Configuration
```bash
cp backend/.env.example backend/.env
```

Edit `backend/.env` and set your OpenAI API key:
```
OPENAI_API_KEY=your-api-key-here
```

### 3. Start Services
```bash
docker-compose up -d
```

### 4. Initialize Database
```bash
docker-compose exec backend python scripts/init_db.py
```

### 5. Access Application
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Documentation: http://localhost:8000/docs

## Manual Deployment

### Backend Setup

1. **Create Virtual Environment**
```bash
cd backend
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. **Install Dependencies**
```bash
pip install -r requirements.txt
```

3. **Configure Environment**
```bash
cp .env.example .env
# Edit .env with your configuration
```

4. **Initialize Database**
```bash
python scripts/init_db.py
```

5. **Start Backend**
```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

### Frontend Setup

1. **Install Dependencies**
```bash
cd frontend
npm install
```

2. **Start Frontend**
```bash
npm start
```

## Production Deployment

### Using Docker Compose with Production Profile

1. **Production Configuration**
```bash
# Create production environment file
cp backend/.env.example backend/.env.prod

# Edit with production values
# - Set USE_SQLITE=false
# - Configure PostgreSQL DATABASE_URL
# - Set strong SECRET_KEY
# - Configure CORS origins
```

2. **Start Production Services**
```bash
docker-compose --profile production up -d
```

### Cloud Deployment Options

#### AWS Deployment

1. **ECS with Fargate**
   - Deploy containers using AWS ECS
   - Use RDS for PostgreSQL
   - Use ElastiCache for Redis
   - Configure ALB for load balancing

2. **Elastic Beanstalk**
   - Deploy using Docker Compose
   - Configure environment variables
   - Set up RDS and ElastiCache

#### Google Cloud Platform

1. **Cloud Run**
   - Deploy containerized services
   - Use Cloud SQL for PostgreSQL
   - Use Memorystore for Redis

2. **GKE (Google Kubernetes Engine)**
   - Deploy using Kubernetes manifests
   - Configure services and ingress
   - Use managed databases

#### Heroku

1. **Backend Deployment**
```bash
# In backend directory
heroku create your-app-backend
heroku addons:create heroku-postgresql:hobby-dev
heroku addons:create heroku-redis:hobby-dev
git push heroku main
```

2. **Frontend Deployment**
```bash
# In frontend directory
heroku create your-app-frontend
heroku buildpacks:set heroku/nodejs
git push heroku main
```

### Environment Variables for Production

**Backend (.env.prod)**
```
# Database
DATABASE_URL=postgresql://user:password@localhost/ai_customer_service
USE_SQLITE=false

# Security
SECRET_KEY=your-super-secret-production-key-64-characters-minimum
ACCESS_TOKEN_EXPIRE_MINUTES=30

# OpenAI
OPENAI_API_KEY=your-openai-api-key

# Redis
REDIS_URL=redis://localhost:6379

# CORS
BACKEND_CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com

# Logging
LOG_LEVEL=INFO
LOG_FILE=/var/log/app.log
```

## Monitoring and Logging

### Application Monitoring

1. **Health Checks**
   - Backend: `GET /health`
   - Monitor response time and status

2. **Metrics Collection**
   - Implement Prometheus metrics
   - Monitor API response times
   - Track conversation metrics

3. **Log Aggregation**
   - Use structured logging
   - Implement log rotation
   - Consider ELK stack or cloud logging

### Database Monitoring

1. **PostgreSQL**
   - Monitor connection pools
   - Track query performance
   - Set up automated backups

2. **Redis**
   - Monitor memory usage
   - Track cache hit rates
   - Set up persistence

## Security Considerations

### Authentication & Authorization

1. **JWT Token Security**
   - Use strong secret keys
   - Implement token rotation
   - Set appropriate expiration times

2. **Password Security**
   - Enforce strong password policies
   - Use bcrypt for hashing
   - Implement rate limiting

### API Security

1. **CORS Configuration**
   - Set specific origins in production
   - Avoid wildcard origins

2. **Rate Limiting**
   - Implement request rate limiting
   - Use Redis for rate limit storage

3. **Input Validation**
   - Validate all inputs
   - Sanitize user data
   - Use Pydantic for validation

### Data Protection

1. **Database Security**
   - Use SSL connections
   - Encrypt sensitive data
   - Regular security updates

2. **OpenAI API Key**
   - Store securely in environment variables
   - Rotate keys regularly
   - Monitor usage and costs

## Scaling Considerations

### Horizontal Scaling

1. **Multiple Backend Instances**
   - Use load balancer
   - Implement session storage in Redis
   - Ensure stateless design

2. **Database Scaling**
   - Read replicas for PostgreSQL
   - Connection pooling
   - Query optimization

### Performance Optimization

1. **Caching Strategy**
   - Cache frequently accessed data
   - Implement API response caching
   - Use Redis for session storage

2. **Frontend Optimization**
   - Code splitting
   - Image optimization
   - CDN for static assets

## Backup and Recovery

### Database Backups

1. **Automated Backups**
   - Daily PostgreSQL dumps
   - Point-in-time recovery
   - Cross-region backup storage

2. **Backup Testing**
   - Regular restore testing
   - Documented recovery procedures
   - RTO/RPO definitions

### Application Backups

1. **Configuration Backups**
   - Environment variables
   - Application configurations
   - Infrastructure as Code

2. **Code Repository**
   - Version control
   - Tagged releases
   - Branch protection

## Troubleshooting

### Common Issues

1. **Database Connection Issues**
   - Check connection strings
   - Verify network connectivity
   - Check credentials

2. **OpenAI API Issues**
   - Verify API key
   - Check rate limits
   - Monitor API quotas

3. **Frontend-Backend Communication**
   - Check CORS settings
   - Verify API endpoints
   - Check authentication tokens

### Debugging Tools

1. **Backend Debugging**
   - Check application logs
   - Use FastAPI debug mode
   - Monitor database queries

2. **Frontend Debugging**
   - Browser developer tools
   - Network tab inspection
   - React DevTools

## Support and Maintenance

### Regular Maintenance

1. **Security Updates**
   - Regular dependency updates
   - Security patch management
   - Vulnerability scanning

2. **Performance Monitoring**
   - Regular performance reviews
   - Capacity planning
   - Resource optimization

### Getting Help

1. **Documentation**
   - API documentation at `/docs`
   - Frontend component documentation
   - Database schema documentation

2. **Community Support**
   - GitHub issues
   - Community forums
   - Stack Overflow tags
