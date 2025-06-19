# DEVELOPER_HANDOFF_GUIDE.md
SWARM ‑ Multi-Agent AI Platform  
Developer Handoff • v2.0.0 • June 2025  

---

## 1. Current State Overview
| Area | Status |
|------|--------|
| Real-time multi-agent chat | ✅ (OpenRouter API, WebSocket) |
| Multi-agent collaboration endpoint | ✅ Sequential & parallel, exec-summary |
| Database persistence | ✅ PostgreSQL + Redis cache |
| Email → Task pipeline | ✅ Mailgun inbound → parser → agents |
| Plugin hot-reload system | ✅ `core/plugins` |
| Advanced UI | ✅ Progress dashboard, workflow viz |
| Audit trail (API) | ✅ CSV/PDF export; DB persistence |
| Deployment artifacts | ✅ Dockerfile, `production_setup.sh`, `app_production.py` |

**Works End-to-End:**  
Email → Task → Multi-agent workflow → Audit → UI dashboards.

---

## 2. Architecture Summary
```
Mailgun Webhook
        │
        ▼
Email Parser  ──▶  Collaboration Orchestrator ─────────┐
        │                                   ▲         │
        ▼                                   │         │
Task DB (Postgres)                          │         │
        │                                   │         │
        ▼                                   │         │
Celery Workers (Redis)   ◀─── Agents (OpenRouter) ─────┘
        │                                   │
        ▼                                   │
Audit Logger ──▶ Audit DB ──▶ Audit API ──▶ UI Dashboards
```
Components:
1. **Flask API Layer** – REST + Socket.IO (gevent)
2. **Celery Worker Pool** – async heavy tasks
3. **Agents** – call OpenRouter models (model per agent)
4. **Task/Audit Storage** – PostgreSQL via SQLAlchemy
5. **Cache / Sessions** – Redis
6. **Static SPA** – Vanilla JS + Tailwind

---

## 3. Codebase Navigation
```
mcp_new_project/
│
├─ app_production.py        # WSGI entry (Prod)
├─ scripts/
│   ├─ start_with_api.py    # Dev server (in-memory)
│   └─ start_with_db_api.py # Dev server (DB)
│
├─ models/
│   ├─ core.py              # shared SQLA base
│   └─ task_storage.py      # CollaborationTask, ConversationHistory, AuditLog
│
├─ services/
│   ├─ orchestrator.py      # multi-agent workflow logic
│   ├─ db_task_storage.py   # DB storage adapter
│   ├─ email_agent_integration.py
│   └─ redis_cache_manager.py
│
├─ utils/
│   ├─ logging_config.py
│   ├─ websocket.py         # Socket.IO helpers
│   └─ file_io.py
│
├─ static/
│   ├─ index.html
│   ├─ css/, js/
│   └─ docs ui assets
│
├─ migrations/
│   ├─ *.sql                # schema
│   └─ run_migrations.py
└─ tests/
```

Entry points:  
`app_production.py` (Gunicorn) • `scripts/start_with_*` (local)

---

## 4. Development Environment Setup
```bash
# clone & create env
git clone https://github.com/your-org/swarm.git
cd swarm/mcp_new_project
pyenv install 3.11.9 && pyenv local 3.11.9
python -m venv venv && source venv/bin/activate
pip install -r config/requirements/requirements.txt

# env vars
cp config/.env.example config/.env
# add OPENROUTER_API_KEY / OPENAI_API_KEY etc.

# run postgres & redis (docker shortcut)
docker compose -f deployment/docker-compose.dev.yml up -d

# migrate & seed
python migrations/run_migrations.py

# start dev server (db + websockets)
python scripts/start_with_db_api.py
```
Navigate to `http://localhost:5006`.

---

## 5. Testing & QA
```bash
# unit + integration
pytest -q

# persistence tests
python tests/test_persistence.py

# load tests (Locust)
locust -f tests/test_load_scenarios.py
```
Coverage ~78 %.

---

## 6. Deployment Status
| Mode | Script / Tool | Status |
|------|---------------|--------|
| Docker Compose PoC | `docker-compose.dev.yml` | ✅ |
| Ubuntu 22.04 Script | `deployment/production_setup.sh` | ✅ |
| Gunicorn + gevent   | `app_production.py`      | ✅ |
| Kubernetes (Helm)   | _Roadmap Q3_             | ⏳ |

Prod command:
```bash
gunicorn -w 4 -k gevent -b 0.0.0.0:8000 app_production:app
```

---

## 7. Remaining Operational Polish
1. **SSL / HTTPS** – automate LetsEncrypt in setup script  
2. **Backup / DR** – nightly Postgres dumps + S3 sync  
3. **Sentry DSN** – add real key & environment variables  
4. **Scale Celery** – autoscale worker count in prod  
5. **Admin GUI** – simple React SPA for agents & plugins  
6. **K8s Helm Chart** – package for enterprise clusters  
7. **Role-based auth** – JWT scopes + refresh tokens  

---

## 8. Known Issues & Technical Debt
| Area | Issue | Impact |
|------|-------|--------|
| Exec-summary agent | Sometimes returns “need context” | cosmetic |
| WebSocket fallback | Long-poll if proxy drops ws | minor perf |
| Email attachments  | Not stored in DB yet | edge feature |
| Task cleanup | Old tasks >90 d not auto-purged | storage bloat |
| Tests | No mocking for external LLM errors | flaky on outage |

---

## 9. Monitoring & Observability
* **/health** – basic JSON  
* **/metrics** – Prometheus (Flask-Prom)  
* **Loguru** – JSON logs to file & stdout  
* **Sentry hooks** – configured, needs DSN  
* **Grafana** – docker-compose.monitoring.yml template

Missing: Alerts, DB metrics dashboards.

---

## 10. Next Development Priorities
1. **SSL & Ingress** – secure public deployment  
2. **Backup & DR automation**  
3. **Admin Panel** – manage agents, plugins, keys  
4. **Additional Integrations** – Slack, Calendar webhooks  
5. **K8s & Autoscaling** – enterprise customers  
6. **Advanced Audit UI** – filter, timeline, diff view  
7. **Security Pen-Test** – external vulnerability scan

---

### Contact
Lead Dev: Josh Copp — `@copp1723`  
Docs: `/docs/*` – for detailed API & architecture.
