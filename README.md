# 🤖 Nexus AI - Autonomous Marketing Agent Society

**A 13-agent marketing society, orchestrated end-to-end, powered by Alibaba Cloud's Qwen.**

Nexus AI is a multi-tenant autonomous digital marketing platform where 13 specialized AI agents — each with a distinct role — collaborate through a central orchestrator to plan, create, audit, optimize, and report on a brand's marketing activity. Agents don't just run in parallel: Brand Guardian reviews and can block Social Manager's content before it ever gets auto-published, demonstrating real task division and conflict resolution, not just isolated API calls.

Built for the **Qwen Cloud Global AI Hackathon 2026 — Track 3: Agent Society**.

## 🤖 The Agent Society

| Agent | Role |
|---|---|
| **Analytics** | Gathers performance insights that inform every other agent's decisions |
| **Social Manager** | Creates platform-specific content suggestions and handles publishing |
| **Brand Guardian** | Audits Social Manager's content for compliance/brand risk *before* publish — can block and escalate to human review |
| **Digital Marketer** | Develops 30-day multi-channel marketing strategy |
| **Ads Manager** | Analyzes and optimizes ad campaign budgets across platforms |
| **SEO Expert** | Identifies keyword opportunities and technical SEO fixes |
| **Conversion Optimizer** | Evaluates campaign funnels and proposes A/B tests |
| **Community Engagement** | Classifies sentiment on incoming comments/DMs and drafts replies |
| **Market Intelligence** | Produces competitor and industry trend briefs |
| **Dynamic CFO** | Assesses subscription/churn risk and proposes retention offers |
| **Security SRE** | Audits system logs for security anomalies |
| **Calendar Planner** | Plans a multi-day, multi-platform content calendar and persists it to the DB |
| **Media Generator** | Produces image/audio/video creative briefs for calendar items |

All agents run through a single [`AgentOrchestrator`](backend/app/agents/orchestrator.py), which sequences them, logs every action (with the model's reasoning trace) to `AgentActionLog`, and routes higher-risk actions to a human-reviewable `ApprovalQueue`.

## ☁️ Alibaba Cloud / Qwen Integration

All agent intelligence is routed through [`backend/app/agents/qwen_client.py`](backend/app/agents/qwen_client.py), which calls **Qwen-Max via the official `dashscope` Python SDK**. A high-fidelity local simulator is available as a fallback (toggle via `POST /api/v1/admin/config/toggle-simulator`) so the full 13-agent cycle can be demoed reliably without live API cost.

## 🛠️ Tech Stack

- **FastAPI** (sync) — web framework
- **SQLAlchemy** (sync engine) + **SQLite** — local demo database (swap `DATABASE_URL` for Postgres in production)
- **dashscope** — Alibaba Cloud Qwen SDK
- **JWT** (PyJWT) + **bcrypt** — auth
- **Stripe / Coinbase Commerce / SendGrid** — billing and email integrations (present but not part of the agent-society demo path)

## 🚀 Quick Start

### Prerequisites
- Python 3.11+

### 1. Install dependencies
```bash
cd backend
pip install -r requirements.txt
```

### 2. Configure environment
Copy `.env` at the project root (or create one) with at minimum:
```
DASHSCOPE_API_KEY=your-qwen-api-key
DASHSCOPE_BASE_URL=https://dashscope.aliyuncs.com/api/v1
DATABASE_URL=sqlite:///./nexus_ai.db
```
Without a real key, the app runs entirely on the local simulator by default (`force_simulator = True` in `qwen_client.py`) — no key required to try it out.

### 3. Run the server
```bash
uvicorn app.main:app --reload
```

- API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Health check: http://localhost:8000/health

### 4. Try the agent society
```bash
# Register a workspace (also seeds initial agent logs/approvals)
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"you@example.com","password":"YourPass123!","name":"Your Name","company_name":"Your Co"}'

# Use the returned access_token + workspace_id:
curl -X POST "http://localhost:8000/api/v1/dashboard/agents/optimize?workspace_id=YOUR_WORKSPACE_ID" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## 🧪 Testing

```bash
cd backend
pytest tests/ -v
```

## 📖 API Documentation

### Authentication
```
POST /api/v1/auth/register
POST /api/v1/auth/login
GET  /api/v1/auth/me
```

### Dashboard / Agent Orchestration
```
GET  /api/v1/dashboard/workspaces
GET  /api/v1/dashboard/summary?workspace_id=ws-123
GET  /api/v1/dashboard/agent-logs?workspace_id=ws-123&limit=50
GET  /api/v1/dashboard/approvals?workspace_id=ws-123
POST /api/v1/dashboard/approvals/{approval_id}/review?decision=approved

# Run the full 13-agent cycle
POST /api/v1/dashboard/agents/optimize?workspace_id=ws-123

# Run one agent individually
POST /api/v1/dashboard/agents/{agent_name}/run?workspace_id=ws-123
```

### Content
```
POST /api/v1/content/generate
POST /api/v1/content/create
GET  /api/v1/content/calendar/items?workspace_id=ws-123
```

### Campaigns
```
GET  /api/v1/campaigns/list?workspace_id=ws-123
POST /api/v1/campaigns/create
POST /api/v1/campaigns/optimize?workspace_id=ws-123
```

### Admin
```
GET  /api/v1/admin/health
GET  /api/v1/admin/tenants?limit=50
GET  /api/v1/admin/config/status
POST /api/v1/admin/config/toggle-simulator?force_simulator=false
```

## 📊 Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   FastAPI Backend (sync)                │
│                  http://localhost:8000                  │
│                                                           │
│  Auth Router │ Dashboard Router │ Content │ Campaigns    │
│  Billing │ Admin                                         │
│                                                           │
│  ┌─────────────────────────────────────────────────┐    │
│  │             Agent Orchestrator                   │    │
│  │  Analytics → Social Manager ⇄ Brand Guardian     │    │
│  │  → Digital Marketer → Ads Manager → SEO Expert   │    │
│  │  → Conversion Optimizer → Community Engagement   │    │
│  │  → Market Intelligence → Dynamic CFO             │    │
│  │  → Security SRE → Calendar Planner               │    │
│  │  → Media Generator                               │    │
│  └───────────────────────┬───────────────────────────┘    │
│                          │                                │
│                  ┌───────▼────────┐                      │
│                  │  qwen_client.py │──── dashscope SDK ──▶ Qwen Cloud
│                  │ (simulator      │                      │
│                  │  fallback)      │                      │
│                  └────────────────┘                      │
└──────────────────────────┬────────────────────────────────┘
                           │
                  ┌────────▼────────┐
                  │  SQLite / SQL   │
                  │  AgentActionLog │
                  │  ApprovalQueue  │
                  └─────────────────┘
```

---

Built for the **Qwen Cloud Global AI Hackathon 2026** — Track 3: Agent Society.

Licensed under the [MIT License](LICENSE).
