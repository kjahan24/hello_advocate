# AI Lawyer — Bangladesh Legal SaaS Platform
## CLAUDE.md — Project Master Context File

> Claude reads this file at the start of every session.
> Do NOT remove or rename this file.

---

## 1. PROJECT IDENTITY

**App Name:** AI Lawyer
**Tagline:** Bangladesh-er Aain, Apnar Bhashay (বাংলাদেশের আইন, আপনার ভাষায়)
**Type:** Full-stack SaaS Web Application
**Purpose:** AI-powered Bangladesh law assistant — citizens, lawyers, and businesses
can query any Bangladesh law in Bengali or English using natural language.

**Three mandatory core features (NEVER skip these):**
1. INTENT DETECTION → classify what the user legally wants
2. DIRECT DATA QUERY → hit PostgreSQL/pgvector based on intent
3. AI CHATBOT → stream a human-readable legal response

---

## 2. TECH STACK (STRICT — never deviate without asking)

### Frontend
- Framework: Next.js 14 (App Router, not Pages Router)
- Language: TypeScript (strict mode, no `any`)
- Styling: Tailwind CSS + shadcn/ui
- State: Zustand
- Forms: React Hook Form + Zod validation
- HTTP: Axios + React Query (TanStack Query v5)

### Backend
- Server: FastAPI (Python 3.11+)
- Language: Python with full type hints (Pydantic v2)
- Auth: NextAuth.js (JWT + Google OAuth) on frontend; FastAPI verifies JWT
- Task Queue: Celery + Redis
- WebSockets/SSE: FastAPI StreamingResponse for chat

### Database
- Primary: PostgreSQL 16 with pgvector extension
- Cache: Redis 7
- ORM: SQLAlchemy 2.0 (async with asyncpg driver)
- Migrations: Alembic
- Search: pgvector cosine similarity (ivfflat index)

### AI / ML
- LLM: claude-sonnet-4-20250514 via Anthropic SDK (Python)
- Embeddings: multilingual-e5-large (HuggingFace, free) OR text-embedding-3-small (OpenAI)
- RAG: LangChain + pgvector retriever
- Intent: keyword classifier (Stage 1) + Claude API (Stage 2 fallback)

### Infrastructure
- Containers: Docker + Docker Compose
- CI/CD: GitHub Actions
- Frontend hosting: Vercel
- Backend hosting: Railway.app
- File storage: AWS S3
- Monitoring: Sentry (errors) + PostHog (analytics)

---

## 3. FOLDER STRUCTURE

```
ai-lawyer/
├── CLAUDE.md                    ← this file
├── docker-compose.yml
├── .env.example
├── README.md
│
├── frontend/                    ← Next.js 14 App
│   ├── app/
│   │   ├── (auth)/
│   │   │   ├── login/page.tsx
│   │   │   └── register/page.tsx
│   │   ├── (main)/
│   │   │   ├── chat/page.tsx          ← main feature
│   │   │   ├── chat/[id]/page.tsx     ← session view
│   │   │   ├── laws/page.tsx          ← browse acts
│   │   │   ├── laws/[act_id]/page.tsx ← single act
│   │   │   ├── cases/page.tsx
│   │   │   └── dashboard/page.tsx
│   │   ├── api/auth/[...nextauth]/route.ts
│   │   ├── layout.tsx
│   │   └── page.tsx                   ← landing page
│   ├── components/
│   │   ├── chat/
│   │   │   ├── ChatInterface.tsx      ← primary component
│   │   │   ├── MessageBubble.tsx
│   │   │   ├── IntentBadge.tsx
│   │   │   ├── SourceCard.tsx
│   │   │   └── SuggestedQuestions.tsx
│   │   ├── laws/
│   │   │   ├── ActCard.tsx
│   │   │   ├── SectionView.tsx
│   │   │   └── ActBrowser.tsx
│   │   └── ui/                        ← shadcn components
│   ├── lib/
│   │   ├── api.ts                     ← API client
│   │   ├── store.ts                   ← Zustand store
│   │   ├── auth.ts                    ← NextAuth config
│   │   └── utils.ts
│   ├── types/
│   │   └── index.ts                   ← shared TypeScript types
│   ├── public/
│   ├── tailwind.config.ts
│   ├── next.config.ts
│   └── package.json
│
├── backend/                     ← FastAPI App
│   ├── app/
│   │   ├── main.py                    ← FastAPI app entry
│   │   ├── config.py                  ← settings via pydantic-settings
│   │   ├── routers/
│   │   │   ├── chat.py                ← POST /api/chat (SSE stream)
│   │   │   ├── acts.py
│   │   │   ├── cases.py
│   │   │   └── auth.py
│   │   ├── services/
│   │   │   ├── intent_detector.py     ← Stage 1 + Stage 2 classifier
│   │   │   ├── query_router.py        ← routes intent → DB strategy
│   │   │   ├── rag_pipeline.py        ← retrieval + Claude streaming
│   │   │   └── embedding_service.py   ← generate + cache embeddings
│   │   ├── models/
│   │   │   ├── act.py
│   │   │   ├── section.py
│   │   │   ├── case.py
│   │   │   ├── user.py
│   │   │   └── message.py
│   │   ├── schemas/                   ← Pydantic request/response schemas
│   │   │   ├── chat.py
│   │   │   └── act.py
│   │   ├── db/
│   │   │   ├── database.py            ← async engine + session factory
│   │   │   └── migrations/            ← Alembic migrations
│   │   └── core/
│   │       ├── security.py            ← JWT verification
│   │       └── rate_limiter.py        ← per-user query limits
│   ├── scripts/
│   │   ├── ingest_acts.py             ← one-time data import
│   │   └── generate_embeddings.py     ← batch embedding generator
│   ├── tests/
│   │   ├── test_intent.py
│   │   ├── test_query_router.py
│   │   └── test_chat_api.py
│   ├── Dockerfile
│   └── requirements.txt
```

---

## 4. DATABASE SCHEMA

### Key tables (PostgreSQL 16 + pgvector)

```sql
-- Always run first
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- acts: Bangladesh legal acts (1484+ from bdlaws.minlaw.gov.bd)
CREATE TABLE acts (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    act_id          VARCHAR(20) UNIQUE NOT NULL,
    title_en        TEXT NOT NULL,
    title_bn        TEXT,
    year            INTEGER,
    category        VARCHAR(50),        -- see Section 5 categories
    subcategory     VARCHAR(100),
    is_repealed     BOOLEAN DEFAULT FALSE,
    full_text_en    TEXT,
    full_text_bn    TEXT,
    source_url      TEXT,
    embedding       VECTOR(1536),
    created_at      TIMESTAMP DEFAULT NOW()
);

-- sections: individual clauses/sections of each act
CREATE TABLE sections (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    act_id          UUID REFERENCES acts(id) ON DELETE CASCADE,
    section_number  VARCHAR(20),
    title           TEXT,
    content_en      TEXT,
    content_bn      TEXT,
    keywords        TEXT[],
    embedding       VECTOR(1536),
    created_at      TIMESTAMP DEFAULT NOW()
);

-- cases: court judgments (from BDLex / Legislib)
CREATE TABLE cases (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    citation        TEXT UNIQUE,
    court           VARCHAR(100),
    year            INTEGER,
    parties         TEXT,
    summary         TEXT,
    related_acts    UUID[],
    embedding       VECTOR(1536),
    created_at      TIMESTAMP DEFAULT NOW()
);

-- users
CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email           TEXT UNIQUE NOT NULL,
    name            TEXT,
    role            VARCHAR(20) DEFAULT 'citizen',
    plan            VARCHAR(20) DEFAULT 'free',
    query_count_today INTEGER DEFAULT 0,
    query_limit     INTEGER DEFAULT 10,
    created_at      TIMESTAMP DEFAULT NOW()
);

-- chat_sessions
CREATE TABLE chat_sessions (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID REFERENCES users(id),
    title           TEXT,
    created_at      TIMESTAMP DEFAULT NOW()
);

-- messages
CREATE TABLE messages (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id      UUID REFERENCES chat_sessions(id) ON DELETE CASCADE,
    role            VARCHAR(10) NOT NULL,   -- 'user' | 'assistant'
    content         TEXT NOT NULL,
    intent          VARCHAR(50),
    category        VARCHAR(50),
    sources         JSONB,
    created_at      TIMESTAMP DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_acts_category    ON acts(category);
CREATE INDEX idx_acts_embedding   ON acts    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX idx_sections_act_id  ON sections(act_id);
CREATE INDEX idx_sections_embedding ON sections USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX idx_messages_session ON messages(session_id);
```

---

## 5. INTENT DETECTION SYSTEM

### 9 Primary Intents
```
FIND_LAW        → "চুরির শাস্তি কী?" / "punishment for theft?"
FIND_SECTION    → "ধারা ৩০২ কী?" / "what is section 302?"
FIND_CASE       → "জমি নিয়ে কোনো নজির আছে?"
EXPLAIN_RIGHTS  → "আমার কী কী অধিকার আছে?"
CHECK_PROCESS   → "মামলা করতে হলে কী করতে হবে?"
COMPARE_LAWS    → "দেওয়ানি ও ফৌজদারি পার্থক্য কী?"
GET_DOCUMENT    → "তালাকের জন্য কোন ফর্ম লাগে?"
GENERAL_INFO    → "আইনজীবী কোথায় পাব?"
UNKNOWN         → fallback — ask clarifying question
```

### 12 Legal Categories
```
criminal | civil | family | land_property | labor_employment |
constitutional | commercial_business | banking_finance |
tenancy_rent | consumer_rights | digital_cyber | immigration
```

### Two-Stage Classification
- **Stage 1 (fast, ~0ms):** Keyword/regex match. Handles ~80% of queries.
- **Stage 2 (LLM, ~400ms):** Claude API call for ambiguous queries (confidence < 0.7).

### Claude LLM Classification Prompt (Stage 2)
```
System: You are a legal intent classifier for Bangladesh law. Return only valid JSON.

User:
Classify this legal query for the Bangladesh jurisdiction.
Query: "{user_query}"

Return ONLY this JSON structure, no other text:
{
  "intent": "<one of the 9 intents above>",
  "category": "<one of the 12 categories above>",
  "confidence": <float 0.0-1.0>,
  "language": "bn|en|mixed",
  "key_concepts": ["concept1", "concept2"]
}
```

---

## 6. QUERY ROUTER LOGIC

After intent detection, route to the correct DB strategy:

| Intent | Strategy | Query Type |
|---|---|---|
| FIND_SECTION | Exact match | `WHERE section_number = ?` |
| FIND_LAW | Vector search | pgvector cosine similarity on sections |
| EXPLAIN_RIGHTS | Vector search | pgvector on acts + sections |
| FIND_CASE | Case search | Vector on cases table |
| CHECK_PROCESS | Hybrid | keyword + vector |
| COMPARE_LAWS | Multi-vector | Two separate vector searches |
| GET_DOCUMENT | Keyword | Full-text search |
| GENERAL_INFO | Knowledge | LLM direct (no DB needed) |

### Core Vector Search SQL Pattern
```sql
SELECT
    a.title_en, a.category, a.year, a.act_id,
    s.section_number, s.content_en, s.content_bn,
    1 - (s.embedding <=> :query_embedding) AS relevance_score
FROM sections s
JOIN acts a ON s.act_id = a.id
WHERE a.category = :category
  AND a.is_repealed = FALSE
  AND 1 - (s.embedding <=> :query_embedding) > 0.6
ORDER BY s.embedding <=> :query_embedding
LIMIT :top_k;
```

---

## 7. CHATBOT SYSTEM PROMPT

Inject this at every Claude API call for the chat feature:

```
You are AI Lawyer, an expert AI assistant specializing in Bangladesh law.
You help Bangladeshi citizens, lawyers, and businesses understand their 
legal rights and options under Bangladesh legislation.

STRICT RULES:
1. Base answers ONLY on the provided legal context from the database
2. Always cite the exact Act name and Section number: [Act Name, Section X]
3. Respond in the SAME language the user used (Bengali or English)
4. Structure every response as:
   a) Direct answer (2-3 sentences)
   b) Relevant law: [Act Name, Section X]
   c) Plain language explanation
   d) Practical next steps
   e) Disclaimer (mandatory, always last)
5. NEVER fabricate laws, sections, or case citations
6. If no relevant law is found in context, say: 
   "এই বিষয়ে আমার ডেটাবেজে সুনির্দিষ্ট তথ্য নেই। একজন আইনজীবীর সাথে যোগাযোগ করুন।"
7. ALWAYS end with this disclaimer:
   Bengali: "⚠️ এটি AI-সহায়তা, আইনি পরামর্শ নয়। গুরুত্বপূর্ণ বিষয়ে একজন যোগ্য আইনজীবীর সাথে পরামর্শ করুন।"
   English: "⚠️ This is AI assistance, not legal advice. For serious matters, consult a qualified lawyer."
```

---

## 8. KEY API ENDPOINTS

```
POST   /api/chat                    ← main endpoint (SSE streaming)
POST   /api/chat/sessions           ← create new chat session
GET    /api/chat/sessions           ← list user sessions
GET    /api/chat/sessions/{id}      ← get session + all messages

GET    /api/acts                    ← list acts (filter: category, year)
GET    /api/acts/{act_id}           ← single act with all sections
GET    /api/acts/search?q=          ← full-text search

GET    /api/cases                   ← list cases
GET    /api/cases/search?q=         ← search case laws

POST   /api/auth/register
POST   /api/auth/login
GET    /api/users/me
GET    /api/users/me/usage

POST   /api/admin/ingest            ← trigger data ingestion (admin only)
```

### Chat Endpoint SSE Stream Format
```
data: {"type": "intent",   "data": {"intent": "FIND_LAW", "category": "criminal"}}
data: {"type": "sources",  "data": [{"act": "Penal Code 1860", "section": "379"}]}
data: {"type": "token",    "data": "চুরির"}
data: {"type": "token",    "data": " শাস্তি"}
...
data: {"type": "done",     "data": {"message_id": "uuid", "response_time_ms": 980}}
```

---

## 9. DATA SOURCES

| Source | Type | URL | Cost | Priority |
|---|---|---|---|---|
| BD Laws Portal | Acts 1836–present | bdlaws.minlaw.gov.bd | Free (scrape) | 1st |
| HuggingFace Dataset | 1484+ acts JSON | sakhadib/Bangladesh-Legal-Acts-Dataset | Free (CC-BY 4.0) | Use for MVP |
| BDLex | Case laws | bdlex.com | Paid | Phase 2 |
| Legislib | 200K+ cases | legislib.com | Paid subscription | Phase 2 |

### Ingestion Order for MVP
1. Download `sakhadib/Bangladesh-Legal-Acts-Dataset` from HuggingFace
2. Parse JSON → insert into `acts` and `sections` tables
3. Generate embeddings for all sections (batch of 50)
4. Build ivfflat index

---

## 10. PRICING PLANS

```
FREE     → 10 queries/day | Acts only | No history saved
PRO      → 200 queries/day | Acts + Cases | History | PDF export | ৳499/month
LAWYER   → Unlimited | All features + doc upload + API access | ৳1999/month
ENTERPRISE → Custom | On-premise option | Private doc training | Custom price
```

---

## 11. ENVIRONMENT VARIABLES

```bash
# .env (never commit this file)
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/ai_lawyer
REDIS_URL=redis://localhost:6379
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
NEXTAUTH_SECRET=change-me-in-production
NEXTAUTH_URL=http://localhost:3000
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_S3_BUCKET=ai-lawyer-docs
JWT_SECRET=change-me
CORS_ORIGINS=http://localhost:3000
SENTRY_DSN=...
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## 12. CODE STANDARDS (enforce strictly)

### Python (backend)
- Full type hints on all functions using Pydantic v2 models
- Async all DB calls: `async with db.begin():`
- Error handling: raise HTTPException with clear detail messages
- Logging: use `structlog` with JSON output
- No raw SQL strings — use SQLAlchemy ORM or text() with bound params
- Tests: pytest + pytest-asyncio, minimum 80% coverage on services/

### TypeScript (frontend)
- No `any` type — use `unknown` then narrow
- All API calls through `lib/api.ts` — no raw fetch elsewhere
- Components: functional only, no class components
- Zod schema for every API response before use
- Error boundaries on all page-level components

### Git
- Branch naming: `feat/`, `fix/`, `chore/`
- Never commit `.env` or secrets
- Commit messages: conventional commits (`feat:`, `fix:`, `docs:`)
- PR required for main branch — no direct pushes

---

## 13. DEVELOPMENT COMMANDS

```bash
# Full stack startup
docker compose up -d

# Backend only
cd backend && uvicorn app.main:app --reload --port 8000

# Frontend only
cd frontend && npm run dev

# Run data ingestion (one-time)
cd backend && python scripts/ingest_acts.py

# Generate embeddings (after ingestion)
cd backend && python scripts/generate_embeddings.py

# Run tests
cd backend && pytest tests/ -v
cd frontend && npm run test

# Database migrations
cd backend && alembic upgrade head
cd backend && alembic revision --autogenerate -m "description"

# Lint
cd backend && ruff check app/ && mypy app/
cd frontend && npm run lint
```

---

## 14. HOW TO WORK WITH CLAUDE CODE

### Giving tasks
Always use this format:
```
BUILD: <component name>
```
Examples:
- `BUILD: IntentDetector service (backend/app/services/intent_detector.py)`
- `BUILD: Chat SSE streaming endpoint (backend/app/routers/chat.py)`
- `BUILD: ChatInterface React component (frontend/components/chat/ChatInterface.tsx)`
- `BUILD: Database schema + Alembic migration`
- `BUILD: Data ingestion script (backend/scripts/ingest_acts.py)`
- `BUILD: Docker Compose full setup`
- `BUILD: Landing page (frontend/app/page.tsx)`
- `BUILD: Act browser page with filter + search`

### Rules for Claude
- Always check this CLAUDE.md before writing any code
- Never use a different tech stack than Section 2
- Every backend service must implement all 3 core features (intent + query + chat)
- Write complete working code — no `# TODO` or `pass` placeholders
- Include error handling, logging, and type hints always
- Follow the folder structure in Section 3 exactly
- When generating a new file, state which path you're writing to first

---

## 15. PROJECT STATUS (updated 2026-06-11, Phase 19 complete)

### Infrastructure
- Docker data root moved to `D:\DockerData` — D: drive used for containers
- C: drive: ~51 GB free
- All containers healthy: PostgreSQL, Redis, migrate, backend, frontend
- **Backend image is lean** — no ML/GPU packages (sentence-transformers removed)
- Embeddings: OpenAI `text-embedding-3-small` (not local HuggingFace model)

### Password hashing
- **Direct `bcrypt==4.0.1`** — passlib removed entirely
- `backend/app/routers/auth.py` and `backend/app/core/security.py` both use direct `bcrypt` calls
- 72-byte UTF-8 truncation pattern applied consistently at all 4 call sites:
  `plain.encode('utf-8')[:72].decode('utf-8', errors='ignore').encode('utf-8')`
- `security.py` exposes `hash_password()` / `verify_password()` helpers (thin wrappers around bcrypt)

### Dependencies — key decisions
- `sentence-transformers` **removed** from `requirements.txt` (was pulling PyTorch/CUDA, caused Docker build timeout)
- All ingestion/scraping packages moved to `backend/requirements-scripts.txt` (install locally when running scripts)
- `pypdf==3.17.4` and `python-docx==0.8.11` pinned (document analysis)
- `weasyprint>=60.0` added (Phase 9); requires Pango/Cairo system libs in Dockerfile
- `reportlab>=4.0.0` kept in requirements but PDF generation now uses WeasyPrint (reportlab cannot shape Bengali conjuncts)
- `pip install --timeout 300 --retries 5` in Dockerfile

---

### Phase 1 — Auth ✅ COMPLETE (one deferred issue)
| Feature | Status | Notes |
|---|---|---|
| Register (`POST /api/auth/register`) | ✅ | bcrypt hash, JWT returned |
| Login (`POST /api/auth/login`) | ✅ | direct fetch to backend (no NextAuth) |
| JWT stored in localStorage | ✅ | keys: `token`, `user` |
| Login browser autofill | ⚠️ Deferred | browser autofill bypasses React state |
| NavBar auth | ⚠️ Deferred | still reads `useSession()` (NextAuth); needs localStorage migration |

---

### Phase 2 — Legal Category Pages ✅ COMPLETE
All pages: hero → 4 service cards (→ `/chat?q=`) → 5 FAQ accordions → CTA

| Page | Route | Status |
|---|---|---|
| জমি ও সম্পত্তি | `/land` | ✅ |
| পারিবারিক আইন | `/family` | ✅ |
| ব্যবসায়িক আইন | `/business` | ✅ |
| শ্রম আইন | `/labor` | ✅ |
| ভোক্তা অধিকার | `/consumer` | ✅ |

- NavBar: "আইনি সেবা" dropdown (5 links) + "📄 ডকুমেন্ট" link — all active
- Chat pre-fill: `/chat?q=<encoded>` → `useSearchParams()` in `ChatInterface` → "প্রশ্ন পাঠান →" button
- `app/chat/page.tsx` deleted (route conflict) — canonical: `app/(main)/chat/page.tsx` + `Suspense`

---

### Phase 3 — Document Assistant ✅ COMPLETE
- **Page:** `frontend/app/document/page.tsx` → `/document`
- **Endpoint:** `POST /api/documents/analyze` (`backend/app/routers/documents.py`)
- **File support:** PDF (`pypdf`), DOCX (`python-docx`), legacy `.doc` (UTF-8 best-effort)
- **Upload UX:** drag & drop + file picker, 10 MB limit, client-side ext/size validation
- **Analysis output:** 4 cards — summary (white), risks (red), dates (blue), advice (green)
- **Claude prompt:** Bengali JSON-only instruction + single-line schema; system prompt enforces no markdown
- **Parser:** 4-stage fallback — `json.loads` → strip fences → regex `{.*}` → `ast.literal_eval` → structured error dict (never returns 500 to frontend)
- **max_tokens:** 2000 (Bengali text needs headroom; 1024 caused truncation → broken JSON)

---

### Phase 4 — Payment Gateway ✅ COMPLETE
| Feature | Status | Notes |
|---|---|---|
| SSLCommerz integration | ✅ | Sandbox (`testbox`/`qwerty`); switch `SSLCOMMERZ_SANDBOX=false` for prod |
| Pricing page (`/pricing`) | ✅ | FREE ৳০ vs PRO ৳৯৯৯/মাস cards |
| Payment initiate (`POST /api/payments/initiate`) | ✅ | Creates pending Subscription, returns GatewayPageURL |
| Success / Fail / Cancel pages | ✅ | `/payment/success`, `/payment/fail`, `/payment/cancel` |
| IPN webhook (`POST /api/payments/ipn`) | ✅ | Server-to-server verify + activate |
| Subscriptions table | ✅ | Migration `0004_add_subscriptions.py` applied |
| Auth bug fix — register auto-login | ✅ | `register/page.tsx` captures JWT from register response; no NextAuth |
| Login redirect (`?redirect=`) | ✅ | `login/page.tsx` reads param via `URLSearchParams`, falls back to `/dashboard` |
| Unauthenticated payment 401 | ✅ | Bengali message "পেমেন্ট শুরু করতে লগইন করুন।" |

- **Payment methods available via SSLCommerz:** bKash, Nagad, Rocket, Cards (Visa/Master/Amex)
- **Plan upgrade flow:** payment verified → `user.plan = 'pro'`, `query_limit = 200`, `expires_at = now + 30d`
- **Auth architecture:** Pure localStorage JWT (`token`, `user` keys) — NextAuth removed from register page

---

### Phase 5 — Dashboard ✅ COMPLETE
| Feature | Status | Notes |
|---|---|---|
| Dashboard page (`/dashboard`) | ✅ | Hero + 4 stat cards + quick actions + subscription card |
| Dashboard API (`GET /api/dashboard/stats`) | ✅ | User info, active subscription, chat count |
| NavBar localStorage auth | ✅ | Reads `token`/`user` from localStorage; no NextAuth |
| next-auth fully removed from NavBar | ✅ | `useSession` / `signOut` replaced with localStorage state |
| Subscription badge | ✅ | Grey "বিনামূল্যে" or gold "প্রো ⭐" in hero |
| Pro upgrade CTA (free users only) | ✅ | Hidden for active pro subscribers |

- **Auth architecture (final):** Pure localStorage JWT across all pages — NavBar, login, register, dashboard, pricing all use `localStorage.getItem('token')`
- **Dashboard redirect:** Unauthenticated → `/login?redirect=/dashboard`; expired token → clear localStorage + redirect

---

### Phase 6 — Lawyer Referral Marketplace ✅ COMPLETE
| Feature | Status | Notes |
|---|---|---|
| Lawyers list page (`/lawyers`) | ✅ | 3-column card grid, filter by specialization + location |
| Lawyer profile page (`/lawyers/[id]`) | ✅ | Bio, fees, tags, contact reveal, chat CTA |
| Backend API (`GET /api/lawyers`, `GET /api/lawyers/{id}`) | ✅ | Sorted by rating; specialization filter in Python |
| Contact endpoint (`POST /api/lawyers/{id}/contact`) | ✅ | Auth required; returns phone + email |
| 6 seeded lawyers | ✅ | Rahman, Fatema, Karim, Sultana, Islam, Rehana — all `is_verified=true` |
| Lawyers table + lawyer_reviews table | ✅ | Migration `0005_add_lawyers.py` applied |
| NavBar "আইনজীবী" link | ✅ | Added before মূল্য তালিকা |
| Document page CTA updated | ✅ | Now links to `/lawyers` instead of `/chat` |

- **Seed script:** `docker compose exec backend python app/data/seed_lawyers.py` (idempotent, skips by `bar_number`)
- **Contact flow:** Button click → POST with Bearer token → reveals phone/email; login redirect if unauthenticated

---

### Phase 7 — Court Date Reminder ✅ COMPLETE
| Feature | Status | Notes |
|---|---|---|
| Court cases page (`/court-cases`) | ✅ | Hero + 3 stat cards + case cards grid + add/edit modal |
| Add / Edit / Delete cases | ✅ | Modal form; DELETE returns `Response(status_code=204)` directly |
| Urgency coloring | ✅ | 🔴 আজ!, ⚠️ ≤7 days (red), ⏰ ≤30 days (amber), normal >30 days |
| Upcoming reminders banner | ✅ | Red banner lists all cases due within 7 days |
| Backend CRUD (`/api/court-cases`) | ✅ | 6 endpoints; `/upcoming` declared before `/{id}` to avoid conflict |
| Migration `0006_add_court_cases.py` | ✅ | `court_cases` table; indexes on user_id, next_date, status |
| Dashboard `upcoming_cases` stat | ✅ | Red card when >0; counts active cases within 7 days |
| Dashboard quick action | ✅ | "📅 মামলার তারিখ" → `/court-cases` |
| NavBar "📅 মামলা" link | ✅ | Added before "⚖️ আইনজীবী" |
| "আইনজীবী খুঁজুন" CTA | ✅ | Shown at bottom of cases list → `/lawyers` |

- **Route order:** `/court-cases/upcoming` registered before `/court-cases/{case_id}` — critical to prevent FastAPI treating "upcoming" as a UUID
- **Auth:** All endpoints require Bearer token; unauthenticated → redirect `/login?redirect=/court-cases`

---

### Phase 8 — Chat History ✅ COMPLETE
| Feature | Status | Notes |
|---|---|---|
| Chat history page (`/history`) | ✅ | Hero + search bar + category filter + session cards |
| Session cards | ✅ | Title, category badge, relative Bengali time, preview text |
| Full conversation modal | ✅ | Q&A bubbles, close on Escape/outside click, "নতুন প্রশ্ন করুন" CTA |
| Delete session | ✅ | Confirm dialog; 204 response; card removed from list |
| Search + filter | ✅ | Client-side filter by title/preview text + category dropdown |
| Load more pagination | ✅ | "আরও দেখুন" button; `has_more` from backend |
| Backend API (`GET /api/chat-history`) | ✅ | Paginated; `updated_at` = max(messages.created_at); preview from first assistant msg |
| Backend API (`GET /api/chat-history/{id}`) | ✅ | Full transcript ordered by created_at |
| Backend API (`DELETE /api/chat-history/{id}`) | ✅ | Ownership verified; CASCADE deletes messages |
| Dashboard "মোট কথোপকথন" card | ✅ | Now a clickable link → `/history` |
| NavBar user dropdown | ✅ | "📜 চ্যাট ইতিহাস" added between ড্যাশবোর্ড and চ্যাট |
| **BUG FIX: ChatInterface auth** | ✅ | Replaced `useSession()` (NextAuth, always null) with `localStorage.getItem('token')` |

- **Root cause of history showing 0 results:** `ChatInterface.tsx` used `useSession()` from `next-auth/react` — NextAuth was removed in Phase 5, so token was always `undefined`. All chats were saved under `guest@dev.local` UUID, not the real user's UUID.
- **Fix:** `useState` + `useEffect` reads token from localStorage on mount — same pattern as all other pages.
- **Note:** Sessions created before this fix are tied to the guest user and won't appear in history. Only sessions created after the fix are linked to the logged-in user.

---

### Phase 9 — PDF Report Download ✅ COMPLETE
| Feature | Status | Notes |
|---|---|---|
| Backend endpoint (`POST /api/documents/report`) | ✅ | Accepts JSON analysis result; returns PDF as file download |
| WeasyPrint HTML→PDF renderer | ✅ | `weasyprint>=60.0` (installed as 69.0); replaces reportlab |
| Bengali font — Noto Sans Bengali | ✅ | Loaded via Google Fonts `@import` in CSS; full conjunct character (যুক্তাক্ষর) support |
| Dockerfile system packages | ✅ | Added `libpango-1.0-0`, `libpangoft2-1.0-0`, `libpangocairo-1.0-0`, `libgdk-pixbuf-2.0-0`, `libffi8`, `shared-mime-info` |
| reportlab removed | ✅ | Deleted font registration block; `reportlab` kept in requirements only for compatibility |
| Colored section headers | ✅ | সারসংক্ষেপ (green), ঝুঁকি (red), তারিখ (blue), পরামর্শ (green) |
| RFC 5987 Content-Disposition | ✅ | `filename="hello-advocate-report.pdf"; filename*=UTF-8''<encoded>` — no latin-1 crash |
| HTML escaping | ✅ | All user content escaped via `html.escape()` before template insertion |
| Frontend download button | ✅ | Green outlined button on `/document` result page; fetch→blob→anchor click |

- **PDF renderer:** `HTML(string=html_str).write_pdf()` — WeasyPrint renders the HTML template to PDF in-memory
- **Font strategy:** CSS `@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+Bengali...')` — fetched at render time from Google Fonts; no local TTF needed
- **Previous approach (reportlab):** Removed — reportlab's glyph engine cannot shape Bengali conjunct characters correctly regardless of which TTF is registered

---

### Phase 10 — Landing Page Redesign ✅ COMPLETE
| Feature | Status | Notes |
|---|---|---|
| Full viewport hero — dark green gradient | ✅ | `from-[#064e3b] to-[#065f46]`; badge, headline, dual CTA buttons |
| Hero stats row | ✅ | ১,৬০০+ আইন · ৪৬,০০০+ ধারা · ২৪/৭ সেবা |
| Features section (6 cards, 2×3 grid) | ✅ | `#features` anchor; smooth-scroll from hero caret |
| How It Works (3 steps + chevron arrows) | ✅ | `React.Fragment` with key for separators |
| Legal Categories (6 cards → category pages) | ✅ | Links to `/land`, `/family`, `/business`, `/labor`, `/consumer`, `/chat` |
| Pricing Preview (FREE vs PRO) | ✅ | Feature list comparison; CTA to `/pricing` |
| CTA banner | ✅ | Full-width emerald gradient; links to `/register` and `/chat` |
| Footer (3-column) | ✅ | Brand column, সেবাসমূহ links, অ্যাকাউন্ট links |

- **File:** `frontend/app/page.tsx` — `'use client'` for smooth-scroll `onClick`

---

### Phase 11 — Admin Panel ✅ COMPLETE
| Feature | Status | Notes |
|---|---|---|
| Migration `0007_add_is_admin_to_users.py` | ✅ | `is_admin BOOLEAN NOT NULL DEFAULT false` on `users` table |
| User model `is_admin` field | ✅ | `backend/app/models/user.py` |
| `UserResponse` schema `is_admin` | ✅ | `backend/app/schemas/auth.py` + `_to_response()` in `auth.py` |
| `get_admin_user` dependency | ✅ | `backend/app/core/security.py`; raises 403 if `is_admin = false` |
| Admin router (`/api/admin/*`) | ✅ | `backend/app/routers/admin.py` — 8 endpoints |
| `GET /api/admin/stats` | ✅ | 6 platform counters (users, pro, lawyers, verified, subs, active subs) |
| `GET /api/admin/users` + `PATCH /users/{id}` | ✅ | List with search; upgrade plan; toggle admin |
| `GET /api/admin/lawyers` + `POST` + `PATCH /{id}` + `DELETE /{id}` | ✅ | Full CRUD; verify/active toggles |
| `GET /api/admin/subscriptions` | ✅ | Paginated; joined with user email via `selectinload` |
| Admin page (`/admin`) | ✅ | `frontend/app/admin/page.tsx`; sidebar + 4 tabs |
| Overview tab | ✅ | 6 stat cards |
| Users tab | ✅ | Table with search, plan badge, pro/free toggle, admin toggle |
| Lawyers tab | ✅ | Table with verify/active toggles, add-lawyer modal, delete |
| Subscriptions tab | ✅ | Read-only table with status badges |
| NavBar admin link | ✅ | "🔧 অ্যাডমিন প্যানেল" in user dropdown when `storedUser.is_admin` |
| Admin user seeded | ✅ | `bullionus@gmail.com` → `is_admin = true` (SQL UPDATE applied) |

- **Auth gate:** Admin page checks `localStorage.getItem('user').is_admin`; redirects to `/` if not admin
- **Note:** Must re-login after the admin SQL update to get refreshed JWT with `is_admin` in stored user object

---

### Data Ingestion — PARTIAL
| Item | Status | Notes |
|---|---|---|
| 1,484 acts inserted | ✅ | From `sakhadib/Bangladesh-Legal-Acts-Dataset` via direct JSON URL |
| 5,633 sections inserted | ✅ | `--skip-embeddings` flag used (fast insert without OpenAI calls) |
| Embeddings | ⏳ Pending | Run: `pip install -r requirements-scripts.txt && python scripts/generate_embeddings.py` |
| ivfflat index | ⏳ Pending | Auto-built after embeddings populated |
| RAG pipeline active | ❌ Not yet | Claude uses own knowledge until embeddings done; vector search returns empty |

- **Dataset URL:** `https://huggingface.co/datasets/sakhadib/Bangladesh-Legal-Acts-Dataset/resolve/main/Contextualized_Bangladesh_Legal_Acts.json`
- **JSON structure:** `{"dataset_info": {...}, "acts": [1484 items]}` — field aliases: `act_year`, `section_content`
- **To activate RAG:** Run `generate_embeddings.py` (requires `OPENAI_API_KEY`; ~50 sections/batch; ~30 min for all sections)

---

### Phase 12 — Legal Document Templates ✅ COMPLETE
| Feature | Status | Notes |
|---|---|---|
| Templates list page (`/templates`) | ✅ | Category filter tabs, PRO badge, 3-column grid |
| Template form page (`/templates/[id]`) | ✅ | Dynamic fields, PRO gate, Claude generation, copy + PDF download |
| Backend (`GET/POST /api/templates/*`) | ✅ | 5 endpoints; `my-documents` before `/{id}` to avoid FastAPI routing conflict |
| Claude generation | ✅ | `claude-opus-4-5`; 3000 max_tokens; Bengali legal document |
| PDF export (`POST /api/templates/documents/{id}/pdf`) | ✅ | WeasyPrint + Noto Sans Bengali |
| 8 seeded templates | ✅ | `python app/data/seed_templates.py` — ভাড়া চুক্তি, কর্মসংস্থান চুক্তি, বিক্রয় চুক্তি, তালাকনামা, উইল, আমমোক্তারনামা, শ্রমিক অভিযোগ, জমি দলিল |
| NavBar + Dashboard | ✅ | "📝 দলিল টেমপ্লেট" in services menu and quick actions |
| Migration `0008_add_document_templates.py` | ✅ | `document_templates` + `generated_documents` tables |

---

### Phase 13 — Mobile Responsive Polish ✅ COMPLETE
| Feature | Status | Notes |
|---|---|---|
| NavBar hamburger menu | ✅ | `☰` / `✕` toggle; slide-down mobile menu; all nav links + auth in panel |
| Mobile menu | ✅ | Services, document, court-cases, lawyers, pricing, account links; `max-h-[80vh] overflow-y-auto` |
| Chat viewport | ✅ | `h-[100dvh]` (replaces `h-screen`) — avoids mobile browser chrome overflow |
| Category page CTAs | ✅ | `w-full sm:w-auto justify-center` on all 5 pages (land, family, business, labor, consumer) |
| Document upload area | ✅ | `p-6 sm:p-10` — touch-friendly padding on mobile |
| Global scrollbar | ✅ | Green emerald scrollbar (`#059669`) replacing slate; `::-webkit-scrollbar` in globals.css |
| Focus rings | ✅ | `*:focus-visible { outline: 2px solid #059669 }` for keyboard accessibility |
| NavBar z-index | ✅ | Raised from `z-10` to `z-40` — mobile menu overlays page content correctly |

---

### Phase 14 — Legal News Feed ✅ COMPLETE
| Feature | Status | Notes |
|---|---|---|
| News router (`GET /api/news`) | ✅ | `backend/app/routers/news.py`; Redis 30min cache; async concurrent RSS fetch |
| 3 RSS feed sources | ✅ | প্রথম আলো, বিডি প্রতিদিন, যুগান্তর — httpx.AsyncClient + asyncio.gather |
| Legal keyword filter | ✅ | 15 keywords; only legal-relevant items kept |
| Category auto-detection | ✅ | 7 categories: আদালত, হাইকোর্ট, সুপ্রিম কোর্ট, মামলা, রায়, জামিন, আইন |
| 5-item fallback news | ✅ | Returns hardcoded items if all 3 feeds fail |
| News page (`/news`) | ✅ | `frontend/app/news/page.tsx`; blue hero, sticky filter bar, 3-column grid |
| Category + source filter chips | ✅ | Client-side filter; 8 category chips + 3 source chips |
| Skeleton loaders | ✅ | `animate-pulse` gray bars during fetch |
| Auto-refresh every 30min | ✅ | `setInterval(AUTO_REFRESH_MS)` in useEffect |
| NavBar "📰 সংবাদ" link | ✅ | Desktop + mobile menu, after আইনজীবী |
| Landing page news widget | ✅ | 3-card row between Legal Categories and Pricing Preview; hides when no news |

- **RSS parsing**: `root.iter("item")` (namespace-safe) + `parsedate_to_datetime` (RFC 2822) with ISO fallback
- **Redis**: non-fatal — if unavailable, news still fetched and returned uncached
- **Feed robustness**: each `_fetch_one` catches all exceptions and returns `[]`; `asyncio.gather(..., return_exceptions=True)`

---

### Phase 15 — Multi-Language Support ✅ COMPLETE
| Feature | Status | Notes |
|---|---|---|
| `LanguageContext` + `useLanguage()` hook | ✅ | `frontend/contexts/LanguageContext.tsx`; localStorage persistence; `t('section.key')` dotted-key traversal |
| `translations.ts` — bn/en map | ✅ | `frontend/lib/translations.ts`; sections: navbar, landing, services, chat, document, lawyers, courtCases, news, pricing, dashboard, history, auth, common |
| Language toggle button in NavBar | ✅ | `বাং / EN` button; updates context + localStorage |
| `LanguageProvider` in providers.tsx | ✅ | Wraps all pages; SSR hydration-safe via `mounted` state |
| All pages updated with `useLanguage()` | ✅ | chat, document, lawyers, court-cases, news, pricing, dashboard, history, login, register, land, family, business, labor, consumer |
| `language` field in `ChatRequest` schema | ✅ | `backend/app/schemas/chat.py`; `pattern='^(bn|en)$'`; default `'bn'` |
| Dual system prompts in RAG pipeline | ✅ | `_SYSTEM_PROMPT` (Bengali) + `_SYSTEM_PROMPT_EN` (English); selected by `language` param in `stream()` |
| Frontend sends `language` to backend | ✅ | `lib/api.ts` `streamChat()` passes `language` in POST body; `ChatInterface.tsx` reads from `useLanguage()` |

- **Architecture:** Custom React Context — no external i18n library (no next-intl, no react-i18next)
- **Auth/JWT unchanged:** No modification to auth logic or JWT handling
- **API endpoints unchanged:** Only `POST /api/chat` schema extended with optional `language` field (backward-compatible default `'bn'`)

---

### Phase 16 (Admin Dashboard Enhancement) ✅ COMPLETE
| Feature | Status | Notes |
|---|---|---|
| `is_active` field on User model | ✅ | Migration `0009_add_is_active_to_users.py` |
| Enhanced `GET /api/admin/stats` | ✅ | 17 fields: new_users_today/week, chats_today, free/student/pro/active counts, revenue |
| Paginated `GET /api/admin/users` | ✅ | `page`, `limit`, `search`, `plan` filter; returns `{users, total, page, pages}` |
| `DELETE /api/admin/users/{id}` | ✅ | Soft delete — sets `is_active=False`; blocks deletion of admins |
| `GET /api/admin/revenue` | ✅ | Last 12 months breakdown: `{monthly, total_revenue, mrr}` |
| `GET /api/admin/activity` | ✅ | Last 50 activities merged from users/subs/chats; sorted by time |
| Admin dashboard 4 tabs | ✅ | Overview · Users · Revenue · Activity (replaced Lawyers/Subscriptions tabs) |
| Overview tab | ✅ | 8 stat cards (2 rows × 4) + revenue summary card + plan distribution bars |
| Users tab | ✅ | Search + plan filter + paginated table; plan toggle (free/pro/student); soft-delete; admin toggle |
| Revenue tab | ✅ | CSS-only bar chart (12 months) + 3 summary cards + monthly table |
| Activity tab | ✅ | Color-coded timeline: 👤 new user · 💳 payment · 💬 chat |
| Dark sidebar (desktop) | ✅ | `bg-gray-900` sidebar; active tab = emerald highlight |
| Mobile bottom tab bar | ✅ | Fixed 4-tab bar replaces sidebar on mobile |
| Admin translations | ✅ | `admin` section added to `translations.ts` (bn + en) |

- **Soft delete:** sets `user.is_active = False`; admin users are protected (403)
- **Correlated subquery:** `total_chats` per user computed via `SELECT COUNT(*) FROM chat_sessions WHERE user_id = users.id`
- **Revenue:** based on `subscriptions.amount` where `status='active'`; MRR = current month activated subs
- **Lawyer/Subscription endpoints:** kept in backend admin router; removed from frontend tabs

---

### Phase 17 — Vision AI for Document Assistant ✅ COMPLETE
| Feature | Status | Notes |
|---|---|---|
| Backend endpoint `POST /api/documents/analyze-image` | ✅ | `backend/app/routers/documents.py`; multipart: `image` + `language` form fields |
| Image validation | ✅ | JPG/JPEG/PNG/WEBP/GIF accepted; max 5 MB; 415 on bad ext, 413 on oversize |
| Claude vision API call | ✅ | `claude-opus-4-5`; base64 image + system prompt; 2000 max_tokens |
| Document type detection | ✅ | Keyword match on Claude response: court_notice/contract/land_deed/legal_form/id_document/other |
| Dual language prompts | ✅ | `_VISION_PROMPT_BN` (Bengali) / `_VISION_PROMPT_EN` (English); selected by `language` form param |
| `analyzeImage()` in api.ts | ✅ | `frontend/lib/api.ts`; Bearer token from localStorage; returns `ImageAnalysisResult` |
| Tab system on /document page | ✅ | "📄 ডকুমেন্ট বিশ্লেষণ" (existing) + "🖼️ ছবি বিশ্লেষণ" (new) |
| Image upload zone | ✅ | Drag & drop or click; violet icon; image/jpeg,image/png,image/webp,image/gif |
| Image preview | ✅ | `URL.createObjectURL`; max-h-72; animate-pulse during loading; thumbnail in result |
| Document type badge | ✅ | Color-coded: red/blue/green/purple/orange/gray; bilingual labels |
| Markdown renderer | ✅ | Inline `MarkdownContent` component; handles `## headers`, `**bold**`, paragraphs |
| Copy + New Analysis buttons | ✅ | clipboard copy with ✓ feedback; reset clears state and revokes object URL |
| Translation keys | ✅ | 9 new keys added to `document` section in both bn/en |

- **Endpoint:** `POST /api/documents/analyze-image` — no auth required (same as existing analyze)
- **Vision model:** `claude-opus-4-5` (supports image input via base64)
- **Media type detection:** extension → `image/jpeg`/`image/png`/`image/webp`/`image/gif` literal for Anthropic SDK
- **Object URL lifecycle:** revoked on component unmount and on new image selection (`useEffect` cleanup)
- **Existing PDF/DOCX analysis:** unchanged; preserved as Tab 1

---

### Phase 18 — AI Agent Tool Calling ✅ COMPLETE
| Feature | Status | Notes |
|---|---|---|
| Agent tools service (`backend/app/services/agent_tools.py`) | ✅ | 6 tools: search_laws, get_law_details, search_legal_templates, calculate_legal_deadline, get_court_info, check_legal_eligibility |
| Agent router (`backend/app/routers/agent.py`) | ✅ | `POST /api/agent/chat`; Anthropic tool_use agentic loop; max 5 iterations |
| Tool definitions (Anthropic format) | ✅ | All 6 tools with full `input_schema` |
| System prompts | ✅ | `_SYSTEM_BN` (Bengali) + `_SYSTEM_EN` (English) |
| Agent page (`/agent`) | ✅ | `frontend/app/agent/page.tsx`; dark purple gradient hero; 4 capability cards |
| Tool badges in UI | ✅ | Collapsible tool panels showing name → result summary; expandable JSON |
| Suggested questions | ✅ | 4 Bengali + 4 English questions rendered as clickable buttons |
| Chat history | ✅ | `conversation_history` array passed to each subsequent request |
| NavBar "🤖 এজেন্ট" link | ✅ | Desktop + mobile menu; after ডকুমেন্ট |
| Translations | ✅ | `agent` section added to both bn/en in `translations.ts` |
| Model | ✅ | `claude-opus-4-5` |

- **Tool 1 `search_laws`:** ILIKE keyword search on sections + acts joined; returns up to 5 results with content preview (600 chars)
- **Tool 2 `get_law_details`:** Fetches act by ILIKE name match; returns id, year, category, total_sections count
- **Tool 3 `search_legal_templates`:** Hardcoded 14 templates across 5 categories; keyword match on name/description
- **Tool 4 `calculate_legal_deadline`:** 7 event types (appeal, limitation_contract, limitation_tort, cheque_dishonor, labor_complaint, consumer_complaint, land_dispute); returns deadline_date + days_remaining + legal_basis
- **Tool 5 `get_court_info`:** 8 court types hardcoded (supreme, high_court, district, sessions, magistrate, labour, family, administrative)
- **Tool 6 `check_legal_eligibility`:** 3 action types: bail (bailable vs non-bailable), appeal (30-day limit), legal_aid (≤10,000 BDT/month)
- **Agentic loop:** Claude decides which tools to call; results fed back; up to 5 iterations; `stop_reason == "end_turn"` terminates

---

### Phase 19 — Better RAG ✅ COMPLETE (including post-session bug fixes)
| Feature | Status | Notes |
|---|---|---|
| `query_expander.py` (new) | ✅ | SYNONYM_MAP for ILIKE + `_FTS_EXTRAS` for ts_rank; `expand_query()` + `fts_core_terms()` |
| Hybrid RRF search in `query_router.py` | ✅ | Vector (top-20) + keyword ILIKE (top-20) → RRF formula `1/(rank+60)` → re-rank → top-5 |
| Re-ranking bonuses | ✅ | +0.3 exact phrase match, +0.2 law name match, +0.1 year ≥ 2000; all items considered (not just top 10) |
| `_build_keyword_sql()` dynamic ILIKE | ✅ | Searches `content_en`+`content_bn`; ordered by `ts_rank(..., 1)` (length-normalised FTS) |
| Context window optimization | ✅ | Per-section: 12 000 chars (paragraph extraction if oversized); total: 48 000 chars |
| Metadata header format | ✅ | `আইনের নাম: {law}` / `ধারা: {section} - {title}` / content / relevance score |
| Context injected into system prompt | ✅ | `_SYSTEM_PROMPT_TEMPLATE_BN/EN.format(context=...)` — replaces static prompt |
| Improved Bengali system prompt | ✅ | 6 explicit rules; "only use provided legal sections" constraint |
| `citations` SSE event | ✅ | `{"type":"citations","data":[{law_name,section,title,relevance}]}` after streaming |
| Frontend `CitationSource` type | ✅ | `types/index.ts`; `SSECitationsEventSchema` added to `SSEEventSchema` |
| Store `setMessageCitations` action | ✅ | `store.ts`; ChatMessage.citations field |
| api.ts citations handler | ✅ | `case 'citations': handlers.onCitations?.(event.data)` |
| ChatInterface wired | ✅ | `onCitations: (d) => setMessageCitations(assistantId, d)` |
| MessageBubble collapsible citations | ✅ | `CitationsSection` component; pill badges with law name, ধারা, title, relevance% |
| **BUG FIX: vector failure transaction abort** | ✅ | `await db.rollback()` after PG error so keyword leg can run in fresh transaction |
| **BUG FIX: section_number extraction** | ✅ | SQL UPDATE extracted section numbers from inline content (`^\d+[A-Za-z]?\.`) — 3,233 sections updated |
| **BUG FIX: act title "1" prefix** | ✅ | `regexp_replace(title_en, '^\d+', '')` fixed 7 acts (Penal Code etc.) |
| **BUG FIX: FTS term quality** | ✅ | `fts_core_terms()` uses `_FTS_EXTRAS` for cross-concept terms (e.g. "punishment theft") not same-concept synonyms |

- **RRF intents:** FIND_LAW, EXPLAIN_RIGHTS, CHECK_PROCESS, FIND_SECTION fallback
- **Unchanged:** FIND_CASE (case vector), COMPARE_LAWS (dual vector), GET_DOCUMENT (FTS), GENERAL_INFO/UNKNOWN (no DB)
- **Keyword fallback:** unfiltered ILIKE if category-filtered returns 0; unfiltered vector if both legs empty
- **_MIN_SCORE:** lowered from 0.60 to 0.30 for better vector recall once embeddings are generated
- **`stream_with_document()`** also gets query expansion + context optimization; system prompt unchanged (document flow)
- **Pipeline passes `fts_terms` through:** `rag_pipeline.py` → `route()` → `_rrf_search()` → `_build_keyword_sql()` → ts_rank

---

### Phase 20 — NOT STARTED
| Option | Notes |
|---|---|
| Production deployment prep | Vercel (frontend) + Railway (backend) + real SSLCommerz creds + env setup |

---

*Last updated: 2026-06-11 (Phase 19 RAG bug fixes complete) | Project: AI Lawyer Bangladesh SaaS*
