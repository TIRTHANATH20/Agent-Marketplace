# Architecture Overview

## System Design

```
┌─────────────┐         ┌──────────────┐         ┌─────────────┐
│   Browser   │◄───────►│   Nginx      │◄───────►│   FastAPI   │
│  (React)    │  HTTP   │   Reverse    │  HTTP   │   Backend   │
└─────────────┘         │   Proxy      │         └─────────────┘
                        └──────────────┘              │
                                                      ▼
                                            ┌──────────────────┐
                                            │  SQLite DB       │
                                            │  - Users         │
                                            │  - Agents        │
                                            │  - Purchases     │
                                            │  - Messages      │
                                            │  - Event Logs    │
                                            └──────────────────┘
```

## Component Architecture

### Frontend (React)
- **App.js**: Main application shell
- **Components/**:
  - `AgentGrid.js` - Agent listing view
  - `AgentModal.js` - Agent purchase & details modal
  - `AuthModal.js` - Login/register modal
  - `LogsPanel.js` - User activity logs
  - `MainContent.js` - Main layout container
  - `MCPToolsGrid.js` - Tool integration display
  - `A2APanel.js` - Agent messaging interface

### Backend (FastAPI)
```
main.py
├── Authentication Routes
│   ├── POST /auth/register
│   ├── POST /auth/login
│   └── GET /auth/profile
├── Agent Routes
│   ├── GET /agents
│   ├── GET /agents/{id}
│   └── POST /agents/{id}/purchase
├── A2A Messaging
│   ├── POST /a2a/send
│   └── GET /a2a/messages
└── Utilities
    ├── JWT token management
    ├── Password hashing (bcrypt)
    └── Event logging & redaction
```

### Database Schema
```
users
├── id (PK)
├── email (UNIQUE)
├── hashed_password
├── full_name
└── created_at

agents
├── id (PK)
├── name
├── description
├── category
├── price
├── features (JSON)
└── created_at

purchases
├── id (PK)
├── user_id (FK)
├── agent_id (FK)
├── access_token
├── purchased_at
└── expires_at

messages
├── id (PK)
├── from_agent_id (FK)
├── to_agent_id (FK)
├── message
├── created_at
└── metadata (JSON)

event_logs
├── id (PK)
├── event_type
├── user_id (FK)
├── details (JSON)
└── timestamp
```

## Data Flow

### Purchase Flow
1. User clicks "Buy Agent"
2. Frontend sends POST to `/agents/{id}/purchase` with JWT
3. Backend verifies user, creates purchase record
4. Backend generates purchase access token (short-lived JWT)
5. Backend returns token & API endpoint URL
6. Frontend immediately displays token to user
7. User can now call `/agent/{id}/execute` with this token

### Authentication Flow
1. User enters credentials in AuthModal
2. Frontend sends POST to `/auth/login`
3. Backend validates password with bcrypt
4. Backend returns JWT access token
5. Frontend stores token in state
6. All subsequent requests include `Authorization: Bearer <token>`
7. Backend validates token signature on each request

### A2A Messaging Flow
1. Agent A sends message to Agent B
2. Message stored in `messages` table
3. Event logged in `event_logs` (with redaction of sensitive data)
4. Agent B can retrieve messages via GET `/a2a/messages`
5. Full audit trail maintained

## Security Considerations

- **Passwords**: Hashed with bcrypt (cost factor 10)
- **Tokens**: JWT with HS256 signature, 24h expiry
- **CORS**: Configured to allow only authorized frontend domain
- **Logging**: Sensitive fields (tokens, passwords) redacted in logs
- **HTTPS**: Use in production (TLS 1.2+)
- **SQL Injection**: Protected via SQLAlchemy ORM parameterization
- **CSRF**: Frontend handles with double-submit cookies

## Scalability Considerations

**Current Bottlenecks**:
- Single SQLite database (not suitable for high concurrency)
- Synchronous FastAPI workers (good for < 100 concurrent users)

**Recommended Improvements**:
- Migrate to PostgreSQL for production
- Add Redis caching layer for agents list
- Implement connection pooling
- Use async/await throughout backend
- Add message queue (Celery) for long-running tasks
- Deploy multiple backend instances with load balancer

## Monitoring & Logging

- **Backend logs**: Stdout + file rotation
- **Database logs**: SQLite .log files (if enabled)
- **Client errors**: Sent to browser console + optional error tracking service
- **Metrics**: Response times, error rates tracked in event_logs
