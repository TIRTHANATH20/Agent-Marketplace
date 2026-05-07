# Security Guidelines

## Authentication Security

### Password Requirements
- Minimum 8 characters
- Stored as bcrypt hash (cost factor 10)
- Never log or expose passwords

### JWT Tokens
- Algorithm: HS256
- Secret key: 256-bit random (store in environment)
- Expiry: 24 hours
- Refresh tokens: Not yet implemented (TODO)

### Best Practices
- Always use HTTPS in production
- Rotate JWT secret annually
- Monitor failed login attempts
- Implement rate limiting on auth endpoints

## Database Security

### SQL Injection Protection
- All queries use SQLAlchemy ORM (parameterized)
- Never concatenate user input into queries
- Use prepared statements for direct SQL

### Data Validation
- Email validation: RFC 5322 compliant
- Password: Length and type checking
- Agent data: Whitelist allowed fields

## API Security

### CORS Configuration
```python
allow_origins = [os.getenv("FRONTEND_URL")]  # Restrict to authorized domains
allow_credentials = True
allow_methods = ["GET", "POST", "PUT", "DELETE"]
allow_headers = ["Content-Type", "Authorization"]
```

### Rate Limiting
- Auth endpoints: 5 requests/minute per IP
- General endpoints: 100 requests/minute per user
- Use Redis + Slow-Down library

### Input Validation
```python
# Schema validation for all inputs
class PurchaseRequest(BaseModel):
    agent_id: int = Field(..., gt=0)
    # Only positive integers accepted
```

## Logging & Monitoring

### Sensitive Data Redaction
```python
def redact_sensitive(data):
    """Remove tokens, passwords from logs"""
    if 'token' in data:
        data['token'] = '***'
    if 'password' in data:
        data['password'] = '***'
    return data
```

### Audit Trail
- All purchases logged with timestamp
- User actions tracked (login, agent access)
- Failed attempts logged
- Admin can review event_logs table

## Infrastructure Security

### Server Hardening
- SSH key-only authentication (no passwords)
- Firewall: Only ports 80, 443, 22 open
- Disable unnecessary services
- Regular security updates

### Database Backups
```bash
# Daily automated backup
sqlite3 marketplace.db ".backup 'backup_$(date +%Y%m%d).db'"
```

### Secrets Management
- JWT secret: Environment variable (never in code)
- API keys: Stored securely, rotated quarterly
- Database credentials: Separate .env file (gitignored)

## Compliance

### GDPR Compliance
- User can request data export
- User can request account deletion (TODO)
- Privacy policy required
- Cookie consent banner required (TODO)

### Payment Security (if implemented)
- Use Stripe/PayPal (PCI compliance)
- Never store card numbers
- Use tokens instead of raw data

## Vulnerability Management

### Regular Scanning
```bash
# Check for vulnerable dependencies
pip check
npm audit

# Security linting
bandit -r backend/
```

### Incident Response
1. Identify breach
2. Isolate affected systems
3. Notify users if data exposed
4. Fix root cause
5. Document in security log
6. Update security procedures

## Testing Security

```python
# Example: Test password hashing
def test_password_hashing():
    plain = "test123"
    hashed = hash_password(plain)
    assert hashed != plain
    assert verify_password(plain, hashed)
    assert not verify_password("wrong", hashed)

# Example: Test CORS
def test_cors_headers():
    response = client.get("/agents")
    assert "Access-Control-Allow-Origin" in response.headers
```

## Resources

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [JWT Best Practices](https://tools.ietf.org/html/rfc8949)
- [SQLAlchemy Security](https://docs.sqlalchemy.org/en/14/faq/security.html)
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)
