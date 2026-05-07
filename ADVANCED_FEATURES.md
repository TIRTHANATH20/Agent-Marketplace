# Advanced Features

## Rate Limiting

### Token Bucket Algorithm

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.post("/auth/login")
@limiter.limit("5/minute")
async def login(request: Request, credentials: LoginRequest):
    pass

@app.get("/agents")
@limiter.limit("100/minute")
async def get_agents():
    pass
```

## Request Signing

### HMAC Signature Verification

```python
import hmac
import hashlib

def sign_request(method: str, path: str, body: str, secret: str) -> str:
    """Generate request signature"""
    message = f"{method}:{path}:{body}"
    signature = hmac.new(
        secret.encode(),
        message.encode(),
        hashlib.sha256
    ).hexdigest()
    return signature

def verify_signature(method: str, path: str, body: str, signature: str, secret: str) -> bool:
    """Verify request signature"""
    expected = sign_request(method, path, body, secret)
    return hmac.compare_digest(signature, expected)

@app.post("/agents/{agent_id}/purchase")
async def purchase_agent(
    agent_id: int,
    request: Request,
    current_user: User = Depends(get_current_user)
):
    body = await request.body()
    signature = request.headers.get("X-Signature")
    
    if not verify_signature(
        "POST",
        f"/agents/{agent_id}/purchase",
        body.decode(),
        signature,
        current_user.api_secret
    ):
        raise HTTPException(status_code=401, detail="Invalid signature")
```

## GraphQL API

```python
import strawberry
from fastapi import FastAPI
from strawberry.fastapi import GraphQLRouter

@strawberry.type
class AgentType:
    id: int
    name: str
    price: float
    description: str

@strawberry.type
class Query:
    @strawberry.field
    def get_agents(self) -> list[AgentType]:
        agents = db.query(Agent).all()
        return [
            AgentType(
                id=a.id,
                name=a.name,
                price=a.price,
                description=a.description
            )
            for a in agents
        ]
    
    @strawberry.field
    def get_agent(self, id: int) -> AgentType:
        agent = db.query(Agent).filter(Agent.id == id).first()
        return AgentType(
            id=agent.id,
            name=agent.name,
            price=agent.price,
            description=agent.description
        )

schema = strawberry.Schema(query=Query)
graphql_app = GraphQLRouter(schema)

app.include_router(graphql_app, prefix="/graphql")
```

## Batch Operations

```python
@app.post("/batch")
async def batch_operations(
    requests: list[dict],
    current_user: User = Depends(get_current_user)
):
    """Execute multiple operations in one request"""
    results = []
    
    for req in requests:
        method = req.get("method")
        endpoint = req.get("endpoint")
        data = req.get("data", {})
        
        if method == "GET" and endpoint == "/agents":
            result = db.query(Agent).all()
        elif method == "POST" and endpoint.startswith("/agents/"):
            agent_id = int(endpoint.split("/")[2])
            result = create_purchase(agent_id, current_user.id)
        
        results.append({"endpoint": endpoint, "result": result})
    
    return results
```

## Webhook Management

```python
from enum import Enum
from typing import List

class WebhookEvent(str, Enum):
    AGENT_PURCHASED = "agent.purchased"
    AGENT_CREATED = "agent.created"
    USER_REGISTERED = "user.registered"

class Webhook(Base):
    __tablename__ = "webhooks"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    url = Column(String)
    events = Column(JSON)  # List of events
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

async def trigger_webhook(event: WebhookEvent, data: dict):
    """Send webhook to all subscribers"""
    webhooks = db.query(Webhook).filter(
        Webhook.active == True,
        Webhook.events.contains(event)
    ).all()
    
    async with AsyncClient() as client:
        for webhook in webhooks:
            try:
                await client.post(
                    webhook.url,
                    json={"event": event, "data": data},
                    timeout=10
                )
            except Exception as e:
                logger.error(f"Webhook failed for {webhook.url}: {e}")

@app.post("/webhooks")
async def create_webhook(
    webhook_url: str,
    events: List[WebhookEvent],
    current_user: User = Depends(get_current_user)
):
    """Create new webhook subscription"""
    webhook = Webhook(
        user_id=current_user.id,
        url=webhook_url,
        events=events
    )
    db.add(webhook)
    db.commit()
    return webhook
```

## Event Sourcing

```python
from enum import Enum
from uuid import uuid4

class EventType(str, Enum):
    USER_CREATED = "user.created"
    AGENT_PURCHASED = "agent.purchased"
    MESSAGE_SENT = "message.sent"

class Event(Base):
    __tablename__ = "events"
    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    type = Column(String)
    aggregate_id = Column(String)  # Entity ID
    data = Column(JSON)
    timestamp = Column(DateTime, default=datetime.utcnow)
    version = Column(Integer)

async def store_event(
    event_type: EventType,
    aggregate_id: str,
    data: dict
):
    """Store event for replay and audit"""
    event = Event(
        type=event_type,
        aggregate_id=aggregate_id,
        data=data,
        version=1
    )
    db.add(event)
    db.commit()
    return event

@app.post("/agents/{agent_id}/purchase")
async def purchase_agent(
    agent_id: int,
    current_user: User = Depends(get_current_user)
):
    # Create purchase
    purchase = create_purchase(agent_id, current_user.id)
    
    # Store event
    await store_event(
        EventType.AGENT_PURCHASED,
        str(purchase.id),
        {
            "user_id": current_user.id,
            "agent_id": agent_id,
            "amount": purchase.amount
        }
    )
    
    # Trigger webhook
    await trigger_webhook(
        WebhookEvent.AGENT_PURCHASED,
        {"purchase_id": purchase.id, "user_id": current_user.id}
    )
    
    return purchase
```

## Circuit Breaker Pattern

```python
from enum import Enum
from datetime import datetime, timedelta

class CircuitState(Enum):
    CLOSED = "closed"       # Normal operation
    OPEN = "open"           # Failing, reject requests
    HALF_OPEN = "half_open" # Testing recovery

class CircuitBreaker:
    def __init__(self, failure_threshold=5, timeout=60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failures = 0
        self.state = CircuitState.CLOSED
        self.last_failure_time = None
    
    def call(self, func, *args, **kwargs):
        if self.state == CircuitState.OPEN:
            if datetime.now() - self.last_failure_time > timedelta(seconds=self.timeout):
                self.state = CircuitState.HALF_OPEN
            else:
                raise Exception("Circuit breaker is OPEN")
        
        try:
            result = func(*args, **kwargs)
            if self.state == CircuitState.HALF_OPEN:
                self.state = CircuitState.CLOSED
                self.failures = 0
            return result
        except Exception as e:
            self.failures += 1
            self.last_failure_time = datetime.now()
            if self.failures >= self.failure_threshold:
                self.state = CircuitState.OPEN
            raise

# Usage
breaker = CircuitBreaker(failure_threshold=3, timeout=60)

@app.get("/agents")
async def get_agents():
    def fetch_agents():
        return db.query(Agent).all()
    
    try:
        return breaker.call(fetch_agents)
    except Exception as e:
        logger.error(f"Circuit breaker triggered: {e}")
        return {"error": "Service temporarily unavailable"}
```
