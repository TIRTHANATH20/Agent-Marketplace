# Troubleshooting Guide

## Common Issues & Solutions

### Backend Won't Start

**Error**: `ModuleNotFoundError: No module named 'fastapi'`

**Solution**:
```bash
cd backend
source venv/bin/activate
pip install -r requirements.txt
python main.py
```

**Error**: `Address already in use: ('0.0.0.0', 8000)`

**Solution**:
```bash
# Find process using port 8000
lsof -i :8000

# Kill the process
kill -9 <PID>

# Or use different port
python main.py --port 8001
```

---

### JWT Token Not Displaying After Purchase

**Issue**: User purchases agent but token doesn't show

**Solution**: 
- This was fixed in recent update — AgentModal now populates token immediately
- Ensure frontend is running latest version
- Clear browser cache and refresh
- Check browser console for errors (F12)

**Debug Steps**:
```javascript
// In browser console
localStorage.getItem('jwt_token')  // Should contain token
fetch('/agents/1/purchase', {
  headers: {'Authorization': 'Bearer ' + localStorage.getItem('jwt_token')}
})
```

---

### CORS Errors in Frontend

**Error**: `Access to XMLHttpRequest blocked by CORS policy`

**Solution**: Check backend CORS config:
```python
# backend/main.py
origins = [
    "http://localhost:3000",
    "https://your-domain.com"
]
```

**Debug**:
```bash
# Check CORS headers in response
curl -i http://localhost:8000/agents
# Should include: Access-Control-Allow-Origin: *
```

---

### Database Locked Error

**Error**: `database is locked`

**Cause**: Multiple processes writing to SQLite simultaneously

**Solution**:
```bash
# Ensure only one backend running
ps aux | grep python

# Check SQLite lock file
ls -la marketplace.db*

# Restart backend
pkill -f "python main.py"
python main.py
```

**For Production**: Migrate to PostgreSQL

---

### Frontend Shows Blank Page

**Issue**: React app doesn't load

**Solution**:
```bash
cd frontend
npm install
npm start  # Should open http://localhost:3000

# Check if built correctly
npm run build
# Check build/index.html exists
```

**Debug**:
- Open DevTools (F12)
- Check Console tab for errors
- Check Network tab for failed requests
- Verify `REACT_APP_API_BASE_URL` environment variable

---

### Login Fails with Invalid Credentials

**Debug Steps**:
```bash
# 1. Check user exists in database
sqlite3 marketplace.db "SELECT * FROM users;"

# 2. Test login endpoint directly
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"test123"}'

# 3. Check error response
# Should show specific error (user not found vs wrong password)
```

**Common Causes**:
- User never registered
- Email spelled wrong
- Password changed
- Database not initialized

---

### Slow API Responses

**Investigate**:
```bash
# Check backend logs
tail -f backend.log

# Profile with timing
curl -w "@curl-format.txt" -o /dev/null http://localhost:8000/agents

# Monitor system resources
top  # CPU/Memory usage
```

**Solutions**:
- Add database indexes: `CREATE INDEX idx_agent_id ON purchases(agent_id);`
- Enable response caching for `/agents` endpoint
- Upgrade SQLite to PostgreSQL
- Add Redis cache layer

---

### SSL Certificate Errors (HTTPS)

**Error**: `ERR_CERT_AUTHORITY_INVALID`

**Solution**:
```bash
# Renew Let's Encrypt certificate
sudo certbot renew

# Or get new certificate
sudo certbot --nginx -d your-domain.com
```

**Verify Certificate**:
```bash
openssl s_client -connect your-domain.com:443 -showcerts
```

---

### A2A Messaging Not Working

**Issue**: Messages not being sent/received

**Debug**:
```bash
# Check messages table
sqlite3 marketplace.db "SELECT * FROM messages;"

# Test endpoint
curl -X POST http://localhost:8000/a2a/send \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"from_agent_id":1,"to_agent_id":2,"message":"test"}'
```

**Common Issues**:
- Agent IDs don't exist
- User not authenticated
- Message text too long
- Database connection issue

---

### File Not Found Errors

**Error**: `FileNotFoundError: marketplace.db`

**Solution**: Database initializes on first run
```bash
# If not created automatically
sqlite3 marketplace.db < schema.sql
python main.py  # Will initialize
```

---

## Getting Help

1. **Check logs**: `tail -f backend.log`, DevTools Console
2. **Search docs**: Check SETUP_GUIDE.md, API_REFERENCE.md
3. **Test endpoints**: Use curl or Postman
4. **GitHub Issues**: Search existing issues
5. **Ask for help**: Provide error message + steps to reproduce

## Debug Mode

Enable verbose logging:
```bash
# Backend
export LOG_LEVEL=DEBUG
python main.py

# Frontend
REACT_APP_DEBUG=true npm start
```

## Performance Baseline

Expected response times:
- GET /agents: < 100ms
- POST /auth/login: < 200ms (due to bcrypt)
- POST /agents/{id}/purchase: < 300ms
- GET /a2a/messages: < 150ms

If slower, investigate database or network issues.
