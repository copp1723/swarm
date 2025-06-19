# SWARM Production Deployment Guide

This guide walks you from a blank cloud server to a live, production-grade SWARM installation capable of running full multi-agent collaborations.

---

## 1. Prerequisites
### 1.1 Server
| Requirement | Recommended |
|-------------|-------------|
| OS          | Ubuntu 22.04 LTS |
| CPU         | 2 vCPU (4 vCPU for heavy workloads) |
| RAM         | 4 GB minimum |
| Disk        | 50 GB SSD |
| Public IP   | Static |

### 1.2 Domain
* Register your domain (e.g. `swarm.example.com`).
* Create an **A** record pointing to the server’s public IP **before** running the setup script (LetsEncrypt verification).

### 1.3 API Keys & Secrets
Have the following ready:
* `OPENROUTER_API_KEY`, `OPENAI_API_KEY`, etc.
* `MAILGUN_API_KEY`, `MAILGUN_DOMAIN`, `MAILGUN_SIGNING_KEY`.
* `SUPERMEMORY_API_KEY` (optional but recommended).
* `SENTRY_DSN` (optional error tracking).

---

## 2. Quick Start

> All commands assume you are **root** or using `sudo`.

### Step 1 – Provision the server
```bash
# DigitalOcean example
doctl compute droplet create swarm \
  --image ubuntu-22-04-x64 \
  --size s-2vcpu-4gb \
  --region nyc1 \
  --ssh-keys <your-ssh-key-id>
```

### Step 2 – Point DNS
Add an **A** record:  
`swarm.example.com → <server-IP>`

### Step 3 – Run the setup script
```bash
scp deployment/production_setup.sh root@<server>:/root/
ssh root@<server>
chmod +x production_setup.sh
./production_setup.sh swarm.example.com you@example.com
```
What it does:
1. Updates OS & installs Python 3.11, Node 18, Redis, PostgreSQL, Nginx.
2. Creates `swarm` user, directories, virtual-env.
3. Sets up Gunicorn + Celery systemd services.
4. Generates Nginx site and optional LetsEncrypt SSL.
5. Produces `/home/swarm/swarm/.env.production` template.

### Step 4 – Deploy SWARM code
```bash
ssh swarm@<server>
cd ~/swarm
git clone https://github.com/<your-org>/swarm.git .
source ~/venv/bin/activate
pip install -r requirements.txt
```

### Step 5 – Configure services
Edit `.env.production` with real secrets.  
Run initial DB migration:
```bash
python init/init_database.py
```
Enable & start services:
```bash
sudo systemctl enable swarm swarm-celery swarm-celery-beat
sudo systemctl start swarm swarm-celery swarm-celery-beat
```

### Step 6 – Smoke-test multi-agent functionality
```bash
curl https://swarm.example.com/api/agents/list
# → should return 4 agents

curl -X POST https://swarm.example.com/api/agents/collaborate \
  -H "X-API-Key: <SWARM_API_KEY>" \
  -H "Content-Type: application/json" \
  -d '{"task_description":"Refactor login flow","tagged_agents":["coding_01","bug_01"]}'
```
Open the UI at `https://swarm.example.com` – you should see agents and live chat.

---

## 3. Production Checklist
| Area | ✅ Verify |
|------|-----------|
| **Secrets** | `.env.production` filled, permissions `600`, owned by `swarm` |
| **SSL** | LetsEncrypt certificate valid (`https://` green lock) |
| **Firewall** | `ufw status` → only 22, 80, 443 open |
| **Security Headers** | Check `/health` response for `Strict-Transport-Security`, `Content-Security-Policy` |
| **Log Rotation** | `cat /etc/logrotate.d/swarm` exists |
| **Backups** | DB dump cron or managed backup configured |
| **Monitoring** | `/health` returns `status":"healthy"`; Sentry receiving test error |
| **Performance** | `htop` shows memory < 70 % at idle |

---

## 4. Testing Multi-Agent Collaborations
### 4.1 Create Your First Collaboration
1. In the UI click **Multi-Agent Task**  
2. Enter task: “Implement dark-mode toggle site-wide”  
3. Tag agents `product_01`, `coding_01`, `bug_01`  
4. Observe real-time sidebar: each agent posts status updates.

### 4.2 Key API Endpoints
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/agents/list` | GET | list agents |
| `/api/agents/collaborate` | POST | start multi-agent task |
| `/api/agents/conversation/<task_id>` | GET | streaming task status |
| `/api/audit/task/<task_id>` | GET | audit trail |
| `/api/audit/task/<task_id>/export?format=csv` | GET | export |

### 4.3 Expected Behaviour
* Task status progresses from `queued → running → completed`.
* Each agent posts its actions in order.
* Audit dashboard shows timeline and allows CSV export.

### 4.4 Troubleshooting
| Symptom | Fix |
|---------|-----|
| `503 service unavailable` | `systemctl status swarm` – likely Gunicorn crashed |
| WebSocket disconnects | Check `ufw` & Nginx config allows `Upgrade` headers |
| Agents list empty | Verify `/api/agents/list` returns JSON; check `.env` keys |

---

## 5. Monitoring & Maintenance
### 5.1 Logs
```
sudo journalctl -u swarm -f          # Gunicorn
sudo journalctl -u swarm-celery -f   # Celery worker
tail -f /home/swarm/logs/swarm.log   # App log (Loguru)
```

### 5.2 Health & Performance
* `https://swarm.example.com/health` – JSON health summary
* Enable Sentry DSN for error tracking
* Optional: ship logs to ELK/Loki/Datadog

### 5.3 Backups
```bash
# Daily PostgreSQL dump
0 2 * * * postgres pg_dump swarm_db | gzip > /var/backups/swarm_$(date +\%F).sql.gz
```
Store dumps in off-site object storage (S3, Backblaze).

### 5.4 Updating
```bash
ssh swarm@<server>
cd ~/swarm
git pull
source ~/venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart swarm swarm-celery swarm-celery-beat
```

### 5.5 Scaling
* **Vertical**: Upgrade droplet size (CPU/RAM).
* **Horizontal**:  
  * Add more Celery workers (`swarm-celery@2.service`, etc.)  
  * Use load-balanced Gunicorn behind Nginx on separate nodes.

---

**You’re ready!**  
Spin up your server, follow the quick-start, and run real multi-agent collaborations in production.  
For questions or issues open a GitHub issue or contact the SWARM maintainers.
