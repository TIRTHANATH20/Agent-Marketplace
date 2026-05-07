# Agent Marketplace Setup Guide

## Quick Start (Local Development)

### Prerequisites
- Python 3.9+
- Node.js 16+
- SQLite3
- Git

### Backend Setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your settings

# Run migrations & start server
python main.py
```

Backend runs on `http://localhost:8000`

### Frontend Setup

```bash
cd frontend
npm install

# Configure API endpoint
echo "REACT_APP_API_BASE_URL=http://localhost:8000" > .env

npm start
```

Frontend runs on `http://localhost:3000`

## API Documentation

### Key Endpoints

**Agents**
- `GET /agents` - List all agents
- `GET /agents/{id}` - Get agent details
- `POST /agents/{id}/purchase` - Purchase agent access

**Authentication**
- `POST /auth/register` - Create account
- `POST /auth/login` - Get JWT token
- `GET /auth/profile` - Get current user

**A2A Messaging**
- `GET /a2a/messages` - Fetch messages
- `POST /a2a/send` - Send agent-to-agent message

### Authentication Header

All protected endpoints require:
```
Authorization: Bearer <jwt_token>
```

## Database Schema

Key tables:
- `users` - User accounts
- `agents` - AI agent definitions
- `purchases` - Purchase records with tokens
- `messages` - A2A message history
- `event_logs` - System event tracking

## Deployment

See [DEPLOYMENT.md](DEPLOYMENT.md) for EC2/Nginx setup.

## Troubleshooting

**CORS errors?** → Update `FRONTEND_URL` in backend `.env`
**Token not showing?** → Clear browser cache, refresh page
**Database locked?** → Ensure only one backend instance running

## Contributing

Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.
