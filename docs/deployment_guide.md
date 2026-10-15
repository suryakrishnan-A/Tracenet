# TraceNest Production Deployment Guide

This guide details the production deployment architecture for **TraceNest**, an AI-powered observability and incident investigation platform. It provides actionable, step-by-step instructions for containerized deployment, SSL/TLS reverse proxying, credential security, database persistence, and low-cost cloud hosting.

---

## 1. Production Architecture Overview

TraceNest uses a service-oriented, containerized architecture designed for high availability, least-privilege security, and low operational overhead.

```
                          Internet (HTTPS)
                                │
                                ▼
                   ┌─────────────────────────┐
                   │  Caddy / Nginx Proxy    │ (Automatic Let's Encrypt TLS)
                   │  Port 80 / 443          │
                   └────────────┬────────────┘
                                │
          ┌─────────────────────┴─────────────────────┐
          │                                           │
  Reverse Proxy (/)                          Reverse Proxy (/api/*)
          │                                           │
          ▼                                           ▼
┌───────────────────────────┐               ┌───────────────────────────┐
│ Next.js Frontend          │               │ FastAPI Backend           │
│ Standalone Node.js        │               │ Non-root user (tracenest) │
│ Port 3000                 │               │ Port 8000                 │
│ Health: /api/health       │               │ Health: /api/v1/health    │
└───────────────────────────┘               └─────────────┬─────────────┘
                                                          │
                                                    AsyncPG Pool (Port 5432)
                                                          │
                                                          ▼
                                            ┌───────────────────────────┐
                                            │ PostgreSQL 16 Persistent  │
                                            │ Named Volume: pgdata_prod │
                                            │ Healthcheck: pg_isready   │
                                            └───────────────────────────┘
```

### Security & Isolation Invariants
- **Dedicated Docker Network**: Frontend, Backend, and Database communicate on an internal bridge network (`tracenest-net`). PostgreSQL's port (`5432`) is **never exposed** to the public internet.
- **Non-Root Containers**: Backend runs under UID `10001:10001` (`tracenest`), Frontend runs under Next.js unprivileged user `nextjs:nodejs`.
- **Scoped Ingestion Credentials**: Public services transmit telemetry using scoped `tn_ingest_...` tokens. Even if an ingestion token is intercepted, it is strictly forbidden (`403 Forbidden`) from reading incidents or accessing administrative endpoints.
- **SHA-256 Hash Storage**: No raw credentials or API keys are ever stored plaintext in PostgreSQL.

---

## 2. Environment Configuration

Create a dedicated `.env.production` file on your production host. Never commit this file to source control.

```bash
# -------------------------------------------------------------------
# TraceNest Production Configuration (.env.production)
# -------------------------------------------------------------------

# Environment
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO

# PostgreSQL Configuration
POSTGRES_USER=tracenest_admin
POSTGRES_PASSWORD=generate_a_strong_random_password_here_min_32_chars
POSTGRES_DB=tracenest
POSTGRES_PORT=5432
DATABASE_URL=postgresql+asyncpg://tracenest_admin:generate_a_strong_random_password_here_min_32_chars@db:5432/tracenest

# Security & CORS (Replace with your actual production domain)
ALLOWED_ORIGINS=["https://tracenest.yourdomain.com"]
BACKEND_CORS_ORIGINS=["https://tracenest.yourdomain.com"]

# Rate Limiting (Sliding Window in-memory)
RATE_LIMIT_PER_MINUTE=120

# AI Incident Investigation (Gemini 1.5 Flash recommended)
GEMINI_API_KEY=your_production_google_gemini_api_key_here
AI_MODEL_NAME=gemini-1.5-flash
AI_TEMPERATURE=0.2

# Frontend Configuration
NEXT_PUBLIC_API_URL=https://tracenest.yourdomain.com
```

---

## 3. Production Docker Compose (`docker-compose.prod.yml`)

Save the following production composition file:

```yaml
version: "3.8"

services:
  db:
    image: postgres:16-alpine
    container_name: tracenest-db-prod
    restart: always
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
    volumes:
      - pgdata_prod:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - tracenest-net
    deploy:
      resources:
        limits:
          cpus: "1.0"
          memory: 1024M

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: tracenest-backend-prod
    restart: always
    depends_on:
      db:
        condition: service_healthy
    env_file:
      - .env.production
    networks:
      - tracenest-net
    healthcheck:
      test: ["CMD-SHELL", "curl -f http://localhost:8000/api/v1/health/liveness || exit 1"]
      interval: 15s
      timeout: 5s
      retries: 3
    deploy:
      resources:
        limits:
          cpus: "1.5"
          memory: 1024M

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    container_name: tracenest-frontend-prod
    restart: always
    depends_on:
      - backend
    environment:
      - NODE_ENV=production
      - PORT=3000
    networks:
      - tracenest-net
    healthcheck:
      test: ["CMD-SHELL", "wget --no-verbose --tries=1 --spider http://localhost:3000 || exit 1"]
      interval: 15s
      timeout: 5s
      retries: 3
    deploy:
      resources:
        limits:
          cpus: "1.0"
          memory: 512M

  caddy:
    image: caddy:2-alpine
    container_name: tracenest-caddy-proxy
    restart: always
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile:ro
      - caddy_data:/data
      - caddy_config:/config
    depends_on:
      - frontend
      - backend
    networks:
      - tracenest-net

volumes:
  pgdata_prod:
  caddy_data:
  caddy_config:

networks:
  tracenest-net:
    driver: bridge
```

---

## 4. Reverse Proxy & Automated HTTPS (Caddy)

Caddy automatically provisions and renews SSL/TLS certificates via Let's Encrypt without requiring manual certbot cron jobs.

Create `Caddyfile` in the project root:

```caddy
tracenest.yourdomain.com {
    # Compress responses
    encode zstd gzip

    # Security Headers
    header {
        X-Content-Type-Options "nosniff"
        X-Frame-Options "DENY"
        X-XSS-Protection "1; mode=block"
        Referrer-Policy "strict-origin-when-cross-origin"
        Strict-Transport-Security "max-age=31536000; includeSubDomains; preload"
    }

    # API and OpenAPI routes -> FastAPI Backend
    handle /api/* {
        reverse_proxy backend:8000 {
            header_up Host {host}
            header_up X-Real-IP {remote}
            header_up X-Forwarded-For {remote}
            header_up X-Forwarded-Proto {scheme}
        }
    }

    handle /docs* {
        reverse_proxy backend:8000
    }

    handle /openapi.json* {
        reverse_proxy backend:8000
    }

    # All other routes -> Next.js Frontend
    handle {
        reverse_proxy frontend:3000 {
            header_up Host {host}
            header_up X-Real-IP {remote}
            header_up X-Forwarded-For {remote}
            header_up X-Forwarded-Proto {scheme}
        }
    }
}
```

---

## 5. Deployment Step-by-Step Execution

### Step 1: Clone and Configure
```bash
git clone https://github.com/your-username/tracenest.git
cd tracenest
cp .env.example .env.production
nano .env.production  # Set production credentials and domain
```

### Step 2: Run Database Migrations
Before exposing traffic, run the reversible Alembic database migrations:
```bash
docker compose -f docker-compose.prod.yml run --rm backend \
  alembic upgrade head
```

### Step 3: Launch Services
```bash
docker compose -f docker-compose.prod.yml up -d --build
```

### Step 4: Verify Deployment Health
```bash
# Verify backend readiness
curl -i https://tracenest.yourdomain.com/api/v1/health/readiness

# Verify backend liveness
curl -i https://tracenest.yourdomain.com/api/v1/health/liveness

# Check container logs
docker compose -f docker-compose.prod.yml logs -f --tail=50
```

---

## 6. Cloud Platform Hosting Options & Cost Analysis

TraceNest is lightweight and can be hosted effectively on developer-friendly cloud infrastructure:

| Provider | Topology | Monthly Cost | Pros | Cons / Trade-offs |
| :--- | :--- | :--- | :--- | :--- |
| **Hetzner Cloud VPS (CX22)** | 2 vCPU, 4GB RAM, 40GB NVMe, Docker Compose | **~$4.00 / mo** | Maximum performance, full root control, persistent local storage, unmetered bandwidth. | Requires self-managing Docker and Linux security updates. |
| **DigitalOcean Droplet** | 1 vCPU, 2GB RAM, 50GB SSD, Docker Compose | **$12.00 / mo** | Global data centers, straightforward snapshot backups, 1-click Docker droplet. | Slightly higher pricing than Hetzner. |
| **Railway** | Managed Postgres + 2 Web Services (Node + Python) | **~$5.00 - $10.00 / mo** | Zero server management, native GitHub git-push deployments, managed PostgreSQL backups. | RAM usage spikes can increment costs. |
| **Render** | Managed Postgres + 2 Web Services | **~$14.00 / mo** ($7/service) | Extremely simple dashboard, automatic SSL, managed database. | Free tier spins down after inactivity (unsuitable for production telemetry). |
| **Fly.io** | 3 Micro-VMs (Front, Back, PG) | **~$5.00 - $8.00 / mo** | Edge deployment close to users, fast cold starts. | Volumes require careful region-pinning. |

> [!TIP]
> **Recommended Portfolio Setup**: A **Hetzner CX22 (€3.79/mo)** or **Railway ($5/mo Hobby plan)** provides the best balance between zero cold starts and low cost.

---

## 7. Database Backups & Recovery Plan

### Automated Nightly PostgreSQL Backup
Create `/etc/cron.daily/tracenest-backup`:

```bash
#!/bin/bash
set -eo pipefail

BACKUP_DIR="/var/backups/tracenest"
DATE=$(date +"%Y%m%d_%H%M%S")
FILENAME="tracenest_backup_${DATE}.sql.gz"

mkdir -p "${BACKUP_DIR}"

# Execute pg_dump inside container and compress
docker exec -t tracenest-db-prod pg_dump -U tracenest_admin -d tracenest | gzip > "${BACKUP_DIR}/${FILENAME}"

# Retain backups for 14 days
find "${BACKUP_DIR}" -type f -name "tracenest_backup_*.sql.gz" -mtime +14 -delete

echo "TraceNest backup completed: ${FILENAME}"
```

Make executable:
```bash
chmod +x /etc/cron.daily/tracenest-backup
```

### Database Restore Procedure
```bash
gunzip < /var/backups/tracenest/tracenest_backup_YYYYMMDD_HHMMSS.sql.gz | \
  docker exec -i tracenest-db-prod psql -U tracenest_admin -d tracenest
```

---

## 8. Incident Response & Troubleshooting Playbook

| Symptom | Probable Cause | Diagnostic Command | Remediation Action |
| :--- | :--- | :--- | :--- |
| **HTTP 401 Unauthorized on Telemetry** | Key revoked, expired, or invalid prefix | `docker logs tracenest-backend-prod` | Generate a new scoped ingestion key via `/api/v1/projects/ingestion-keys`. |
| **HTTP 403 Forbidden on Management Route** | Using `tn_ingest_...` key on `/projects` or `/issues` | Inspect `X-API-Key` header | Switch to project management key (`tn_mgmt_...`). |
| **HTTP 429 Too Many Requests** | Client exceeded 120 req/min rate limit | Check `Retry-After` header | Implement exponential backoff in client or increase `RATE_LIMIT_PER_MINUTE`. |
| **Database Connection Refused** | PostgreSQL container not healthy | `docker ps -a` and `docker inspect tracenest-db-prod` | Check disk space (`df -h`) and restart database container. |
| **AI Investigation Timeout / 504** | LLM API rate limit or invalid API key | `docker logs tracenest-backend-prod \| grep -i gemini` | Verify `GEMINI_API_KEY` validity and quotas. TraceNest will return cached reports if available. |
