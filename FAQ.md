# Frequently Asked Questions

## General

**Q: What is Agent Marketplace?**
A: A full-stack application for discovering, purchasing, and managing AI agents. Features include user authentication, agent browsing, purchase management, and agent-to-agent messaging (A2A).

**Q: Is it open source?**
A: Yes! Licensed under MIT. Feel free to fork, modify, and deploy your own instance.

**Q: Can I self-host it?**
A: Absolutely. See SETUP_GUIDE.md for local development and DEPLOYMENT.md for production.

---

## Installation & Setup

**Q: What are the system requirements?**
A: 
- Python 3.9+
- Node.js 16+
- 512MB RAM minimum
- SQLite (built-in) or PostgreSQL for production

**Q: How do I set up the development environment?**
A: Follow SETUP_GUIDE.md. Takes ~5 minutes.

**Q: Do I need Docker?**
A: No, but it's recommended for production. (Docker support coming soon)

---

## Authentication

**Q: How secure are passwords?**
A: Passwords are hashed with bcrypt (cost factor 10). Never stored in plain text. Admin can't even see passwords.

**Q: How long do JWT tokens last?**
A: 24 hours. After expiry, user must log in again. Refresh tokens not yet implemented.

**Q: Can I integrate with social login (Google, GitHub)?**
A: Not yet, but it's on the roadmap. Currently supports email/password only.

**Q: What if I forget my password?**
A: Password reset not yet implemented. For now, admin must reset via database.

---

## Agents & Purchases

**Q: What happens after I purchase an agent?**
A: You get:
1. Purchase access token (JWT)
2. API endpoint URL for that agent
3. Immediate access (token displays in UI)

**Q: How long is access valid?**
A: Currently: Forever (no expiry). Future versions will add time-based subscriptions.

**Q: Can I transfer access to another user?**
A: No, each purchase is tied to one user account.

**Q: What if I can't see my purchase token?**
A: Make sure you have latest frontend code. Try clearing browser cache and refreshing.

---

## Technical

**Q: What database does it use?**
A: SQLite for development. PostgreSQL recommended for production (> 100 users).

**Q: Is the API RESTful?**
A: Yes. OpenAPI docs at `/docs` (Swagger UI).

**Q: Can I use this as a library?**
A: Not yet. Currently designed as a complete application. Extracting into packages is on the roadmap.

**Q: Does it support real-time updates?**
A: No WebSockets yet. Uses HTTP polling. Real-time is on the roadmap.

---

## Deployment

**Q: How do I deploy to production?**
A: See DEPLOYMENT.md. We support EC2 + Nginx. AWS AppRunner, Heroku, and Vercel guides coming soon.

**Q: How much does hosting cost?**
A: 
- EC2 t3.micro: $8-15/month
- Database backup: $1-5/month
- Domain: $10-15/year
- Total: ~$15-25/month for 1000 users

**Q: Can I use a different hosting provider?**
A: Yes! Works on any provider with Python + Node support (Heroku, DigitalOcean, AWS, etc.)

**Q: Do I need SSL/HTTPS?**
A: Yes, highly recommended. Use Let's Encrypt (free).

---

## Performance & Scaling

**Q: How many users can this handle?**
A: 
- SQLite: ~100 concurrent users
- PostgreSQL: 1000+ concurrent users
- With Kubernetes: 100,000+

**Q: How do I optimize for more users?**
A: See PERFORMANCE.md. Recommended: migrate to PostgreSQL, add Redis caching, use load balancer.

**Q: What's the response time?**
A: ~100-200ms on modern hardware. See PERFORMANCE.md for benchmarks.

---

## Security

**Q: Is my password stored securely?**
A: Yes, bcrypt with cost factor 10. Industry standard.

**Q: Can admins see passwords?**
A: No. Passwords are hashed one-way. Even admin can't recover them.

**Q: Are API calls encrypted?**
A: Use HTTPS in production (TLS 1.2+). All HTTP headers/data encrypted in transit.

**Q: What about data privacy?**
A: Data stored in your database. No third-party tracking. GDPR compliance work in progress.

**Q: What if there's a security vulnerability?**
A: Please report to security@marketplace.local (not implemented yet). Don't post publicly.

---

## Troubleshooting

**Q: Backend won't start - "Address already in use"**
A: Another process using port 8000. Kill it: `lsof -i :8000 | kill -9 <PID>`

**Q: Frontend shows blank page**
A: Check browser console (F12) for errors. Ensure `.env` has correct `REACT_APP_API_BASE_URL`.

**Q: CORS errors in network tab**
A: Backend CORS not configured. Check backend `.env` has frontend URL.

**Q: Database locked error**
A: Multiple processes writing to SQLite. Ensure only one backend running.

**Q: Can't log in - "Invalid credentials"**
A: Make sure user registered first. Check email spelling.

More troubleshooting in TROUBLESHOOTING.md.

---

## Development

**Q: How do I contribute?**
A: See CONTRIBUTING.md. Fork → branch → commit → pull request.

**Q: What's the code style?**
A: Backend: PEP 8 (Black formatter). Frontend: Prettier.

**Q: Are there tests?**
A: Yes. Run `pytest` (backend) and `npm test` (frontend).

**Q: How do I run tests?**
A: See TESTING.md for full guide.

---

## Future Features

**Q: What's on the roadmap?**
A: 
- [ ] Docker support
- [ ] Social login (Google, GitHub)
- [ ] Real-time messaging (WebSockets)
- [ ] Subscription-based pricing
- [ ] Admin dashboard
- [ ] API rate limiting
- [ ] Elasticsearch integration
- [ ] Kubernetes deployment

**Q: When will feature X be added?**
A: Check CHANGELOG.md and GitHub Issues. No fixed timeline.

**Q: Can I request a feature?**
A: Yes! Open a GitHub Issue. Community PRs welcome.

---

## Support & Community

**Q: How do I get help?**
A: 
1. Check this FAQ
2. Search TROUBLESHOOTING.md
3. Check GitHub Issues
4. Email the maintainer

**Q: Is there a community?**
A: Not yet. Join GitHub Discussions (coming soon).

**Q: Can I use this for commercial purposes?**
A: Yes! MIT license allows commercial use.

**Q: Do I need to credit the project?**
A: Not required, but appreciated! Link to GitHub repo.

---

## License & Legal

**Q: What license is this under?**
A: MIT License. Very permissive. Do almost anything.

**Q: Can I sell access to my deployed version?**
A: Yes! MIT allows it. No royalties owed.

**Q: Do I have to open source my modifications?**
A: No. MIT is permissive. You can keep modifications private.

**Q: What about liability?**
A: No warranty. Use at your own risk. See LICENSE file.
