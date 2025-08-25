# Production Deployment Guide

This guide covers deploying the AI Customer Service Assistant to production environments with best practices for security, scalability, and reliability.

## Prerequisites

- Docker and Docker Compose
- Domain name with SSL certificate
- Cloud provider account (AWS, GCP, Azure)
- Database server (PostgreSQL recommended)
- Redis server for caching
- SMTP server for email notifications

## Environment Setup

### 1. Environment Variables

Create a `.env.production` file with the following variables:

```bash
# Application Settings
PROJECT_NAME="AI Customer Service Assistant"
VERSION="1.0.0"
API_V1_STR="/api/v1"
DEBUG=false
LOG_LEVEL="INFO"

# Database Configuration
DATABASE_URL="postgresql://user:password@db-host:5432/ai_customer_service"
USE_SQLITE=false

# Security
SECRET_KEY="your-super-secure-secret-key-here"
ALGORITHM="HS256"
ACCESS_TOKEN_EXPIRE_MINUTES=30

# OpenAI Configuration
OPENAI_API_KEY="your-openai-api-key"
OPENAI_MODEL="gpt-4"
MAX_TOKENS=2000
TEMPERATURE=0.7

# Redis Configuration
REDIS_URL="redis://redis-host:6379"

# CORS Origins
BACKEND_CORS_ORIGINS=["https://yourdomain.com"]

# Rate Limiting
RATE_LIMIT_PER_MINUTE=60

# Email Configuration
SMTP_SERVER="smtp.gmail.com"
SMTP_PORT=587
SMTP_USERNAME="your-email@gmail.com"
SMTP_PASSWORD="your-app-password"
FROM_EMAIL="noreply@yourdomain.com"

# Microservices Configuration (if using microservices)
MICROSERVICES_CONFIG={
  "user-service": {
    "name": "user-service",
    "host": "user-service",
    "port": 8001
  },
  "chat-service": {
    "name": "chat-service", 
    "host": "chat-service",
    "port": 8002
  }
}

# Monitoring
PROMETHEUS_ENABLED=true
GRAFANA_ENABLED=true
```

### 2. Production Docker Configuration

Create `docker-compose.prod.yml`:

```yaml
version: '3.8'

services:
  # Frontend
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile.prod
    ports:
      - "80:80"
      - "443:443"
    environment:
      - REACT_APP_API_URL=https://api.yourdomain.com
      - REACT_APP_WS_URL=wss://api.yourdomain.com
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/ssl:ro
    depends_on:
      - backend
    restart: unless-stopped

  # Backend
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile.prod
    ports:
      - "8000:8000"
    env_file:
      - .env.production
    environment:
      - DATABASE_URL=postgresql://postgres:${POSTGRES_PASSWORD}@db:5432/ai_customer_service
      - REDIS_URL=redis://redis:6379
    depends_on:
      - db
      - redis
    volumes:
      - ./logs:/app/logs
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  # Database
  db:
    image: postgres:15-alpine
    environment:
      - POSTGRES_DB=ai_customer_service
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./backups:/backups
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Redis
  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes --requirepass ${REDIS_PASSWORD}
    volumes:
      - redis_data:/data
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Nginx Load Balancer
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.prod.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/ssl:ro
      - ./logs:/var/log/nginx
    depends_on:
      - backend
    restart: unless-stopped

  # Monitoring
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/etc/prometheus/console_libraries'
      - '--web.console.templates=/etc/prometheus/consoles'
    restart: unless-stopped

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_PASSWORD}
    volumes:
      - grafana_data:/var/lib/grafana
      - ./monitoring/grafana/dashboards:/etc/grafana/provisioning/dashboards:ro
      - ./monitoring/grafana/datasources:/etc/grafana/provisioning/datasources:ro
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
  prometheus_data:
  grafana_data:
```

### 3. Production Nginx Configuration

Create `nginx.prod.conf`:

```nginx
events {
    worker_connections 1024;
}

http {
    upstream backend {
        server backend:8000;
        # Add more backend servers for load balancing
        # server backend2:8000;
        # server backend3:8000;
    }

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req_zone $binary_remote_addr zone=auth:10m rate=5r/s;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    # SSL Configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;

    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types
        text/plain
        text/css
        text/xml
        text/javascript
        application/javascript
        application/xml+rss
        application/json;

    server {
        listen 80;
        server_name yourdomain.com www.yourdomain.com;
        return 301 https://$server_name$request_uri;
    }

    server {
        listen 443 ssl http2;
        server_name yourdomain.com www.yourdomain.com;

        ssl_certificate /etc/ssl/cert.pem;
        ssl_certificate_key /etc/ssl/key.pem;

        # API endpoints
        location /api/ {
            limit_req zone=api burst=20 nodelay;
            proxy_pass http://backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            
            # Timeouts
            proxy_connect_timeout 30s;
            proxy_send_timeout 30s;
            proxy_read_timeout 30s;
        }

        # Authentication endpoints (stricter rate limiting)
        location /api/v1/auth/ {
            limit_req zone=auth burst=5 nodelay;
            proxy_pass http://backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # WebSocket support
        location /ws {
            proxy_pass http://backend;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # Health check (no rate limiting)
        location /health {
            proxy_pass http://backend;
            access_log off;
        }

        # Static files (if serving from backend)
        location /static/ {
            expires 1y;
            add_header Cache-Control "public, immutable";
            proxy_pass http://backend;
        }

        # Frontend (if serving from same domain)
        location / {
            root /usr/share/nginx/html;
            index index.html;
            try_files $uri $uri/ /index.html;
            
            # Cache static assets
            location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg)$ {
                expires 1y;
                add_header Cache-Control "public, immutable";
            }
        }
    }
}
```

## Deployment Strategies

### 1. Single Server Deployment

For small to medium workloads:

```bash
# 1. Clone repository
git clone https://github.com/your-repo/ai-customer-service.git
cd ai-customer-service

# 2. Set up environment
cp .env.example .env.production
# Edit .env.production with your values

# 3. Build and deploy
docker-compose -f docker-compose.prod.yml up -d

# 4. Run database migrations
docker-compose exec backend alembic upgrade head

# 5. Create admin user
docker-compose exec backend python scripts/create_admin.py

# 6. Verify deployment
curl https://yourdomain.com/health
```

### 2. Kubernetes Deployment

For high-availability and auto-scaling:

Create `k8s/namespace.yaml`:
```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: ai-customer-service
```

Create `k8s/backend-deployment.yaml`:
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: backend
  namespace: ai-customer-service
spec:
  replicas: 3
  selector:
    matchLabels:
      app: backend
  template:
    metadata:
      labels:
        app: backend
    spec:
      containers:
      - name: backend
        image: your-registry/ai-customer-service-backend:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: app-secrets
              key: database-url
        - name: REDIS_URL
          valueFrom:
            secretKeyRef:
              name: app-secrets
              key: redis-url
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "1Gi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: backend-service
  namespace: ai-customer-service
spec:
  selector:
    app: backend
  ports:
  - port: 8000
    targetPort: 8000
  type: ClusterIP
```

Deploy to Kubernetes:
```bash
kubectl apply -f k8s/
```

### 3. Cloud Provider Specific Deployments

#### AWS Deployment with ECS

```bash
# 1. Create ECS cluster
aws ecs create-cluster --cluster-name ai-customer-service

# 2. Build and push to ECR
aws ecr create-repository --repository-name ai-customer-service-backend
docker build -t ai-customer-service-backend ./backend
docker tag ai-customer-service-backend:latest 123456789.dkr.ecr.us-east-1.amazonaws.com/ai-customer-service-backend:latest
docker push 123456789.dkr.ecr.us-east-1.amazonaws.com/ai-customer-service-backend:latest

# 3. Create task definition and service
aws ecs register-task-definition --cli-input-json file://ecs-task-definition.json
aws ecs create-service --cluster ai-customer-service --service-name backend --task-definition backend:1 --desired-count 2
```

#### Google Cloud Deployment with Cloud Run

```bash
# 1. Build and deploy
gcloud builds submit --tag gcr.io/PROJECT-ID/ai-customer-service-backend ./backend
gcloud run deploy ai-customer-service-backend \
  --image gcr.io/PROJECT-ID/ai-customer-service-backend \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars="DATABASE_URL=postgresql://..." \
  --memory=1Gi \
  --cpu=1 \
  --max-instances=10
```

## Monitoring and Observability

### 1. Prometheus Configuration

Create `monitoring/prometheus.yml`:
```yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'ai-customer-service'
    static_configs:
      - targets: ['backend:8000']
    scrape_interval: 5s
    metrics_path: /metrics

  - job_name: 'node-exporter'
    static_configs:
      - targets: ['node-exporter:9100']

rule_files:
  - "alerts.yml"

alerting:
  alertmanagers:
    - static_configs:
        - targets:
          - alertmanager:9093
```

### 2. Grafana Dashboards

Create monitoring dashboards for:
- System metrics (CPU, memory, disk)
- Application metrics (response times, error rates)
- Business metrics (active conversations, user activity)
- Database performance
- Redis performance

### 3. Log Aggregation

Use ELK stack or cloud logging:

```yaml
# Add to docker-compose.prod.yml
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.5.0
    environment:
      - discovery.type=single-node
      - "ES_JAVA_OPTS=-Xms512m -Xmx512m"
    volumes:
      - elasticsearch_data:/usr/share/elasticsearch/data

  logstash:
    image: docker.elastic.co/logstash/logstash:8.5.0
    volumes:
      - ./logstash.conf:/usr/share/logstash/pipeline/logstash.conf:ro
      - ./logs:/logs:ro

  kibana:
    image: docker.elastic.co/kibana/kibana:8.5.0
    ports:
      - "5601:5601"
    environment:
      - ELASTICSEARCH_HOSTS=http://elasticsearch:9200
```

## Security Best Practices

### 1. Application Security
- Use HTTPS everywhere
- Implement proper authentication and authorization
- Validate all inputs
- Use parameterized queries
- Keep dependencies updated
- Implement rate limiting
- Use security headers

### 2. Infrastructure Security
- Use firewalls and security groups
- Implement network segmentation
- Regular security audits
- Encrypted databases
- Secure secrets management
- Regular backups

### 3. Monitoring Security Events
- Failed login attempts
- Unusual access patterns
- API abuse
- Data access auditing

## Backup and Disaster Recovery

### 1. Database Backup Strategy

```bash
#!/bin/bash
# backup.sh
BACKUP_DIR="/backups"
DATE=$(date +%Y%m%d_%H%M%S)

# PostgreSQL backup
docker-compose exec -T db pg_dump -U postgres ai_customer_service > $BACKUP_DIR/db_backup_$DATE.sql

# Compress backup
gzip $BACKUP_DIR/db_backup_$DATE.sql

# Upload to cloud storage
aws s3 cp $BACKUP_DIR/db_backup_$DATE.sql.gz s3://your-backup-bucket/

# Clean old backups (keep last 30 days)
find $BACKUP_DIR -name "db_backup_*.sql.gz" -mtime +30 -delete
```

### 2. Application Data Backup

```bash
#!/bin/bash
# backup-app-data.sh

# Backup logs
tar -czf /backups/logs_$(date +%Y%m%d).tar.gz ./logs/

# Backup configuration
cp .env.production /backups/env_$(date +%Y%m%d).backup

# Backup Redis data
docker-compose exec redis redis-cli --rdb /data/dump_$(date +%Y%m%d).rdb
```

### 3. Disaster Recovery Plan

1. **Recovery Time Objective (RTO)**: 4 hours
2. **Recovery Point Objective (RPO)**: 1 hour
3. **Backup Frequency**: Daily database, hourly logs
4. **Testing**: Monthly disaster recovery drills

## Performance Optimization

### 1. Database Optimization
- Connection pooling
- Query optimization
- Proper indexing
- Read replicas for scaling reads

### 2. Application Optimization
- Async operations
- Caching strategies
- Background task processing
- Connection pooling

### 3. Infrastructure Optimization
- Load balancing
- CDN for static assets
- Auto-scaling policies
- Resource monitoring

## Troubleshooting

### Common Issues

1. **High Response Times**
   ```bash
   # Check system resources
   docker stats
   
   # Check database performance
   docker-compose exec db psql -U postgres -c "SELECT * FROM pg_stat_activity;"
   
   # Check application logs
   docker-compose logs backend
   ```

2. **Database Connection Issues**
   ```bash
   # Test database connectivity
   docker-compose exec backend python -c "from app.core.database import engine; print(engine.execute('SELECT 1').scalar())"
   ```

3. **Redis Connection Issues**
   ```bash
   # Test Redis connectivity
   docker-compose exec redis redis-cli ping
   ```

### Health Check Script

```bash
#!/bin/bash
# health-check.sh

echo "Checking system health..."

# Check if services are running
docker-compose ps

# Check health endpoints
curl -f http://localhost:8000/health || echo "Backend health check failed"

# Check database
docker-compose exec -T db pg_isready -U postgres || echo "Database not ready"

# Check Redis
docker-compose exec -T redis redis-cli ping || echo "Redis not responding"

echo "Health check complete"
```

This deployment guide provides a comprehensive approach to deploying the AI Customer Service Assistant in production environments with proper monitoring, security, and scalability considerations.
