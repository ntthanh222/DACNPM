# Function catalog

Generated from the current source surface. `CÓ TEST` is evidence status, not an assumption.

| ID | Module | Chức năng | Role | Frontend route | API | Database | Docker service | Ưu tiên | Có test |
|---|---|---|---|---|---|---|---|---|---|
| AUTH-001 | Authentication | Login/logout/session | User | /login.html | auth routes | users | backend/frontend | Critical | NOT TESTED |
| AUTH-002 | Authentication | Registration and password validation | User | /login.html | auth routes | users | backend/frontend | High | NOT TESTED |
| AUTH-003 | Authentication | Token/permission rejection | All | n/a | deps | users | backend | Critical | NOT TESTED |
| DASH-001 | Dashboard | Overview and security metrics | User | /dashboard.html | stats/system | stats | backend/frontend | Critical | NOT TESTED |
| USER-001 | User | Profile and account settings | User | dashboard | profiles | profiles | backend/frontend | High | NOT TESTED |
| USER-002 | User | Chat and history isolation | User | /pages/assistant/chat.html | chat/chatbot | chat_history | backend/frontend/redis | Critical | NOT TESTED |
| URL-001 | URL analysis | Safe/suspicious URL analysis | User | /pages/url-check/index.html | chatbot/url scanner | security_scans | backend | Critical | NOT TESTED |
| URL-002 | URL analysis | SSRF/private-network rejection | User | /pages/url-check/index.html | url scanner | n/a | backend | Critical | NOT TESTED |
| PASSWORD-001 | Password | Strength and pattern checks | User | dashboard | client-side | n/a | frontend | High | NOT TESTED |
| NEWS-001 | News | Read security news | User | /pages/news/index.html | news | security_news | backend/frontend | Medium | NOT TESTED |
| ADMIN-001 | Admin | User management | Admin | /pages/admin.html | admin/user-management | users | backend/frontend | Critical | NOT TESTED |
| ADMIN-002 | Admin | News moderation | Admin | /pages/admin.html | admin/news-moderation | security_news | backend/frontend | High | NOT TESTED |
| ADMIN-003 | Admin | Crawler control and logs | Admin | /pages/admin.html | admin/crawler-control | crawler | crawler/redis | High | NOT TESTED |
| ADMIN-004 | Admin | System monitoring | Admin | /pages/admin.html | admin/system-monitoring | metrics/cache | prometheus/grafana | High | NOT TESTED |
| RAG-001 | RAG | Upload, index and delete document | Admin | /pages/admin.html | admin/rag-operations | chroma | chromadb | High | NOT TESTED |
| AI-001 | AI | Chat response and streaming | User | /pages/assistant/chat.html | chatbot/chat | chat_history | rasa/backend | Critical | NOT TESTED |
| AI-002 | AI | Safety, hallucination and cross-user isolation | User | /pages/assistant/chat.html | chatbot | chat_history | rasa/backend | Critical | NOT TESTED |
| CRAWLER-001 | Crawler | Run and schedule crawler | Admin | /pages/admin.html | crawler scheduler | security_news | crawler/redis | High | NOT TESTED |
| MONITORING-001 | Monitoring | Health, metrics and scrape target | SRE | n/a | /health,/metrics | n/a | prometheus/grafana | High | NOT TESTED |
| DOCKER-001 | Docker | Build, health, persistence and restart | SRE | n/a | compose | all | compose | Critical | NOT TESTED |

Total catalogued features: **20**

Status vocabulary: PASS, FAIL, BLOCKED, NOT IMPLEMENTED, NOT TESTED, FLAKY, STABLE.
