# Agent Marketplace

> A modern marketplace platform for AI agents with authentication, real-time A2A communication, and comprehensive logging.

A complete agent marketplace system featuring **3 production-ready agents**, **agent-to-agent communication**, **secure authentication**, and a **beautiful reactive dashboard**.

---

## 🎯 Key Features

### 🤖 **3 Intelligent Agents**

- **Data Analyzer** (agent-001): Queries and analyzes business metrics, customer behavior, and trends
- **Query Executive** (agent-002): Executes targeted database queries and data retrieval
- **Report Generator** (agent-003): Creates comprehensive business reports and analytics

### 🔐 **Secure Authentication**

- JWT-based token authentication with secure secret keys
- User registration and login with password hashing (bcrypt)
- Demo access system with configurable free tier limits
- Unique UUID access keys for purchased agents
- Role-based access control (RBAC)

### 🔄 **Agent-to-Agent Communication (A2A)**

- Real-time message passing between agents
- Message queue with history tracking
- Complete communication audit trail
- Full request/response lifecycle logging

### 📊 **Comprehensive Logging & Monitoring**

- Real-time event logging with multiple severity levels (INFO, WARN, ERROR)
- Advanced filtering and search capabilities
- Log persistence for audit compliance
- Event tracking for all operations

### ✨ **Intuitive Dashboard**

- Agent discovery and capability browsing
- Agent-to-agent communication interface
- Live logs viewer with real-time filtering
- Purchase and access key management
- Dark modern design with Tailwind CSS

---

## 📋 Table of Contents

- [Quick Start](#quick-start)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Installation & Setup](#installation--setup)
- [Demo Credentials](#demo-credentials)
- [Core Concepts](#core-concepts)
- [API Endpoints](#api-endpoints)
- [Usage Guide](#usage-guide)
- [Security Features](#security-features)
- [Troubleshooting](#troubleshooting)
- [Future Enhancements](#future-enhancements)

---

## ⚡ Quick Start

Get up and running in 2 minutes:

### Prerequisites

- Python 3.8+
- A modern web browser
- Basic command-line familiarity

### 1. Start Backend (Terminal 1)

```bash
cd backend
pip install -r requirements.txt
python main.py
```

The API will be running at `http://localhost:8000`

### 2. Start Frontend (Terminal 2)

```bash
cd frontend
python -m http.server 8080
```

Open http://localhost:8080 in your browser

### 3. Login & Explore

Use demo credentials:
| Username | Password |
|----------|----------|
| admin | admin123 |
| user1 | user123 |

You now have **10 free queries per agent** to explore!

---

## 🛠 Tech Stack

- **Backend**: FastAPI, Python 3.8+
- **Frontend**: Vanilla JavaScript, Tailwind CSS
- **Database**: SQLite (Chinook sample database)
- **Authentication**: JWT tokens, bcrypt password hashing
- **Architecture**: RESTful API with real-time logging

---

## 📁 Project Structure

```
.
├── backend/
│   ├── main.py                    # FastAPI application & agent definitions
│   ├── requirements.txt           # Python dependencies
│   └── marketplace.log           # Runtime logs (generated)
├── frontend/
│   ├── index.html                # Single-page application entry
│   ├── package.json              # Frontend metadata
│   ├── public/                   # Static assets
│   └── src/
│       ├── App.js                # Main React component
│       ├── components/           # UI components
│       │   ├── AgentGrid.js
│       │   ├── AgentModal.js
│       │   ├── A2APanel.js
│       │   └── LogsPanel.js
│       └── index.js              # React entry point
├── agents.py                      # Example agent queries
├── README.md                      # This file
└── STATUS_REPORT.md              # Detailed implementation report

```

---

## 📦 Installation & Setup

### Prerequisites Check

Verify you have Python 3.8+:

```bash
python --version
```

### Step 1: Install Backend Dependencies

```bash
cd backend
pip install -r requirements.txt
```

**Required packages:**

- fastapi: Web framework
- uvicorn: ASGI server
- pydantic: Data validation
- bcrypt: Password hashing
- python-multipart: Form parsing

### Step 2: Start the Backend Server

```bash
cd backend
python main.py
```

Expected output:

```
INFO:     Uvicorn running on http://127.0.0.1:8000
```

### Step 3: Start the Frontend

Open a new terminal:

```bash
cd frontend
python -m http.server 8080
```

Then open **http://localhost:8080** in your browser.

---

## 🔐 Demo Credentials

Login with these test accounts:

| Username | Password | Role  |
| -------- | -------- | ----- |
| admin    | admin123 | Admin |
| user1    | user123  | User  |

---

## 💡 Core Concepts

### Demo Access System

Every new user gets **10 free queries per agent** to try before purchasing:

- Tracked server-side to prevent tampering
- Counter decrements with each query
- Returns "demo limit reached" after 10 queries
- Purchase grants unlimited access with a unique UUID key

### Agent Capabilities

Each agent specializes in different data operations:

| Agent                | ID        | Specialty                       |
| -------------------- | --------- | ------------------------------- |
| **Data Analyzer**    | agent-001 | Trends, metrics, top performers |
| **Query Executive**  | agent-002 | Precise database queries        |
| **Report Generator** | agent-003 | Comprehensive business reports  |

### Access Key Authentication

After purchasing an agent, you receive a UUID-based access key:

```
Authorization: Bearer 6be47ddd-53ab-4d02-92ec-e1b5c7ee1b7c
```

This allows unlimited queries to that specific agent.

---

## 🔐 Security Features

### Access Control

- ✅ JWT tokens and access keys are **never exposed in URLs**
- ✅ Credentials only visible when clicking "Access Details" on owned agents
- ✅ All credential requests authenticated via API (no storage in browser history)
- ✅ Each purchased agent gets unique UUID-based access key
- ✅ Only authenticated users can view their own access details

### Best Practices Built-In

- ✅ Password hashing with bcrypt (not reversible)
- ✅ Secure token generation and validation
- ✅ Audit trail for all operations
- ✅ Per-agent access control (demo vs purchased)

---

## 📚 API Endpoints

### Authentication

- `POST /auth/login` - Login user
- `POST /auth/register` - Register new user

### Agents

- `GET /agents` - Get all agents
- `GET /agents/{agent_id}` - Get agent details
- `GET /agents/{agent_id}/access-details` - Get access URL and key for owned agent (requires purchase)
- `POST /agents/{agent_id}/purchase` - Purchase an agent
- `POST /agents/send-message` - Send A2A message
- `GET /agents/{agent_id}/messages` - Get agent messages
- `GET /agents/{agent_id}/ask` - Query an agent (supports both JWT and access key authentication)
- `GET /agents/communication/history` - Get communication history

### Logs

- `GET /logs` - Get system logs
- `GET /logs/events` - Get unique event types
- `DELETE /logs` - Clear all logs (admin only)

### Health

- `GET /health` - Health check
- `GET /` - API info

---

## 🚀 Usage Guide

### Step 1: Login

1. Open http://localhost:8080
2. Enter test credentials (admin/admin123 or user1/user123)
3. Click "Login" to authenticate
4. You'll see your dashboard with 10 free queries per agent

### Step 2: Explore Agents

Navigate to **Agent Cards** tab to:
- View all 3 available agents with descriptions
- See each agent's capabilities
- Preview what data each agent can access
- Check your demo counter (starts at 10)

### Step 3: Query an Agent

1. Click "Ask" on any agent card
2. Enter your question (e.g., "What are the top genres?" for Data Analyzer)
3. View the response instantly
4. Your demo counter decrements
5. After 10 queries, you'll need to **Purchase** access

### Step 4: Purchase Agent Access

1. Click **"Purchase"** button on an agent
2. Receive a unique UUID access key
3. Copy the key and save it securely
4. You now have **unlimited queries** for that agent

### Step 5: A2A Communication

For advanced users, test agent-to-agent messaging:

1. Go to **"A2A Communication"** tab
2. Select "From Agent" and "To Agent"
3. Enter a JSON payload:
```json
{
  "action": "query",
  "data": "test request"
}
```
4. Click "Send Message"
5. View responses and communication history

### Step 6: Monitor System

View **Logs Viewer** tab to:
- See all system events in real-time
- Filter by event type
- Track authentication, queries, and A2A communication
- Monitor API access and performance

---

## 📋 Full API Reference

### Authentication Endpoints

- `POST /auth/login` - Login user
- `POST /auth/register` - Register new user

### Agent Endpoints
   - Agent communications
   - API access logs
   - System events

## Security Notes

⚠️ **Production Considerations:**

- Change `SECRET_KEY` in `main.py` to a secure random value
- Use environment variables for sensitive configuration
- Implement a real database (not in-memory)
- Add rate limiting and API key management
- Enable HTTPS/SSL for production
- Use proper user management system

## Architecture

```
┌─────────────────────────────────────────────────┐
│          Frontend (HTML/JS/Tailwind)            │
├─────────────────────────────────────────────────┤
│                   FastAPI Backend               │
│  ┌──────────────────────────────────────────┐   │
│  │          Authentication Layer             │   │
│  │  (JWT, Password Hashing, Permissions)    │   │
│  └──────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────┐   │
│  │      Agent Management System              │   │
│  │  (3 Agents with Capabilities)            │   │
│  └──────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────┐   │
│  │  A2A Communication Layer                  │   │
│  │  (Message Queue, History, Routing)       │   │
│  └──────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────┐   │
│  │        Logging System                     │   │
│  │  (Event Tracking, Audit Trail)           │   │
│  └──────────────────────────────────────────┘   │
└─────────────────────────────────────────────────┘
```

## Example: A2A Communication

From `Data Analyzer` to `Query Executive`:

```json
{
  "action": "fetch_metrics",
  "filters": {
    "date_range": "last_30_days",
    "category": "sales"
  },
  "format": "json"
}
```

This creates a log entry:

```
[2024-04-04 10:30:45] A2A_MESSAGE | {
  "message_id": "abc123...",
  "from": "agent-001",
  "to": "agent-002",
  "payload": {...}
}
```

## Troubleshooting

### CORS Errors

- Backend CORS is enabled for all origins (\* format)
- Ensure backend is running on `http://localhost:8000`

### Authentication Failed

- Verify username and password match test credentials
- Check browser console for error details

### Logs Not Showing

- Ensure you're logged in with valid token
- Check backend logs at `backend/marketplace.log`

### A2A Messages Not Sending

- Verify agent IDs are correct (agent-001, agent-002, agent-003)
- Ensure JSON payload is valid
- Check that both agents exist

## Future Enhancements

- [ ] Database persistence (PostgreSQL/MongoDB)
- [ ] Advanced agent routing with ML
- [ ] Real-time WebSocket notifications
- [ ] Agent performance metrics
- [ ] Rate limiting and quotas
- [ ] Multi-tenant support
- [ ] Agent versioning and rollback
- [ ] Custom agent creation UI

## License

MIT License - Feel free to use and modify

---

**Created:** April 4, 2026  
**Version:** 1.0
