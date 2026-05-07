# Testing Guide

## Running Tests

### Backend Tests

```bash
cd backend
source venv/bin/activate

# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific test file
pytest test_auth.py

# Run specific test
pytest test_auth.py::test_login_success
```

### Frontend Tests

```bash
cd frontend

# Run tests
npm test

# Run with coverage
npm test -- --coverage

# Run in CI mode (no watch)
npm test -- --watchAll=false
```

## Test Structure

```
backend/
├── test_auth.py          # Authentication tests
├── test_agents.py        # Agent endpoints
├── test_purchases.py     # Purchase flow
└── test_a2a.py          # A2A messaging

frontend/
├── src/components/__tests__/
│   ├── AgentModal.test.js
│   ├── AuthModal.test.js
│   └── AgentGrid.test.js
└── src/__tests__/
    └── App.test.js
```

## Key Test Scenarios

### Authentication
- ✅ User registration with valid email/password
- ✅ Login with correct credentials
- ✅ Login fails with wrong password
- ✅ Duplicate email registration fails
- ✅ JWT token validation
- ✅ Token expiry handling

### Agents
- ✅ List agents returns all available agents
- ✅ Get agent details shows correct info
- ✅ Purchase creates purchase record
- ✅ Purchase token is generated correctly
- ✅ Access details show for purchased agents only

### A2A Messaging
- ✅ Send message creates record
- ✅ Get messages retrieves all messages
- ✅ Metadata is stored correctly
- ✅ Timestamp is recorded

### Frontend UI
- ✅ AgentModal shows token after purchase
- ✅ AuthModal handles login/register toggle
- ✅ AgentGrid displays all agents
- ✅ Error messages display on failure

## Performance Testing

```bash
# Load testing with locust
pip install locust
locust -f locustfile.py --host=http://localhost:8000

# Check response times
ab -n 100 -c 10 http://localhost:8000/agents
```

## Integration Testing Checklist

- [ ] User can register → login → view agents → purchase agent
- [ ] User receives access token immediately after purchase
- [ ] User cannot access agent without purchase
- [ ] Logout clears JWT token
- [ ] A2A messaging between agents works
- [ ] Database persists across backend restarts
- [ ] Nginx reverse proxy correctly routes requests
- [ ] CORS allows frontend domain

## Continuous Integration

GitHub Actions runs tests on every push:
- Python tests (pytest)
- Frontend tests (Jest)
- Lint checks (flake8, eslint)
- Coverage reports
