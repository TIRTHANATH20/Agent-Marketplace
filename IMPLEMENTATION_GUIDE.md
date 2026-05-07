# Implementation Guide

## Backend Implementation

### Database Models

```python
from sqlalchemy import Column, Integer, String, DateTime, JSON
from datetime import datetime

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    full_name = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

class Agent(Base):
    __tablename__ = "agents"
    id = Column(Integer, primary_key=True)
    name = Column(String, index=True)
    description = Column(String)
    price = Column(Float)
    features = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)

class Purchase(Base):
    __tablename__ = "purchases"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    agent_id = Column(Integer, ForeignKey("agents.id"))
    access_token = Column(String, unique=True)
    purchased_at = Column(DateTime, default=datetime.utcnow)
```

### Authentication Implementation

```python
from passlib.context import CryptContext
from jose import JWTError, jwt

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=24)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt
```

### API Endpoints

```python
@app.post("/auth/login")
async def login(credentials: LoginRequest):
    user = db.query(User).filter(User.email == credentials.email).first()
    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    access_token = create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/agents")
async def list_agents(skip: int = 0, limit: int = 10):
    return db.query(Agent).offset(skip).limit(limit).all()

@app.post("/agents/{agent_id}/purchase")
async def purchase_agent(agent_id: int, current_user: User = Depends(get_current_user)):
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    purchase = Purchase(
        user_id=current_user.id,
        agent_id=agent_id,
        access_token=generate_token()
    )
    db.add(purchase)
    db.commit()
    return purchase
```

## Frontend Implementation

### React Components

```javascript
// AgentGrid.js
import React, { useState, useEffect } from 'react';
import axios from 'axios';

export default function AgentGrid() {
  const [agents, setAgents] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchAgents();
  }, []);

  const fetchAgents = async () => {
    try {
      const response = await axios.get(`${process.env.REACT_APP_API_BASE_URL}/agents`);
      setAgents(response.data);
    } catch (error) {
      console.error('Error fetching agents:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <div>Loading agents...</div>;

  return (
    <div className="agent-grid">
      {agents.map(agent => (
        <AgentCard key={agent.id} agent={agent} />
      ))}
    </div>
  );
}

// AgentCard.js
export function AgentCard({ agent }) {
  const [isPurchased, setIsPurchased] = useState(false);

  const handlePurchase = async () => {
    try {
      const token = localStorage.getItem('jwt_token');
      const response = await axios.post(
        `${process.env.REACT_APP_API_BASE_URL}/agents/${agent.id}/purchase`,
        {},
        { headers: { Authorization: `Bearer ${token}` } }
      );
      setIsPurchased(true);
      alert(`Purchase successful! Token: ${response.data.access_token}`);
    } catch (error) {
      alert('Purchase failed: ' + error.message);
    }
  };

  return (
    <div className="agent-card">
      <h3>{agent.name}</h3>
      <p>{agent.description}</p>
      <p>Price: ${agent.price}</p>
      <button onClick={handlePurchase} disabled={isPurchased}>
        {isPurchased ? 'Purchased' : 'Purchase'}
      </button>
    </div>
  );
}
```

### State Management

```javascript
// AuthContext.js
import React, { createContext, useState, useCallback } from 'react';

export const AuthContext = createContext();

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(localStorage.getItem('jwt_token'));

  const login = useCallback(async (email, password) => {
    const response = await fetch('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password })
    });
    const data = await response.json();
    setToken(data.access_token);
    localStorage.setItem('jwt_token', data.access_token);
  }, []);

  const logout = useCallback(() => {
    setUser(null);
    setToken(null);
    localStorage.removeItem('jwt_token');
  }, []);

  return (
    <AuthContext.Provider value={{ user, token, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}
```

## Testing Strategies

### Backend Testing

```python
# test_auth.py
def test_user_registration():
    response = client.post("/auth/register", json={
        "email": "test@example.com",
        "password": "test123",
        "full_name": "Test User"
    })
    assert response.status_code == 200
    assert response.json()["email"] == "test@example.com"

def test_user_login():
    response = client.post("/auth/login", json={
        "email": "admin@test.com",
        "password": "admin123"
    })
    assert response.status_code == 200
    assert "access_token" in response.json()
```

### Frontend Testing

```javascript
// AgentCard.test.js
import { render, screen, fireEvent } from '@testing-library/react';
import AgentCard from './AgentCard';

test('renders agent card with purchase button', () => {
  const agent = { id: 1, name: 'TestAgent', price: 9.99 };
  render(<AgentCard agent={agent} />);
  expect(screen.getByText('TestAgent')).toBeInTheDocument();
  expect(screen.getByRole('button', { name: /purchase/i })).toBeInTheDocument();
});
```

## Performance Optimization

### Caching Strategy

```python
from functools import lru_cache
from redis import Redis

redis_client = Redis(host='localhost', port=6379, db=0)

@app.get("/agents")
def get_agents(skip: int = 0):
    cache_key = f"agents:{skip}"
    cached = redis_client.get(cache_key)
    
    if cached:
        return json.loads(cached)
    
    agents = db.query(Agent).offset(skip).limit(10).all()
    redis_client.setex(cache_key, 300, json.dumps([a.dict() for a in agents]))
    return agents
```

### Database Optimization

```python
# Add indexes
db.execute("CREATE INDEX idx_user_email ON users(email)")
db.execute("CREATE INDEX idx_agent_name ON agents(name)")
db.execute("CREATE INDEX idx_purchase_user_id ON purchases(user_id)")
```

## Monitoring & Logging

```python
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.post("/agents/{agent_id}/purchase")
async def purchase_agent(agent_id: int, current_user: User = Depends(get_current_user)):
    logger.info(f"Purchase attempt: user={current_user.id}, agent={agent_id}")
    try:
        # Purchase logic
        logger.info(f"Purchase successful: user={current_user.id}, agent={agent_id}")
    except Exception as e:
        logger.error(f"Purchase failed: {str(e)}")
        raise
```
