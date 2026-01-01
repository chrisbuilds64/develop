# Security Guidelines - ChrisBuilds64

**Last Updated:** January 1, 2026
**Status:** Hobby Project (Not NIS2 Regulated)

---

## Current Threat Landscape

### Attack Statistics (api.chrisbuilds64.com)
- **Daily attack attempts:** ~500-600
- **Most common targets:** `.env` files, PHP admin panels, WordPress
- **Success rate:** 0% (all return 404)
- **Source:** Automated bots scanning the internet

**This is NORMAL for any public server.**

---

## What We Do RIGHT ✅

### 1. No Vulnerable Technologies
- ❌ No PHP (common vulnerability)
- ❌ No WordPress (40% of attacks target this)
- ❌ No `.env` files in production
- ✅ FastAPI (modern, secure Python framework)
- ✅ Docker containerization (isolation)

### 2. HTTPS Everywhere
- ✅ Let's Encrypt SSL certificate
- ✅ All traffic encrypted
- ✅ Auto-renewal configured

### 3. Minimal Attack Surface
- ✅ Only necessary ports open (80, 443)
- ✅ No admin panels
- ✅ No file upload endpoints (yet)
- ✅ Simple API with limited endpoints

### 4. Building in Public Safely
- ✅ No secrets in GitHub (all public code)
- ✅ Environment variables in Docker (not in code)
- ✅ NIS2 disclaimer (hobby project boundaries)

---

## Current Vulnerabilities (Low Priority)

### 1. No Rate Limiting
**Risk:** API could be overloaded with requests
**Impact:** Service degradation, not data breach
**Priority:** Medium
**Solution:** Add FastAPI rate limiting middleware

### 2. No Authentication (Yet)
**Risk:** Anyone can read/write videos
**Impact:** Data modification, not system compromise
**Priority:** Low (single user app)
**Solution:** Add auth when multi-user needed

### 3. No Request Logging to File
**Risk:** Attacks visible in Docker logs only
**Impact:** Limited forensics capability
**Priority:** Low
**Solution:** Add structured logging to file

### 4. No Intrusion Detection
**Risk:** Sophisticated attacks might go unnoticed
**Impact:** Unknown
**Priority:** Low (overkill for hobby project)
**Solution:** Consider fail2ban for SSH

---

## Security Roadmap

### Phase 1: Immediate (Next Week)
**Goal:** Harden basics without over-engineering

- [ ] Add rate limiting to FastAPI
- [ ] Configure fail2ban for SSH
- [ ] Enable UFW firewall (allow 80, 443, 22 only)
- [ ] Review nginx security headers
- [ ] Document backup strategy

### Phase 2: Before Multi-User (Month 1-2)
**Goal:** Prepare for beta testers

- [ ] Implement authentication (JWT or session-based)
- [ ] Add CORS configuration
- [ ] Input validation on all endpoints
- [ ] SQL injection prevention audit
- [ ] XSS prevention audit

### Phase 3: Before Public Launch (Month 3+)
**Goal:** Production-ready security

- [ ] Security audit by third party
- [ ] Penetration testing
- [ ] Logging & monitoring infrastructure
- [ ] Incident response plan
- [ ] Rate limiting per user
- [ ] GDPR compliance review

---

## Daily Attack Patterns (Observed)

### Common Bot Scanners
```
172.18.0.1  - nginx reverse proxy (internal)
64.227.*    - DigitalOcean IPs (bots)
Various     - Automated scanners
```

### Attack Types
1. **Config File Discovery** - 60% of attacks
   - `.env`, `config.json`, `settings.py`
   - All return 404 ✅

2. **Admin Panel Bruteforce** - 25% of attacks
   - `/admin`, `/wp-admin`, `/login`
   - No admin panels exist ✅

3. **PHP Exploits** - 10% of attacks
   - `phpinfo()`, `eval-stdin.php`
   - No PHP on server ✅

4. **Other** - 5%
   - Random paths, known CVEs
   - Not applicable ✅

---

## What NOT to Worry About (Yet)

### ❌ Over-Engineering Security
- Don't add Web Application Firewall (WAF) for single-user app
- Don't implement complex audit logging for hobby project
- Don't pay for security scanning services (manual audit sufficient)

### ❌ Obsessing Over Failed Attacks
- 500 failed attacks/day is NORMAL
- As long as they return 404, no harm done
- It's just noise from internet background radiation

### ❌ Hiding Everything
- Building in Public means transparency
- Code is public, infrastructure is documented
- This is a feature, not a bug
- Just keep secrets OUT of code (done ✅)

---

## Building in Public Security Model

### Public (GitHub)
- ✅ All source code
- ✅ Architecture decisions
- ✅ Deployment scripts (generic)
- ✅ This security documentation

### Private (Never in GitHub)
- ❌ Environment variables (.env)
- ❌ API keys
- ❌ Database credentials
- ❌ SSL private keys
- ❌ User data

### Server-Only
- Docker environment variables
- Let's Encrypt certificates
- SQLite database file
- nginx configurations (with secrets)

---

## Incident Response Plan

### If Server is Compromised
1. **Immediate:** Stop Docker container
2. **Isolate:** Disconnect from network
3. **Assess:** Check logs for breach extent
4. **Rebuild:** Fresh server from GitHub
5. **Document:** Write post-mortem (Building in Public!)

### If Code Vulnerability Found
1. **Fix:** Patch immediately
2. **Deploy:** Push to production
3. **Notify:** Blog post about issue & fix
4. **Learn:** Update this document

### If Credentials Leaked
1. **Rotate:** All affected credentials
2. **Audit:** Check for unauthorized access
3. **Update:** Deployment scripts
4. **Document:** Lesson learned

---

## Security Checklist (Monthly Review)

- [ ] Review Docker logs for unusual patterns
- [ ] Update all dependencies (`pip install --upgrade`)
- [ ] Check SSL certificate expiry (auto-renewal working?)
- [ ] Review new endpoints for security issues
- [ ] Rotate sensitive credentials (if any)
- [ ] Backup verification (can restore from backup?)
- [ ] Review this document for updates

---

## Resources

**FastAPI Security:**
- https://fastapi.tiangolo.com/tutorial/security/

**OWASP Top 10:**
- https://owasp.org/www-project-top-ten/

**Let's Encrypt:**
- https://letsencrypt.org/docs/

**Docker Security:**
- https://docs.docker.com/engine/security/

---

## Philosophy

**Security is a spectrum, not binary.**

For a hobby project with one user:
- ✅ HTTPS - Essential
- ✅ No secrets in code - Essential
- ✅ Basic firewall - Essential
- ⚠️ Rate limiting - Nice to have
- ⚠️ Authentication - When needed
- ❌ WAF - Overkill
- ❌ 24/7 monitoring - Overkill

**KISS applies to security too:**
- Secure the essentials
- Don't over-engineer
- Add complexity when needed
- Document everything

---

**Building in public since '64** 🚀

*Security through transparency, not obscurity.*
