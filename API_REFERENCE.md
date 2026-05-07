# Agent Marketplace API Reference

## Base URL
```
http://localhost:8000
```

## Authentication

All protected endpoints require JWT bearer token:
```
Authorization: Bearer <token>
```

Get token via `/auth/login`:
```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"pass123"}'
```

---

## Agents Endpoints

### List Agents
```
GET /agents
```

**Response:**
```json
{
  "agents": [
    {
      "id": 1,
      "name": "ChatBot Pro",
      "description": "Advanced conversational AI",
      "category": "conversational",
      "price": 9.99,
      "is_purchased": false
    }
  ]
}
```

### Get Agent Details
```
GET /agents/{agent_id}
```

**Response:**
```json
{
  "id": 1,
  "name": "ChatBot Pro",
  "description": "Advanced conversational AI",
  "category": "conversational",
  "price": 9.99,
  "features": ["NLP", "Context aware", "Multi-language"],
  "is_purchased": false
}
```

### Purchase Agent
```
POST /agents/{agent_id}/purchase
Authorization: Bearer <token>
```

**Response:**
```json
{
  "purchase_id": 123,
  "agent_id": 1,
  "purchase_access_token": "eyJhbGc...",
  "purchased_api_url": "https://api.marketplace.com/agent/1/execute",
  "purchased_at": "2026-05-07T10:30:00Z"
}
```

### Get Purchase Access Details
```
GET /agents/{agent_id}/access-details
Authorization: Bearer <token>
```

**Response:**
```json
{
  "agent_id": 1,
  "agent_name": "ChatBot Pro",
  "is_purchased": true,
  "purchase_access_token": "eyJhbGc...",
  "purchased_api_url": "https://api.marketplace.com/agent/1/execute",
  "purchased_at": "2026-05-07T10:30:00Z",
  "expires_at": "2027-05-07T10:30:00Z"
}
```

---

## Auth Endpoints

### Register
```
POST /auth/register
Content-Type: application/json
```

**Body:**
```json
{
  "email": "user@example.com",
  "password": "secure123",
  "full_name": "John Doe"
}
```

**Response:**
```json
{
  "user_id": 1,
  "email": "user@example.com",
  "full_name": "John Doe",
  "created_at": "2026-05-07T10:00:00Z"
}
```

### Login
```
POST /auth/login
Content-Type: application/json
```

**Body:**
```json
{
  "email": "user@example.com",
  "password": "secure123"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGc...",
  "token_type": "bearer",
  "expires_in": 86400
}
```

### Get Profile
```
GET /auth/profile
Authorization: Bearer <token>
```

**Response:**
```json
{
  "user_id": 1,
  "email": "user@example.com",
  "full_name": "John Doe",
  "created_at": "2026-05-07T10:00:00Z",
  "purchases_count": 3
}
```

---

## A2A Messaging Endpoints

### Get Messages
```
GET /a2a/messages?agent_id={id}&limit=50
Authorization: Bearer <token>
```

### Send Message
```
POST /a2a/send
Authorization: Bearer <token>
Content-Type: application/json
```

**Body:**
```json
{
  "from_agent_id": 1,
  "to_agent_id": 2,
  "message": "Hello, other agent!",
  "metadata": {}
}
```

---

## Error Responses

### 400 Bad Request
```json
{
  "detail": "Invalid request parameters"
}
```

### 401 Unauthorized
```json
{
  "detail": "Invalid or missing authentication token"
}
```

### 404 Not Found
```json
{
  "detail": "Agent not found"
}
```

### 500 Server Error
```json
{
  "detail": "Internal server error"
}
```

---

## Rate Limiting

- Free tier: 100 requests/hour
- Premium: 10,000 requests/hour
- Enterprise: unlimited

Rate limit headers:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 50
X-RateLimit-Reset: 1620000000
```
