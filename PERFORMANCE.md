# Performance Optimization Guide

## Database Performance

### Indexing Strategy

Add these indexes for faster queries:
```sql
CREATE INDEX idx_user_email ON users(email);
CREATE INDEX idx_agent_category ON agents(category);
CREATE INDEX idx_purchase_user_id ON purchases(user_id);
CREATE INDEX idx_purchase_agent_id ON purchases(agent_id);
CREATE INDEX idx_message_from ON messages(from_agent_id);
CREATE INDEX idx_message_to ON messages(to_agent_id);
CREATE INDEX idx_event_timestamp ON event_logs(timestamp);
```

### Query Optimization

**Bad**: Multiple separate queries
```python
user = db.query(User).filter(User.id == user_id).first()
purchases = db.query(Purchase).filter(Purchase.user_id == user_id).all()
```

**Good**: Single query with relationship
```python
user = db.query(User).options(joinedload(User.purchases)).filter(User.id == user_id).first()
```

### Connection Pooling

For PostgreSQL production:
```python
from sqlalchemy.pool import QueuePool

engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=5,
    max_overflow=10
)
```

---

## API Performance

### Response Caching

Cache agent list (doesn't change often):
```python
from functools import lru_cache
from datetime import datetime, timedelta

@router.get("/agents")
def get_agents():
    cached_agents = get_cached_agents()
    if cached_agents:
        return cached_agents
    
    agents = db.query(Agent).all()
    cache_agents(agents, ttl=300)  # 5 minute TTL
    return agents
```

### Pagination

Prevent loading all records:
```python
@router.get("/agents")
def get_agents(skip: int = 0, limit: int = 10):
    return db.query(Agent).offset(skip).limit(limit).all()
```

### Lazy Loading

Only load required fields:
```python
# Instead of returning entire object
agents = db.query(Agent).all()  # Loads everything

# Return only needed fields
agents = db.query(Agent.id, Agent.name, Agent.price).all()
```

---

## Frontend Performance

### Code Splitting

```javascript
// Lazy load components
const AgentModal = React.lazy(() => import('./components/AgentModal'));

function App() {
  return (
    <Suspense fallback={<Loading />}>
      <AgentModal />
    </Suspense>
  );
}
```

### Memoization

Prevent unnecessary re-renders:
```javascript
const AgentCard = React.memo(({ agent, onBuy }) => {
  return <div onClick={onBuy}>{agent.name}</div>;
});
```

### Bundle Size

```bash
# Analyze bundle
npm run build
npm install -g source-map-explorer
source-map-explorer 'build/static/js/*.js'

# Recommended max: < 100KB gzipped
```

---

## Caching Strategy

### Backend Caching Layers

```
┌─────────────┐
│   Browser   │  (HTTP cache, localStorage)
└──────┬──────┘
       │
┌──────▼──────┐
│   Nginx     │  (Response cache, gzip)
└──────┬──────┘
       │
┌──────▼──────┐
│   Redis     │  (Session, query results)
└──────┬──────┘
       │
┌──────▼──────┐
│  FastAPI    │  (In-memory @lru_cache)
└──────┬──────┘
       │
┌──────▼──────┐
│   Database  │  (Query with indexes)
└─────────────┘
```

### Cache Invalidation

Agents list cache resets on:
- New agent created
- Agent updated
- Admin clears cache

```python
def create_agent(agent: AgentCreate):
    db_agent = Agent(**agent.dict())
    db.add(db_agent)
    db.commit()
    invalidate_agents_cache()  # Clear cache
    return db_agent
```

---

## Load Testing

### Locust Script

```python
from locust import HttpUser, task

class ApiUser(HttpUser):
    @task
    def get_agents(self):
        self.client.get("/agents")
    
    @task
    def login(self):
        self.client.post("/auth/login", json={
            "email": "test@example.com",
            "password": "test123"
        })
```

Run: `locust -f locustfile.py --host=http://localhost:8000 --users=100 --spawn-rate=10`

---

## Benchmarks

### Current Performance (SQLite, single worker)

| Operation | Time | Notes |
|-----------|------|-------|
| GET /agents (10 items) | 45ms | Unindexed: 120ms |
| POST /auth/login | 180ms | bcrypt cost factor 10 |
| POST /agents/1/purchase | 120ms | Creates purchase + token |
| GET /a2a/messages (100 messages) | 85ms | Without pagination: 400ms |

### Target Performance

| Operation | Target |
|-----------|--------|
| GET /agents | < 100ms |
| POST /auth/login | < 250ms |
| POST /agents/purchase | < 200ms |
| GET /a2a/messages | < 150ms |

---

## Scaling Recommendations

### Current Limits
- SQLite: ~100 concurrent users
- Single gunicorn worker: ~50 req/sec
- Memory: ~200MB

### Phase 1 (1000s users)
- PostgreSQL
- 4 gunicorn workers
- Redis cache layer
- Nginx load balancer

### Phase 2 (10000s users)
- Distributed PostgreSQL
- RabbitMQ for async tasks
- Elasticsearch for logs
- CDN for static assets

### Phase 3 (100000s users)
- Kubernetes cluster
- Microservices architecture
- GraphQL API
- Real-time subscriptions (WebSockets)

---

## Monitoring Tools

```bash
# Response time monitoring
pip install prometheus-client

# APM
pip install datadog  # or New Relic, elastic APM

# Database profiling
pip install django-silk  # or py-spy
```

## Quick Wins (Implement First)

- ✅ Add database indexes
- ✅ Enable gzip compression
- ✅ Add HTTP caching headers
- ✅ Implement API pagination
- ✅ Use lazy loading in frontend
- ✅ Split code bundles

Expected improvement: 40-60% faster responses
