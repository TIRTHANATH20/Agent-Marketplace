# Scaling Guide

## Horizontal Scaling

### Load Balancing

```nginx
upstream backend {
    least_conn;
    server backend1.example.com:8000;
    server backend2.example.com:8000;
    server backend3.example.com:8000;
}

server {
    listen 80;
    server_name api.example.com;
    
    location / {
        proxy_pass http://backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

### Database Replication

```
Primary Database (Write)
├── Replica 1 (Read)
├── Replica 2 (Read)
└── Replica 3 (Read)
```

Setup replica:
```bash
# On primary
mysqldump -u root -p --all-databases > backup.sql

# On replica
mysql -u root -p < backup.sql
mysql> CHANGE MASTER TO MASTER_HOST='primary.ip', MASTER_USER='repl', MASTER_PASSWORD='pass';
mysql> START SLAVE;
```

### Connection Pooling

```python
from sqlalchemy.pool import QueuePool

engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=20,
    max_overflow=40,
    pool_pre_ping=True,
    pool_recycle=3600
)
```

## Vertical Scaling

### Instance Optimization

```bash
# Upgrade server specs
# t3.small (1 CPU, 2GB RAM) → t3.xlarge (4 CPU, 16GB RAM)

# Increase worker processes
gunicorn app:app --workers 8 --worker-class uvicorn.workers.UvicornWorker

# Optimize system limits
ulimit -n 65536
```

## Caching Layers

### Redis Cache

```python
from redis import Redis
from functools import wraps

redis = Redis(host='localhost', port=6379, db=0)

def cache(key_prefix: str, ttl: int = 3600):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            cache_key = f"{key_prefix}:{str(args)}:{str(kwargs)}"
            cached = redis.get(cache_key)
            
            if cached:
                return json.loads(cached)
            
            result = await func(*args, **kwargs)
            redis.setex(cache_key, ttl, json.dumps(result))
            return result
        return wrapper
    return decorator

@app.get("/agents")
@cache("agents", ttl=300)
async def get_agents():
    return db.query(Agent).all()
```

### CDN for Static Assets

```html
<!-- Instead of local -->
<img src="/static/logo.png" />

<!-- Use CDN -->
<img src="https://cdn.example.com/logo.png" />
```

## Database Optimization

### Indexing Strategy

```sql
-- Frequently queried fields
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_agents_category ON agents(category);
CREATE INDEX idx_purchases_user ON purchases(user_id);
CREATE INDEX idx_purchases_agent ON purchases(agent_id);

-- Composite indexes
CREATE INDEX idx_purchase_user_agent ON purchases(user_id, agent_id);

-- Full-text search
CREATE FULLTEXT INDEX idx_agents_search ON agents(name, description);
```

### Query Optimization

```python
# Bad: N+1 query problem
users = db.query(User).all()
for user in users:
    total_purchases = len(user.purchases)  # Query per user

# Good: Use aggregation
from sqlalchemy import func
users_with_count = db.query(
    User,
    func.count(Purchase.id).label('purchase_count')
).join(Purchase).group_by(User.id).all()
```

## Monitoring & Alerting

### Prometheus Metrics

```python
from prometheus_client import Counter, Histogram

request_count = Counter('http_requests_total', 'Total requests', ['method', 'endpoint'])
request_duration = Histogram('http_request_duration_seconds', 'Request duration')

@app.get("/agents")
@request_duration.time()
async def get_agents():
    request_count.labels(method='GET', endpoint='/agents').inc()
    return db.query(Agent).all()
```

### Health Checks

```python
@app.get("/health")
async def health_check():
    try:
        # Check database
        db.execute("SELECT 1")
        
        # Check Redis
        redis.ping()
        
        return {
            "status": "healthy",
            "database": "ok",
            "cache": "ok"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }
```

## Cost Optimization

### Spot Instances

```bash
# Use AWS Spot instances for non-critical work
aws ec2 request-spot-instances \
  --instance-count 5 \
  --type "one-time" \
  --spot-price "0.05" \
  --instance-type t3.large
```

### Auto Scaling

```yaml
# AWS Auto Scaling Group
MinSize: 2
MaxSize: 10
DesiredCapacity: 3
HealthCheckType: ELB
HealthCheckGracePeriod: 300
```

### Reserved Instances

```
Pay upfront for predictable traffic
- 1-year commitment: 35% discount
- 3-year commitment: 60% discount
```

## Disaster Recovery

### Backup Strategy

```bash
# Daily backups
0 2 * * * mysqldump -u root -p$MYSQL_PASS database | gzip > /backups/db-$(date +%Y%m%d).sql.gz

# Weekly full system backup
0 3 0 * * tar -czf /backups/full-$(date +%Y%m%d).tar.gz /var/www/
```

### Failover Setup

```
Active-Passive Setup:
┌─────────────┐
│  Primary    │ ← Active (traffic)
│  Database   │
└─────────────┘
       ↓ (replication)
┌─────────────┐
│  Secondary  │ ← Standby (ready)
│  Database   │
└─────────────┘

On failure: Switch traffic to secondary
```

## Performance Targets

| Metric | Target | Current |
|--------|--------|---------|
| API Response Time | < 200ms | 120ms |
| Database Query Time | < 100ms | 50ms |
| Page Load Time | < 3s | 1.5s |
| 99th Percentile Latency | < 500ms | 300ms |
| Uptime | 99.9% | 99.99% |
| Throughput | 1000 req/s | 500 req/s |
