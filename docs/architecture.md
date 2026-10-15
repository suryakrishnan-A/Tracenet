# TraceNest Architecture & System Design Document

## 1. Executive Summary & Vision

**TraceNest** is an application failure investigation platform designed to bridge the gap between noisy raw application errors and actionable root-cause resolution. Modern observability tools frequently flood engineers with disconnected alerts, duplicate stack traces, and uncontextualized metrics. 

TraceNest ingests error events and API telemetry, groups correlated errors using fingerprinting algorithms, constructs chronological incident timelines, and orchestrates AI-assisted investigations to produce concise, evidence-grounded incident reports.

---

## 2. High-Level System Architecture

TraceNest is built as a **Modular Monolith**. This pattern provides clear bounded contexts, rapid iteration speed, and zero inter-service network overhead during initial development, while maintaining decoupled interfaces that can easily be extracted into independent microservices if scale requires.

```
                              ┌──────────────────────────────────────────────┐
                              │             Client Applications              │
                              │       (Web Browser / Dev Console)            │
                              └──────────────────────┬───────────────────────┘
                                                     │ HTTP / JSON
                                                     ▼
                              ┌──────────────────────────────────────────────┐
                              │           Next.js 14+ Frontend               │
                              │   - App Router & Server Components           │
                              │   - Centralized API Client (src/lib/api)     │
                              │   - Incident Timelines & Recharts Visualizer │
                              └──────────────────────┬───────────────────────┘
                                                     │ REST API (/api/v1/*)
                                                     ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│                                   FastAPI Backend Modular Monolith                          │
│                                                                                             │
│  ┌───────────────────┐    ┌───────────────────┐    ┌───────────────────┐    ┌────────────┐  │
│  │   API Layer       │    │   Service Layer   │    │   Domain Models   │    │  Database  │  │
│  │  - /health        │───►│  - Event Service  │───►│  - Project        │───►│  Layer     │  │
│  │  - /api/v1/health │    │  - Fingerprinting │    │  - TelemetryEvent │    │ SQLAlchemy │  │
│  │  - /api/v1/events │    │  - Incident Logic │    │  - IssueGroup     │    │   Async    │  │
│  │  - /api/v1/issues │    │  - AI Report Gen  │    │  - Incident       │    │  Session   │  │
│  └───────────────────┘    └───────────────────┘    └───────────────────┘    └─────┬──────┘  │
└───────────────────────────────────────────────────────────────────────────────────┼─────────┘
                                                                                    │
                                                                                    ▼
                                                                      ┌───────────────────────┐
                                                                      │  PostgreSQL Database  │
                                                                      │  - Relational Models  │
                                                                      │  - JSONB Telemetry    │
                                                                      │  - Indexes & Timeline │
                                                                      └───────────────────────┘
```

---

## 3. Technology Stack Justification

| Layer | Technology | Key Architectural Rationale |
| :--- | :--- | :--- |
| **Frontend Framework** | **Next.js 14+ (App Router)** | Server-side rendering for snappy initial loads, TypeScript for strict interface validation, and modern React 18/19 server actions. |
| **Styling** | **Tailwind CSS** | Developer-focused, dark-mode-first aesthetic with low CSS footprint and rapid design consistency. |
| **Visualization** | **Recharts** | Declarative charting library for latency histograms, error frequency spikes, and incident timelines. |
| **Backend Framework** | **FastAPI** | High-throughput asynchronous Python framework, automatic OpenAPI documentation, and native typing. |
| **Validation & Serialization** | **Pydantic v2** | Rust-backed blazing-fast request/response schema validation and type coercion. |
| **ORM & Data Layer** | **SQLAlchemy 2.0 (Async)** | Type-safe query building, connection pooling, and seamless transition between sync migrations and async runtime. |
| **Migrations** | **Alembic** | Deterministic, version-controlled database schema evolution. |
| **Database** | **PostgreSQL 16** | Robust relational integrity, advanced indexing (GIN, BRIN), and native JSONB storage for polymorphic event payloads. |
| **Testing** | **Pytest + HTTPX** | Async-capable testing harnesses for both unit and API integration verification. |

---

## 4. Backend Modular Layout

The backend enforces strict separation of concerns across standard architectural layers:

```
backend/
├── app/
│   ├── api/                  # HTTP Entrypoints (Routers, parameter parsing)
│   │   ├── v1/
│   │   │   ├── endpoints/    # Specific domain route handlers
│   │   │   │   ├── health.py
│   │   │   │   ├── events.py (Phase 2)
│   │   │   │   └── issues.py (Phase 3)
│   │   │   └── api.py        # v1 Aggregator Router
│   ├── core/                 # Cross-cutting concerns
│   │   ├── config.py         # Pydantic BaseSettings with .env validation
│   │   └── logging.py        # Structured log configuration
│   ├── db/                   # Database engine, connection lifecycle, session factory
│   │   ├── base.py           # Declarative base class
│   │   └── session.py        # Async engine & get_db dependency
│   ├── models/               # SQLAlchemy ORM declarative models
│   │   └── project.py, event.py, issue.py
│   ├── schemas/              # Pydantic input/output validation contracts
│   │   └── health.py, event.py, issue.py
│   ├── services/             # Pure business logic and domain processing
│   │   └── fingerprinting.py, incident_service.py
│   └── main.py               # FastAPI factory, middleware configuration, root endpoints
└── tests/                    # Integration and unit tests
    ├── conftest.py           # Shared test fixtures and TestClient configuration
    └── test_health.py        # Endpoint health tests
```

---

## 5. Frontend Architecture & Centralized API Client

Direct invocations of `fetch` or `axios` across React components create tight coupling, brittle endpoints, and duplicated error handling. TraceNest uses a **Centralized API Client pattern**:

1. **`src/lib/api/client.ts`**:
   - Single point of HTTP dispatch.
   - Reads `NEXT_PUBLIC_API_BASE_URL` with robust fallbacks.
   - Implements standardized timeout, JSON serialization, and structured error responses.
2. **Domain Service Modules**:
   - Dedicated modules (`src/lib/api/health.ts`, `src/lib/api/events.ts`) wrap the client and expose strongly typed promises.
3. **Type Safety**:
   - TypeScript interfaces mirror Pydantic schemas, ensuring compile-time safety across the network boundary.

---

## 6. Phased Implementation Roadmap

- **Phase 1: Project Initialization & Architecture (Current)**
  - Workspace scaffolding, multi-tier health endpoints (`/health` and `/api/v1/health`), centralized frontend client, pytest harness, documentation.
- **Phase 2: Database Layer & Telemetry Ingestion Engine**
  - PostgreSQL containerization, SQLAlchemy async models, Alembic migrations, `/api/v1/telemetry` ingestion endpoint with Pydantic validation.
- **Phase 3: Error Fingerprinting & Issue Grouping**
  - Grouping algorithms (normalizing stack traces, hashing error types, frame analysis), issue aggregation metrics.
- **Phase 4: Timeline & Visualization Dashboard**
  - Next.js dashboard UI with Recharts displaying issue frequency, latency percentiles, and incident event chronologies.
- **Phase 5: AI-Assisted Root Cause Investigation Engine**
  - LLM evidence synthesis, deterministic prompt templates, markdown incident report generation.
