# SWARM Infrastructure Improvements  
_Applies to `mcp_new_project` (June 2025)_

> This document records all **platform-level improvements** applied during the June 2025 hardening sprint.  
> The goals were security, portability, repeatable deployments, and developer ergonomics.

---

## 1. Secrets Management

| Problem | Fix |
|---------|-----|
| API keys & passwords committed in plaintext (e.g. `docs/API_KEY.txt`, hard-coded constants) | • **Created `.env.example`** – canonical template without real values.<br>• Added secrets‐safe loader via _python-dotenv_.<br>• `.gitignore` expanded: `*.env` files are now ignored by default.<br>• **Rotated** all exposed keys; committed tokens are now invalid. |

**How to use**

```bash
# one-time
cp mcp_new_project/.env.example mcp_new_project/.env
# 👉 fill in real values

# runtime (scripts read automatically)
export $(grep -v '^#' mcp_new_project/.env | xargs)
```

---

## 2. Configurable File-System Paths

| Problem | Fix |
|---------|-----|
| Absolute desktop paths (`/Users/copp1723/Desktop`) baked into code & MCP config | • Introduced `MCP_FILESYSTEM_ROOT` env variable.<br>• `services/filesystem_tools.py` now resolves every path relative to that root, with safe validation.<br>• `mcp_config.json` uses `${MCP_FILESYSTEM_ROOT}` placeholders. |

**Defaults**

```env
MCP_FILESYSTEM_ROOT=/app              # inside container / server
MCP_FILESYSTEM_ALLOWED_DIRS=/app
```

---

## 3. Database Migration Strategy (Alembic)

| Item | Details |
|------|---------|
| Tooling | Integrated **Alembic 1.13**; configuration lives in `migrations/alembic/`. |
| Bootstrap | `scripts/run-migrations.sh init` stamps an existing DB at `head`. |
| Work-flow | `revision --autogenerate`, review, `upgrade head` in CI / CD. |
| Docs | See `migrations/alembic/README.md` for full CLI cheatsheet. |

> Existing raw `.sql` files remain for history but **future schema changes must go through Alembic**.

---

## 4. Dependency Consolidation

| Before | After |
|--------|-------|
| Multiple scattered `requirements*.txt` with drift | • Single **`requirements.txt`** (prod) & **`requirements-dev.txt`** (dev/test).<br>• Vulnerabilities patched (`eventlet 0.35.2`, `openai 1.35.0`, etc.).<br>• Added **hash-pinned** versions for deterministic builds. |

**Install**

```bash
# production image / Render.com
pip install -r mcp_new_project/requirements.txt

# local dev
pip install -r mcp_new_project/requirements-dev.txt
```

---

## 5. Front-End Build Pipeline

| Feature | Implementation |
|---------|----------------|
| Tailwind CSS compilation | `tailwindcss` added as a devDependency. |
| Scripts | `npm run css:dev` (watch) & `npm run css:build` (minify). |
| Source / Output | Input: `static/src/styles.css` → Output: `static/css/styles.css`. |
| Purge/JIT | Configured in `tailwind.config.js` for minimal prod bundle. |

These steps are automatically called in the Render deploy hook; local developers run:

```bash
pnpm install      # or npm ci
npm run css:dev   # hot-reload
```

---

## 6. Production Service Management

### 6.1 Service-specific launchers (`scripts/services/`)

| Script | Purpose |
|--------|---------|
| `gunicorn_web.sh` | Flask app via Gunicorn + gevent. |
| `celery_worker.sh` | Celery workers (`agent_queue`, `analysis_queue`). |
| `celery_beat.sh` | Periodic scheduler. |
| `flower_monitor.sh` | Flower dashboard on port 5555. |

All scripts auto-load `.env`, create log directories, and support graceful shutdown via signals.

### 6.2 Unified Orchestrator

`scripts/run-services.sh` provides `start|stop|restart|status|logs` for any subset of services.

```bash
# Start full stack
./scripts/run-services.sh start

# Restart only workers
./scripts/run-services.sh restart worker

# View last 50 lines of web logs
./scripts/run-services.sh logs web
```

### 6.3 PID & Log Locations

```
mcp_new_project/
 ├─ run/      # *.pid files
 └─ logs/     # gunicorn_*.log, celery_*.log, flower_*.log
```

Logs are rotated externally (e.g., Render log retention or systemd).

---

## 7. Continuous Integration / Deployment Notes

1. **Migrations**  
   CI step: `scripts/run-migrations.sh upgrade head` (SQLite)  
   CD step (Render): same using PostgreSQL URL.

2. **Frontend assets**  
   Build hook runs `npm run css:build`.

3. **Services**  
   Render *web service* → executes `scripts/services/gunicorn_web.sh`.  
   Render *background worker* → executes `scripts/services/celery_worker.sh`.

---

## 8. Next Steps & Recommendations

| Priority | Action |
|----------|--------|
| P0 | Secrets vault integration (Render environment vars ok; long term ‑ HashiCorp Vault). |
| P1 | Containerise each service & use Docker Compose / Kubernetes for orchestration. |
| P1 | Enable Health / Readiness probes per service. |
| P2 | Add pre-commit that blocks secrets and enforces formatting (black, isort, flake8). |
| P2 | Automate Alembic autogenerate + PR review bot to detect dangerous ops. |

---

## 9. Changelog (infrastructure)

| Date | Author | Summary |
|------|--------|---------|
| 2025-06-20 | dev-infra team | Initial infrastructure overhaul (this document). |
| 2025-06-21 | Josh Copp | UI fixes & schema alignment (see `TYPESCRIPT_FIX_STATUS.md`). |

---

**SWARM is now production-hardened** with secure configuration, predictable builds, repeatable schema migrations, and scalable service management. 🚀
