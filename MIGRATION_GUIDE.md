# Migration Guide

## Database Migration from SQLite to PostgreSQL

### Step 1: Install PostgreSQL

```bash
# macOS
brew install postgresql

# Linux (Ubuntu)
sudo apt-get install postgresql postgresql-contrib

# Windows
# Download from https://www.postgresql.org/download/windows/
```

### Step 2: Create PostgreSQL Database

```bash
# Start PostgreSQL
brew services start postgresql  # macOS

# Create database
psql -U postgres
CREATE DATABASE marketplace;
CREATE USER marketplace_user WITH PASSWORD 'secure_password';
ALTER ROLE marketplace_user SET client_encoding TO 'utf8';
GRANT ALL PRIVILEGES ON DATABASE marketplace TO marketplace_user;
```

### Step 3: Update Backend Configuration

```python
# Old (SQLite)
DATABASE_URL = "sqlite:///./marketplace.db"

# New (PostgreSQL)
DATABASE_URL = "postgresql://marketplace_user:secure_password@localhost:5432/marketplace"
```

### Step 4: Install PostgreSQL Driver

```bash
pip install psycopg2-binary
```

### Step 5: Run Migrations

```bash
# Using Alembic for migrations
alembic init alembic
alembic revision --autogenerate -m "Initial migration"
alembic upgrade head
```

### Step 6: Data Export/Import

```python
# Export from SQLite
import sqlite3
import pandas as pd

conn = sqlite3.connect('marketplace.db')
users = pd.read_sql_query("SELECT * FROM users", conn)
agents = pd.read_sql_query("SELECT * FROM agents", conn)

# Import to PostgreSQL
from sqlalchemy import create_engine
engine = create_engine('postgresql://marketplace_user:pass@localhost/marketplace')
users.to_sql('users', engine, if_exists='append', index=False)
agents.to_sql('agents', engine, if_exists='append', index=False)
```

## Backend Migration to FastAPI 0.100+

### Update Dependencies

```bash
# Old
pip install fastapi==0.95.0

# New
pip install fastapi==0.100.0
```

### API Changes

```python
# Old (async generator for dependencies)
async def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# New (lifespan parameter)
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app):
    # Startup
    yield
    # Shutdown

app = FastAPI(lifespan=lifespan)
```

## Frontend Migration to React 19

### Update Dependencies

```bash
npm update react@19 react-dom@19
```

### Hook Changes

```javascript
// Old: useEffect with empty array
useEffect(() => {
  fetchData();
}, []);

// New: useEffect with initializing
useEffect(() => {
  // Called once on mount
  return () => {
    // Cleanup
  };
}, []);
```

## Deployment Migration to Kubernetes

### Step 1: Create Docker Images

```dockerfile
# backend/Dockerfile
FROM python:3.10-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```dockerfile
# frontend/Dockerfile
FROM node:18-alpine as build
WORKDIR /app
COPY package*.json .
RUN npm install
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/build /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

### Step 2: Build and Push Images

```bash
docker build -t tirthanath20/marketplace-backend:1.0 backend/
docker build -t tirthanath20/marketplace-frontend:1.0 frontend/

docker push tirthanath20/marketplace-backend:1.0
docker push tirthanath20/marketplace-frontend:1.0
```

### Step 3: Create Kubernetes Manifests

```yaml
# backend-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: backend
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
        image: tirthanath20/marketplace-backend:1.0
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: db-secret
              key: url

---
apiVersion: v1
kind: Service
metadata:
  name: backend-service
spec:
  selector:
    app: backend
  ports:
  - protocol: TCP
    port: 8000
    targetPort: 8000
  type: LoadBalancer
```

### Step 4: Deploy to Kubernetes

```bash
kubectl apply -f backend-deployment.yaml
kubectl apply -f frontend-deployment.yaml
kubectl get pods
```

## Breaking Changes Checklist

- [ ] Database schema changes documented
- [ ] API endpoint changes documented
- [ ] Environment variables updated
- [ ] Dependencies upgraded
- [ ] Tests pass
- [ ] Migration scripts prepared
- [ ] Rollback plan documented
- [ ] Data backup created
- [ ] Performance tested
- [ ] Security reviewed

## Rollback Procedure

```bash
# If something goes wrong, revert to previous version

# 1. Stop current deployment
kubectl rollout undo deployment/backend

# 2. Restore database backup
psql marketplace < backup-2026-05-07.sql

# 3. Verify system
curl http://localhost:8000/health
```
