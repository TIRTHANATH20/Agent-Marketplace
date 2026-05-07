# Best Practices for Agent Marketplace

## Code Quality

### Python Style Guide
- Use PEP 8 formatting
- Max line length: 100 characters
- Use type hints for all functions
- Document with docstrings

```python
def calculate_price(quantity: int, unit_price: float) -> float:
    """Calculate total price with tax.
    
    Args:
        quantity: Number of items
        unit_price: Price per item
        
    Returns:
        Total price including 10% tax
    """
    subtotal = quantity * unit_price
    return subtotal * 1.1
```

### JavaScript/React Guidelines
- Use functional components with hooks
- Extract components into separate files
- Use meaningful variable names
- Add PropTypes or TypeScript

```javascript
import PropTypes from 'prop-types';

function UserProfile({ userId, onUpdate }) {
  const [user, setUser] = React.useState(null);

  return <div>{user?.name}</div>;
}

UserProfile.propTypes = {
  userId: PropTypes.number.isRequired,
  onUpdate: PropTypes.func.isRequired,
};
```

## Architecture Patterns

### Repository Pattern

```python
class UserRepository:
    def __init__(self, db_session):
        self.db = db_session
    
    def get_by_id(self, user_id: int) -> User:
        return self.db.query(User).filter(User.id == user_id).first()
    
    def create(self, email: str, password: str) -> User:
        user = User(email=email, hashed_password=hash_password(password))
        self.db.add(user)
        self.db.commit()
        return user
```

### Dependency Injection

```python
from fastapi import Depends

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/users/{user_id}")
def get_user(user_id: int, db = Depends(get_db)):
    return db.query(User).filter(User.id == user_id).first()
```

## Error Handling

### Exception Strategy

```python
class AgentNotFoundError(Exception):
    """Raised when agent doesn't exist"""
    pass

class InsufficientCreditsError(Exception):
    """Raised when user has insufficient funds"""
    pass

@app.post("/agents/{agent_id}/purchase")
async def purchase(agent_id: int):
    try:
        agent = db.query(Agent).filter(Agent.id == agent_id).first()
        if not agent:
            raise AgentNotFoundError(f"Agent {agent_id} not found")
    except AgentNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except InsufficientCreditsError as e:
        raise HTTPException(status_code=402, detail=str(e))
```

## API Design

### RESTful Principles

```
GET    /agents                  # List all resources
GET    /agents/{id}             # Get one resource
POST   /agents                  # Create resource
PUT    /agents/{id}             # Update resource
DELETE /agents/{id}             # Delete resource
```

### Versioning

```python
@app.get("/v1/agents")
def list_agents_v1():
    pass

@app.get("/v2/agents")
def list_agents_v2():
    # Improved version with filtering
    pass
```

## Documentation

### Docstring Format

```python
def create_purchase(user_id: int, agent_id: int) -> dict:
    """Create a new agent purchase for a user.
    
    Args:
        user_id: The ID of the purchasing user
        agent_id: The ID of the agent being purchased
        
    Returns:
        Dictionary with keys:
        - purchase_id: Unique purchase identifier
        - access_token: JWT token for API access
        - purchased_at: Timestamp of purchase
        
    Raises:
        ValueError: If user or agent doesn't exist
        HTTPException: If purchase fails
    """
```

## Security Best Practices

### Input Validation

```python
from pydantic import BaseModel, validator, EmailStr

class PurchaseRequest(BaseModel):
    agent_id: int = Field(..., gt=0, description="Must be positive")
    quantity: int = Field(default=1, ge=1, le=100)
    
    @validator('agent_id')
    def agent_exists(cls, v):
        if not db.query(Agent).filter(Agent.id == v).first():
            raise ValueError('Agent does not exist')
        return v
```

### Rate Limiting

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.post("/auth/login")
@limiter.limit("5/minute")
def login(request: Request, credentials: LoginRequest):
    pass
```

## Testing

### Unit Test Example

```python
def test_purchase_success(client, db_session):
    user = create_test_user(db_session)
    agent = create_test_agent(db_session)
    
    response = client.post(
        f"/agents/{agent.id}/purchase",
        headers={"Authorization": f"Bearer {get_test_token(user)}"}
    )
    
    assert response.status_code == 200
    assert "access_token" in response.json()
```

### Integration Test Example

```python
@pytest.mark.asyncio
async def test_full_purchase_flow():
    # 1. Register user
    # 2. Login
    # 3. Browse agents
    # 4. Purchase agent
    # 5. Use access token
    pass
```

## Performance Considerations

### Query Optimization

```python
# Bad: N+1 query problem
users = db.query(User).all()
for user in users:
    purchases = user.purchases  # Triggers query for each user

# Good: Join query
users = db.query(User).join(Purchase).all()
```

### Caching

```python
@app.get("/agents")
async def get_agents(cache: Redis = Depends(get_redis)):
    cached = await cache.get("agents_list")
    if cached:
        return json.loads(cached)
    
    agents = db.query(Agent).all()
    await cache.setex("agents_list", 3600, json.dumps(agents))
    return agents
```

## Deployment Checklist

- [ ] All tests pass
- [ ] No console errors in browser
- [ ] Database migrations complete
- [ ] Environment variables set
- [ ] SSL/HTTPS enabled
- [ ] Logging configured
- [ ] Monitoring enabled
- [ ] Backups scheduled
- [ ] Rate limiting active
- [ ] Security headers set
