<div align="center">

# 🤖 Agent Marketplace

**Discover, purchase, and manage AI agents with enterprise-grade authentication**

A full-stack marketplace platform featuring secure JWT authentication, one-click agent purchases, real-time A2A messaging, and comprehensive operational logging.

[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10+-3776ab?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![Node.js](https://img.shields.io/badge/Node-18+-339933?style=flat-square&logo=node.js&logoColor=white)](https://nodejs.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0F4C81?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-61DAFB?style=flat-square&logo=react&logoColor=white)](https://react.dev)

</div>

<p align="center">
  <img src="assets/agent-marketplace-banner.svg" alt="Agent Marketplace banner" width="100%" />
</p>

---

## 📖 Quick Navigation

[Features](#-key-features) • [Tech Stack](#-tech-stack) • [Setup](#-quick-start) • [API](#-api-endpoints) • [Docs](#-documentation) • [Deployment](#-deployment) • [License](#-license)

---

## 🎯 Overview

Agent Marketplace is a production-ready platform for discovering, purchasing, and managing AI agents. It provides:

- **Secure marketplace**: Browse agents with detailed capabilities and pricing
- **Instant access**: Purchase agents and get immediate API credentials
- **Agent communication**: Send messages between agents and track history
- **Live monitoring**: Real-time event logs for all platform activity
- **Enterprise auth**: JWT tokens, password hashing, CORS protection

---

## ✨ Key Features

### 🛍️ Marketplace
- Browse available AI agents with detailed profiles
- View agent capabilities, pricing, and status
- One-click purchasing with instant access
- Favorites and wishlist management

### 🔐 Security & Auth
- JWT-based authentication with 24-hour expiry
- Passwords hashed with bcrypt (cost factor 10)
- Purchase access tokens with unique API endpoints
- CORS protection and security headers
- Audit trail for all transactions

### 💬 Communication
- Agent-to-agent (A2A) messaging
- Real-time message history
- JSON payload support
- Metadata tracking

### 📊 Operations
- Comprehensive event logging
- Real-time activity monitoring
- API usage tracking
- Performance metrics
- Sensitive data redaction in logs

---

## 🛠️ Tech Stack

### Backend
```
FastAPI 0.95+       API framework with async support
Pydantic            Data validation and serialization
SQLAlchemy          ORM for database operations
SQLite              Lightweight database (PostgreSQL ready)
python-jose         JWT token generation and validation
bcrypt              Password hashing and verification
Groq API            LLM integration for agent responses
```

### Frontend
```
React 18            Component-based UI framework
React Router        Client-side routing
Axios               HTTP client for API calls
CSS3                Modern styling with animations
```

### DevOps
```
Nginx               Reverse proxy and load balancing
Uvicorn             ASGI server for Python
GitHub Actions      CI/CD pipeline
```

---

## 📁 Project Structure

```
Agent-Marketplace/
├── backend/
│   ├── main.py                 # FastAPI app with all endpoints
│   ├── requirements.txt         # Python dependencies
│   └── .env                    # Configuration (create locally)
│
├── frontend/
│   ├── public/
│   │   └── index.html
│   ├── src/
│   │   ├── App.js              # Main React component
│   │   ├── App.css             # Styling
│   │   ├── index.js            # Entry point
│   │   └── components/
│   │       ├── AgentGrid.js     # Agent listing
│   │       ├── AgentModal.js    # Purchase flow
│   │       ├── AuthModal.js     # Login/register
│   │       ├── LogsPanel.js     # Activity logs
│   │       ├── MCPToolsGrid.js  # Tool display
│   │       └── A2APanel.js      # Messaging
│   ├── package.json
│   └── .env                    # API endpoint config
│
├── Documentation/
│   ├── SETUP_GUIDE.md          # Local dev setup
│   ├── DEPLOYMENT.md           # Production deployment
│   ├── API_REFERENCE.md        # Endpoint documentation
│   ├── ARCHITECTURE.md         # System design
│   ├── SECURITY.md             # Security practices
│   ├── TESTING.md              # Test procedures
│   ├── TROUBLESHOOTING.md      # Common issues
│   ├── PERFORMANCE.md          # Optimization guide
│   └── FAQ.md                  # Questions & answers
│
├── LICENSE                      # MIT License
├── CHANGELOG.md                # Release notes
└── .github/
    └── workflows/
        └── ci.yml              # GitHub Actions CI
```

---

## 🚀 Quick Start

### Prerequisites
- **Python** 3.10 or higher
- **Node.js** 18 or higher
- **Git** for version control

### Step 1: Clone Repository
```bash
git clone https://github.com/TIRTHANATH20/Agent-Marketplace.git
cd Agent-Marketplace
```

### Step 2: Backend Setup
```bash
cd backend
python -m venv .venv

# Activate virtual environment
source .venv/bin/activate              # macOS/Linux
# OR
.venv\Scripts\activate                 # Windows

# Install dependencies
pip install -r requirements.txt

# Create .env file
cat > .env << EOF
DATABASE_URL=sqlite:///./marketplace.db
JWT_SECRET_KEY=your-secret-key-min-32-chars
ENVIRONMENT=development
FRONTEND_URL=http://localhost:3000
EOF

# Start backend
python main.py
```

Backend runs at `http://localhost:8000` | API docs at `http://localhost:8000/docs`

### Step 3: Frontend Setup
```bash
cd frontend
npm install

# Create .env file
echo "REACT_APP_API_BASE_URL=http://localhost:8000" > .env

# Start development server
npm start
```

Frontend opens at `http://localhost:3000`

### Step 4: Test with Demo Account

| Email | Password |
|-------|----------|
| `admin@test.com` | `admin123` |
| `user@test.com` | `user123` |

> **First time?** Create an account on the signup page, then browse agents and try purchasing one!

---

## 📚 Common Workflows

### 🔍 Browse & Discover Agents
1. **Login** with your credentials
2. **View agents** in the main dashboard
3. **Click on agent** to see details, capabilities, and pricing
4. **Check status** to see if agent is available

### 🛒 Purchase Agent Access
1. **Click "Purchase"** button on any agent
2. **Confirm transaction** in the modal
3. **Receive access token** immediately (displays in UI)
4. **Copy API URL** for programmatic access
5. **Use token** to make unlimited API calls

### 💬 Send Agent-to-Agent Messages
1. **Open A2A Panel** from the sidebar
2. **Select source agent** (sender)
3. **Select destination agent** (receiver)
4. **Enter JSON message** payload
5. **View response** and message history

### 📊 Monitor Activity
1. **Click Logs Panel** to view all events
2. **Filter by type**: authentication, purchases, messages
3. **Review timestamps** and details
4. **Export logs** for analysis

---

## 🔌 API Endpoints

### Authentication
```
POST   /auth/register          Create new account
POST   /auth/login             Get JWT access token
GET    /auth/profile           Retrieve user profile
```

### Agents
```
GET    /agents                 List all available agents
GET    /agents/{id}            Get agent details
POST   /agents/{id}/purchase   Purchase agent access
GET    /agents/{id}/access-details  Retrieve purchase token
```

### Agent-to-Agent Messaging
```
POST   /a2a/send               Send message to another agent
GET    /a2a/messages           Retrieve message history
```

### Activity Logs
```
GET    /logs                   Get all event logs
GET    /logs/events            Get filtered events
DELETE /logs                   Clear logs (admin only)
```

### Health & Status
```
GET    /health                 API health check
GET    /                       API root endpoint
```

**Full documentation** with request/response examples: [API_REFERENCE.md](API_REFERENCE.md)

---

## 🔒 Security

- ✅ **Passwords**: Hashed with bcrypt (cost factor 10)
- ✅ **Tokens**: JWT with HS256, 24-hour expiry
- ✅ **CORS**: Restricted to authorized frontend domains
- ✅ **Auth**: All endpoints except `/health` require JWT
- ✅ **Logging**: Sensitive data (tokens, passwords) redacted
- ✅ **Headers**: Security headers on all responses
- ✅ **SSL/HTTPS**: Use in production (see deployment guide)

For detailed security guidelines, see [SECURITY.md](SECURITY.md).

> ⚠️ **Production checklist**: Use PostgreSQL, enable HTTPS, use strong secret keys, enable rate limiting

---

## 📖 Documentation

Quick reference for all guides:

| Document | Purpose |
|----------|---------|
| [SETUP_GUIDE.md](SETUP_GUIDE.md) | Local development setup |
| [DEPLOYMENT.md](DEPLOYMENT.md) | Production deployment on EC2/Nginx |
| [API_REFERENCE.md](API_REFERENCE.md) | Complete API documentation |
| [ARCHITECTURE.md](ARCHITECTURE.md) | System design and data flows |
| [SECURITY.md](SECURITY.md) | Security best practices |
| [TESTING.md](TESTING.md) | Testing and CI/CD procedures |
| [TROUBLESHOOTING.md](TROUBLESHOOTING.md) | Common issues and fixes |
| [PERFORMANCE.md](PERFORMANCE.md) | Optimization and scaling |
| [FAQ.md](FAQ.md) | Frequently asked questions |

---

## 🚢 Deployment

### Local Development
```bash
# See SETUP_GUIDE.md for detailed instructions
npm start           # Frontend (port 3000)
python main.py      # Backend (port 8000)
```

### Production (EC2 + Nginx)
See [DEPLOYMENT.md](DEPLOYMENT.md) for complete guide including:
- Server setup and configuration
- PostgreSQL database migration
- SSL/HTTPS with Let's Encrypt
- Systemd service management
- Monitoring and logging

---

## 🧪 Testing & CI/CD

Run tests locally:

```bash
# Backend tests
cd backend && pytest

# Frontend tests  
cd frontend && npm test

# Full coverage
pytest --cov=. --cov-report=html
```

Continuous integration via GitHub Actions on every push. See [TESTING.md](TESTING.md) for details.

---

## 🗺️ Roadmap

Current version: **v1.0** (May 2026)

### Phase 2: Scale & Performance (Q3 2026)
- [ ] PostgreSQL migration
- [ ] Redis caching layer
- [ ] Database indexing optimization

### Phase 3: Enterprise Auth (Q4 2026)
- [ ] Social login (Google, GitHub, LinkedIn)
- [ ] Two-factor authentication (2FA)
- [ ] GDPR compliance

### Phase 4: Real-Time Features (Q1 2027)
- [ ] WebSocket support for live messaging
- [ ] User dashboard and recommendations
- [ ] Push notifications

### Phase 5: Monetization (Q2 2027)
- [ ] Stripe integration
- [ ] Admin analytics dashboard
- [ ] Agent creator tools

### Phase 6: Enterprise Scale (Q3-Q4 2027)
- [ ] Multi-workspace support
- [ ] Team collaboration features
- [ ] Kubernetes deployment

Full roadmap: [ROADMAP.md](ROADMAP.md)

---

## 🤝 Contributing

We welcome contributions! Here's how to get involved:

1. **Fork** the repository
2. **Create feature branch**: `git checkout -b feature/amazing-feature`
3. **Commit changes**: `git commit -m 'Add amazing feature'`
4. **Push to branch**: `git push origin feature/amazing-feature`
5. **Open pull request** with description

For detailed guidelines, see [CONTRIBUTING.md](CONTRIBUTING.md).

---

## 📝 License

This project is licensed under the **MIT License** - see [LICENSE](LICENSE) for details.

You're free to use this for commercial projects, modify it, and distribute it as long as you include the original license.

---

## 💬 Support & Community

- **Issues**: Report bugs or request features on [GitHub Issues](https://github.com/TIRTHANATH20/Agent-Marketplace/issues)
- **Discussions**: Join community conversations on [GitHub Discussions](https://github.com/TIRTHANATH20/Agent-Marketplace/discussions)
- **Email**: Contact via [GitHub profile](https://github.com/TIRTHANATH20)

---

<div align="center">

### Made with ❤️ by [TIRTHANATH20](https://github.com/TIRTHANATH20)

**Give us a ⭐ if this project helped you!**

[![GitHub Stars](https://img.shields.io/github/stars/TIRTHANATH20/Agent-Marketplace?style=social)](https://github.com/TIRTHANATH20/Agent-Marketplace)

</div>
