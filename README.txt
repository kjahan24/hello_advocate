


# হ্যালো এ্যাডভকেট (Hello Advocate)
### Bangladesh's First AI-Powered Legal SaaS Platform

---

## Overview

Hello Advocate is a full-stack AI-powered legal assistance platform for Bangladesh. Users can ask legal questions in Bengali or English and get instant answers backed by 1,600+ Bangladesh laws and 46,868+ legal sections — with source citations.

---

## Features

- **AI Legal Chatbot** — Hybrid RAG pipeline with intent detection, Bengali/English support, and real-time SSE streaming
- **AI Agent** — Autonomous tool-calling agent with 6 legal tools (law search, deadline calculator, court info, eligibility checker)
- **Vision AI** — Upload images of court notices, contracts, or land deeds for instant legal analysis
- **Document Assistant** — Upload PDF/DOCX contracts for AI-powered risk analysis and clause extraction
- **Legal News Feed** — Aggregates Bangladesh legal news from 3 Bengali newspapers with Redis caching
- **Lawyer Marketplace** — Find and connect with verified Bangladesh lawyers
- **Court Case Tracker** — Track hearing dates with automated email reminders
- **Multi-language** — Full Bengali and English UI toggle
- **Subscription Plans** — Free / Pro (৳499/month) / Law Student (Free) with SSLCommerz payment
- **Admin Dashboard** — User management, revenue analytics, activity tracking
- **Mobile Responsive** — Optimized for all screen sizes

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 14, Tailwind CSS, TypeScript |
| Backend | FastAPI, Python |
| Database | PostgreSQL + pgvector |
| Cache | Redis |
| AI Models | claude-opus-4-5 (Anthropic), text-embedding-3-small (OpenAI) |
| Payment | SSLCommerz (bKash, Nagad, Rocket) |
| Infrastructure | Docker Compose |

---

## AI Architecture

**RAG Pipeline**
- 46,868 Bangladesh law sections embedded with `text-embedding-3-small`
- Hybrid search: vector similarity (pgvector) + full-text search (PostgreSQL tsvector)
- Reciprocal Rank Fusion (RRF) re-ranking
- Bengali legal synonym expansion (20-term map)
- Source citations returned after every response

**Intent Detection**
- Rule-based keyword matching
- 9 legal intents × 12 legal categories
- Routes queries to optimized search strategies

**Agent Tool Calling**
- 6 tools via Anthropic tool-use API
- `search_laws`, `get_law_details`, `search_legal_templates`
- `calculate_legal_deadline`, `get_court_info`, `check_legal_eligibility`

**Vision AI**
- Image upload (JPG/PNG/WEBP, max 5MB)
- Base64 encoding → multimodal AI analysis
- Document type detection: court notice, contract, land deed, legal form, ID

---

## Project Structure

```
ai-lawyer/
├── backend/          # FastAPI backend
│   ├── app/
│   │   ├── routers/  # API endpoints
│   │   ├── services/ # RAG, agent, email services
│   │   └── models/   # Database models
│   └── requirements.txt
├── frontend/         # Next.js frontend
│   ├── app/          # Pages
│   └── components/   # UI components
├── docker-compose.yml
└── .env.example
```

---

## Getting Started

**Prerequisites:** Docker Desktop, Git

```bash
# Clone the repository
git clone https://github.com/kjahan24/hello_advocate.git
cd hello_advocate

# Copy environment variables
cp .env.example .env
# Fill in your API keys in .env

# Start all services
docker compose up -d

# Visit
http://localhost:3000
```

---

## Environment Variables

See `.env.example` for all required variables including:
- `ANTHROPIC_API_KEY`
- `OPENAI_API_KEY`
- `DATABASE_URL`
- `SSLCOMMERZ_STORE_ID`
- `SMTP_USER`

---

## Data

The platform uses 1,609 Bangladesh laws and 46,868 sections scraped from [bdlaws.minlaw.gov.bd](https://bdlaws.minlaw.gov.bd) and stored in PostgreSQL with pgvector embeddings.

---

## License

This project was built as part of an AI SaaS development course.
```

GitHub-এ **"Add a README"** click করুন → সব paste করুন → **"Commit changes"** click করুন! 😊                                           


