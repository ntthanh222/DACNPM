# Feature Specification: CyberSec Assistant Platform

**Feature Branch**: `[001-cybersec-assistant]`

**Created**: 2026-07-18

**Status**: Draft

**Input**: User description: ".\README.md"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Security Chatbot with Hybrid Intention Routing (Priority: P1)

As a platform user, I want to ask security-related questions to an AI chatbot so that I can get immediate, intelligent assistance for general conversation or advanced technical issues.

**Why this priority**: This is the core interface of the CyberSec Assistant. It provides interactive AI-powered security advice, routing requests appropriately between a conversational router and deep technical retrieval-augmented generation.

**Independent Test**: Can be tested by sending general messages (e.g., greetings) and verifying the conversational router handles them, and sending complex security queries (e.g., "What is a SQL injection?") and verifying the system retrieves context and replies with accurate security info.

**Acceptance Scenarios**:

1. **Given** the chat interface is loaded, **When** the user sends a message "Hi, how are you?", **Then** the chatbot responds with a standard conversational greeting.
2. **Given** the chat interface is loaded, **When** the user asks "How do I prevent Cross-Site Scripting (XSS)?", **Then** the system retrieves security documents from the knowledge base, enhances the context, routes the query to the language model, and responds with a detailed explanation in Vietnamese.

---

### User Story 2 - CVE Lookup & Vietnamese Translation (Priority: P2)

As a security analyst, I want to query a specific CVE identifier to view detailed vulnerability details and remediation steps translated into Vietnamese.

**Why this priority**: Allows Vietnamese IT administrators and developers to quickly understand CVE hazards and apply security patches without language barriers.

**Independent Test**: Can be tested by entering a CVE ID (e.g., `CVE-2021-44228`) and checking that the system displays details and fix recommendations in Vietnamese.

**Acceptance Scenarios**:

1. **Given** the CVE lookup tool is open, **When** the user searches for `CVE-2021-44228`, **Then** the system checks the database, uses the language model to translate description details if not cached, and displays the details and remediation instructions in Vietnamese.
2. **Given** a user inputs an invalid CVE ID format, **When** they submit the query, **Then** the system displays a user-friendly error message indicating the invalid format.

---

### User Story 3 - URL Phishing & Safety Scanner (Priority: P2)

As a user, I want to scan a URL link to verify if it is safe, phishing, or contains malware.

**Why this priority**: Helps prevent users from falling victim to phishing emails or malicious links by providing quick security verdicts.

**Independent Test**: Can be tested by entering a clean URL and a known malicious URL, then checking if the system correctly identifies and reports the safety status and risk score.

**Acceptance Scenarios**:

1. **Given** the URL scanner input, **When** the user submits a suspicious URL (e.g., `http://secure-bank-login-update.com/reset`), **Then** the system flags local heuristic violations and queries the external security scanner, displaying a high-risk percentage warning.
2. **Given** the URL scanner input, **When** the user submits a safe URL (e.g., `https://google.com`), **Then** the system displays a clean safety status with 0% risk detection.

---

### User Story 4 - Security News Aggregator Feed (Priority: P3)

As a user, I want to view a dashboard with aggregated security news from multiple sources to stay informed about current cyber threats.

**Why this priority**: Provides supplementary value to users by keeping them updated on the security landscape within the same platform.

**Independent Test**: Can be tested by opening the news dashboard and ensuring a populated list of security articles from designated portals is shown.

**Acceptance Scenarios**:

1. **Given** the crawler has run, **When** the user opens the news section, **Then** they see a chronological feed of recent security news headlines, summaries, and links to source articles.

---

### Edge Cases

- **External API Failures**: If the external safety scanner or language model service is down, the system should gracefully fail back to local checks (heuristics) or cache, displaying clear warnings without crashing.
- **Intent Routing Fallback**: If the conversational router cannot classify the intent with high confidence, the system should route the query to the language model as a fallback or prompt the user for clarification.
- **Duplicate CVE Requests**: If a CVE is requested multiple times, the system should retrieve the translated info from the cache or database instead of invoking the translation API repeatedly.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST classify user inputs using a natural language understanding module.
- **FR-002**: System MUST route technical queries to the language model with retrieval-augmented context from a vector database (RAG).
- **FR-003**: System MUST support CVE lookup and translate details to Vietnamese using the language model if not already translated.
- **FR-004**: System MUST perform URL safety analysis using local heuristics (domain check, character checks) and an external security scanning service.
- **FR-005**: System MUST cache scanned URLs and CVE lookup results for rapid subsequent retrieves.
- **FR-006**: System MUST run an automated background task to crawl new security articles from designated portals.
- **FR-007**: System MUST allow guest access to chatbot and scanner functions with daily rate limits, while registered users have unlimited access.
- **FR-008**: System MUST allow users to customize their news feed by filtering by category (e.g., vulnerabilities, news, malware) or searching by keyword.

### Key Entities *(include if feature involves data)*

- **User**: Represents a user account. Attributes: ID, email, password hash, role, created date.
- **ChatSession**: Represents an active or historical conversation session. Attributes: Session ID, User ID, title, created timestamp.
- **ChatMessage**: Represents an individual message in a chat. Attributes: Message ID, Session ID, sender type (user/system), content, timestamp.
- **CVECache**: Represents cached CVE details. Attributes: CVE ID, English details, Vietnamese translated details, remediation steps, cached timestamp.
- **SecurityNews**: Represents crawled security news articles. Attributes: ID, title, summary, source, URL, publish date, crawled date.
- **URLScanResult**: Represents the scan history of a URL. Attributes: URL, risk score, heuristics flags, external response details, scanned date.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Chatbot responses routed to conversational NLU respond in under 1.5 seconds, and queries routed to the language model (RAG) respond in under 4.0 seconds on average.
- **SC-002**: URL scan results are calculated and rendered to the user within 2.5 seconds.
- **SC-003**: Background crawler executes successfully at least once every 24 hours, populating the database with at least 5 new articles if available.
- **SC-004**: Caching reduces response time for identical CVE queries and URL scans by at least 80%.
- **SC-005**: The platform supports at least 50 concurrent active user connections without system degradation.

## Assumptions

- Users have a stable internet connection for accessing the web interface and for external service calls.
- API keys for external services are valid and have sufficient quota.
- User accounts and chat histories are stored securely in a relational cloud database.
- Default interface language is Vietnamese, and queries can be asked in English or Vietnamese.
- Guests can access chatbot and scanning services up to a daily limit of 10 queries, while authentication removes these limitations.
- News aggregation serves a global feed with shared category filtering, with no user-specific feed subscriptions required.
