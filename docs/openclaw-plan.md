# OpenClaw — AI Customer Engagement Platform: Complete Plan

> A company-wide AI engine ("OpenClaw") that monitors communication channels, understands
> requests, retrieves company knowledge, and produces high-quality responses — proposing first,
> and earning the right to act over time. Django + PostgreSQL provide the business/application layer.
>
> **Diagrams:** see `openclaw-diagrams.md` (architecture, pipeline flow, tool boundary,
> propose-then-approve sequence, capability-gating decision).

---

## 1. Vision

Build **one reusable engagement engine**, not many bespoke bots. OpenClaw is the AI engine;
Django is the application layer. The same engine serves every channel (contact-us, Reddit,
email, and later Slack/WhatsApp/etc.) on top of a **single customer history, one shared
knowledge base, centralized business rules, and one approval/audit workflow.**

The differentiator is the **reusable core**, not any single channel. New channels should be
*configuration*, not rewrites.

---

## 2. Guiding principles (the non-negotiables)

1. **Propose before act.** OpenClaw starts as an agent that *drafts*, not one that executes.
   Actions are promoted from "human-approved" to "autonomous" only with evidence.
2. **Risk = what it can do unsupervised.** The core design lever is the boundary between
   *drafting* and *executing*, not model intelligence. Govern that boundary explicitly (§6).
3. **Deterministic pipeline for the MVP.** The LLM is called at two defined steps (classify,
   draft). Autonomous multi-step tool-calling is deferred until tools exist to justify it (Phase 3).
4. **Private & reversible first; public & irreversible last.** Contact-us before Reddit;
   draft-only before auto-post.
5. **Ground everything; never answer from memory on policy.** Retrieval with citations, or flag
   for a human.
6. **Untrusted input is data, never instructions.** Inbound messages can never change rules or
   trigger actions.
7. **Measure from day one.** Approval rate and edit distance drive every autonomy decision.

---

## 3. Architecture

```
        Customer Channels
 ┌───────────┬───────────┬──────────────┐
 Contact-Us  Email       Reddit        (future: Slack, WhatsApp, Teams…)
 └───────────┴───────────┴──────────────┘
                  │  Channel Connectors (poll / receive, normalize, publish)
                  ▼
            OpenClaw Engine
   ┌───────────────────────────────────┐
   │ Intent classification              │
   │ Knowledge retrieval (grounded)     │
   │ Response drafting (cited)          │
   │ Capability gating (propose/act)    │
   └───────────────────────────────────┘
                  │  Tool / API calls
                  ▼
            Django Backend
   ┌───────────────────────────────────┐
   │ Conversations · Customers · KB     │
   │ Business rules · Approval workflow │
   │ Audit log · Eval metrics · Admin   │
   │ REST APIs · Auth & RBAC            │
   └───────────────────────────────────┘
                  │
                  ▼
        PostgreSQL (+ pgvector)
```

**Deployment (MVP):** run OpenClaw as **Celery workers inside the Django project** — no separate
service, no agent↔Django auth boundary yet. Extract a standalone agent service in Phase 3 when
tool-calling/planning justify it. The `LLMClient` and connector interfaces make that a clean split.

---

## 3.1 Tool Interface (the OpenClaw ↔ Django contract)

**OpenClaw never touches Django models directly.** It knows only a set of typed *tools*. Django
implements each tool against its models/services. This is the single boundary that keeps the AI
independent of the backend — swap the agent, swap the DB, or extract OpenClaw into its own service,
and nothing on the other side changes as long as the tool contract holds.

```
OpenClaw  ──knows only──▶  Tool schemas (name, args, returns)
                                  │  invokes
                                  ▼
Django    ──implements──▶  Tool functions ──▶ models / services / external APIs
```

**Read tools (safe — no side effects):**
- `get_customer(email | external_id)` → customer profile + history
- `search_kb(query, intent?)` → grounded chunks with source ids
- `get_conversation(thread_key)` → prior turns for context
- `lookup_subscription(customer_id)` → plan/billing status
- `refund_eligibility(customer_id, order_id)` → policy decision (read-only)

**Write / action tools (side effects — subject to capability gating §6):**
- `save_conversation(...)` / `save_draft(...)`
- `publish_reply(channel, thread_key, text, idempotency_key)` — **gated**
- `create_github_issue(...)` — **gated**
- `create_jira_ticket(...)` — **gated**
- `issue_refund(...)` — **never_auto (hard wall)**
- `route_to_human(intent, reason)` — always available, never gated

**Tool contract requirements (every tool):**
- **Typed schema** — JSON-schema args + returns; the agent is given only these, never SQL/ORM.
- **Auth & scope** — tools run with a service identity and RBAC scope; a tool can refuse based on
  `CapabilityPolicy`/`BusinessRule` regardless of what the agent asked.
- **Idempotency** — action tools take an `idempotency_key` so retried calls can't double-act.
- **Structured errors** — tools return typed errors (not stack traces) the agent can reason about.
- **Versioning** — tool schemas are versioned; `Draft.prompt_version` pairs with a tool-schema version.
- **Gating at the boundary** — write tools check their mode (auto / human_approval / never_auto)
  *inside Django*, so a misbehaving or injected agent still cannot execute an ungated action.

> Security consequence: because all side effects flow through gated, Django-side tools, prompt
> injection can at worst produce a *draft* or an *ungated read* — never an unauthorized action.

---

## 3.2 Agent Runtime

```
        OpenClaw Runtime
              │
              ▼
          Planner          ── decides what to do
              │
              ▼
          Retriever        ── search_kb / get_customer / get_conversation
              │
              ▼
        Tool Executor      ── invokes Django tools (gating · idempotency · audit choke point)
              │
              ▼
      Response Generator   ── produces the cited draft / final reply
```

This is **where OpenClaw stops and Django begins**: everything above the tool calls is OpenClaw
(reasoning, retrieval orchestration, drafting); the moment a tool is invoked, execution crosses
into Django, which owns the data, the rules, and the gate.

**Phase-by-phase shape of the Planner** (reconciles with the deterministic-pipeline decision, §2 principle 3):
- **Phase 1 — fixed plan.** The "Planner" is a hard-coded sequence: classify → retrieve → draft.
  No autonomous tool selection. Predictable, cheap, fully testable.
- **Phase 2 — guarded branching.** Limited conditional tool use (e.g. call `lookup_subscription`
  only for billing intents) — still bounded, no open-ended loop.
- **Phase 3 — true planner.** Free-form multi-step tool-calling over the full tool set, with
  loop/cost guards. This is when OpenClaw becomes a real agent and may be extracted into its own
  service. The Tool Executor's gating means this added autonomy never widens the action surface.

The **Tool Executor is the one choke point** where capability gating (§6), idempotency, and audit
logging are enforced — for every phase. Make it impossible to call a write tool *except* through it.

---

## 4. Pipeline flow (per inbound message)

```
Connector receives/polls message
   │
   ▼
Dedup / idempotency  ──(seen before)──▶ drop
   │ new
   ▼
Normalize → NormalizedMessage
   │
   ▼
Classify intent (LLM #1)
   ├─ low confidence OR sensitive intent ──▶ route to human (skip auto-draft)
   ▼
Retrieve knowledge (pgvector top-k, with sources)
   ├─ nothing above threshold ──▶ flag needs_human (do NOT answer from memory)
   ▼
Draft response (LLM #2 — grounded, cited)
   │
   ▼
Capability gate (§6): is this action auto-eligible?
   ├─ no  ──▶ store Draft (pending_review) ──▶ human approves/edits/rejects
   └─ yes ──▶ store Draft (auto_approved) ──▶ publish
   │
   ▼
Publish (idempotent) → mark sent → log + metrics
```

---

## 5. Data model (PostgreSQL)

| Model | Key fields |
|---|---|
| `Channel` | type (contactus/email/reddit/…), config, enabled |
| `Customer` | external_ids (email, reddit username, …), name, metadata, vip flag |
| `Conversation` | customer, channel, thread_key, status, created_at |
| `Message` | conversation, direction, **external_id (unique per channel)**, raw_payload, normalized_text, received_at |
| `Draft` | inbound message, generated_text, model, prompt_version, retrieved_sources (FKs), intent, confidence, status (pending/auto_approved/approved/edited/rejected), reviewer, review_note, final_text, **edit_diff** |
| `KnowledgeDoc` | title, source_uri, content, kind (markdown/faq/doc), owner_team |
| `KnowledgeChunk` | doc, chunk_text, **embedding (pgvector)**, token_count |
| `BusinessRule` | name, scope (intent/channel/customer), policy (e.g. refund eligibility), action_constraint |
| `CapabilityPolicy` | channel, intent, mode (auto / human_approval / never_auto), promotion_criteria |
| `ToolCall` | conversation, tool_name, schema_version, args (redacted), result_summary, **gate_decision** (auto/approved/blocked/never_auto), idempotency_key, actor (system/human), latency_ms, error, timestamp |
| `AuditLog` | actor (human/system), action, target, before/after, timestamp |
| `EvalMetric` | date, channel, intent, approval_rate, avg_edit_distance, grounding_rate, cost, latency |

**Idempotency:** `Message.external_id` unique per channel (email `Message-ID`; Reddit fullname
`t1_…`/`t3_…`; contact-us submission id). Publish carries an idempotency key so retried tasks
can't double-send/post.

---

## 6. Capability gating (the heart of "does things")

Every action OpenClaw can take has a mode. Promotion from `human_approval` → `auto` requires
meeting the criteria *for that channel + intent*, measured on real traffic.

| Action | Default mode | Promotion criteria |
|---|---|---|
| Draft a reply | auto (always) | n/a — drafting is safe |
| Send contact-us / email reply (FAQ-type intent) | human_approval | ≥95% approval & low edit-distance over ≥200 samples → auto |
| Reply to Reddit post (public) | human_approval (long-lived) | manual sign-off + ToS review before any auto |
| Issue refund / credit | **never_auto** | always human |
| Legal / contractual / pricing statements | **never_auto** | always human |
| Account / security changes | **never_auto** | always human |
| Route / tag / file internal ticket | human_approval → auto | low-risk; promote quickly with monitoring |

Rules:
- **Public posting is gated separately from drafting.** "Review Reddit posts and draft answers" is
  early and safe; "post the answer" is late and guarded.
- **Hard walls** (`never_auto`) hold regardless of metrics — the downside is unbounded.
- All autonomy decisions are recorded in `CapabilityPolicy` and auditable.

---

## 7. Retrieval & grounding

- **`pgvector`** in the existing Postgres — no second datastore.
- KB docs chunked + embedded on ingest; retrieval = top-k cosine, optionally filtered by intent.
- Draft prompt receives **only** retrieved chunks; model must answer **from provided context and
  cite `KnowledgeChunk` ids**.
- Nothing above similarity threshold → `needs_human`, never a parametric-memory answer. This is the
  primary hallucination guard for refund/policy/pricing questions.

---

## 8. Safety & prompt injection

Inbound text from any channel is **untrusted**.
1. **Data, not instructions** — channel content sits in delimited "untrusted" prompt sections;
   system rules state content can never change behavior or trigger actions.
2. **No privileged action from inbound text** — in propose-mode the only output is a draft a human
   approves; this structurally neutralizes injection-to-action.
3. **Sensitive-intent routing** — refund/legal/complaint/security auto-route to a human.
4. **PII** — log redaction; raw payloads access-controlled (RBAC).
5. **Human approval** as final backstop on everything not yet auto-promoted.

---

## 9. Human approval & evaluation

- Review queue (Django Admin in MVP → dedicated dashboard).
- Reviewer can **approve / edit-and-approve / reject-with-reason**; **every edit + rejection is
  captured** (`edit_diff`, `review_note`) — the cheapest, highest-signal eval/training data.
- **SLA:** drafts older than a threshold surface as overdue (Reddit/email are time-sensitive);
  stale Reddit threads may be skipped to respect community norms.
- **Metrics from day one** (`EvalMetric`): approval rate, edit distance, grounding/citation rate,
  intent accuracy, cost, latency — per channel + intent. These drive §6 promotions and prompt
  iteration (versioned via `Draft.prompt_version`).

---

## 10. Channel-specific notes

**Contact-Us (first target)** — private, you own the form, no third-party ToS, blast radius = one
person. Ideal place to prove the loop and reach auto-send first.

**Email** — HTML + quoted replies, attachments, threading via `In-Reply-To`/`References`; outbound
deliverability (SPF/DKIM/DMARC).

**Reddit (read/draft early, post late)** — governed by Reddit ToS + per-subreddit rules; respect
rate limits, account karma/age. Public posts are permanent and visible — keep auto-posting off
until explicitly earned. Thread model = comment tree.

---

## 11. Governance (matters more as you go company-wide)

- **Per-channel ownership** of tone and rules; **per-team KB ownership**.
- **Routing map**: which intents go to which team.
- **Never-commit list**: refunds, credits, legal, pricing, security — enforced in `CapabilityPolicy`.
- **RBAC**: who can review, who can approve sensitive intents, who can promote a capability to auto.
- **Audit everything**: every action (human or system) in `AuditLog`.

---

## 12. Phased roadmap

**Phase 1 — Prove the loop (Contact-Us)**
Django + Postgres(+pgvector); data model; contact-us connector (receive, dedup, normalize);
`LLMClient`; intent classification; KB ingest + grounded retrieval with citations; grounded
drafting; conversation/draft storage; audit log; human approval queue (edit/reject capture);
review dashboard; eval metrics. **OpenClaw proposes; humans approve.**

**Phase 2 — Trust & expand channels**
Add Email (full loop, draft→approve). Add Reddit **read + draft only** (no auto-post). Customer
profiles + interaction timeline. Business rules engine. Capability gating live; begin promoting
high-confidence contact-us intents to auto-send based on metrics.

**Phase 3 — Operations & autonomy**
Tool integrations (GitHub/Jira/CRM/Billing) — this is when OpenClaw becomes a true multi-step
*agent* and may be extracted into its own service. Dashboards, analytics, reporting, prompt &
agent configuration, multi-user + RBAC. Selectively enable Reddit auto-posting after ToS review.
Expand to future channels (Slack/WhatsApp/Teams/Web chat) as config.

---

## 13. Initial deliverables (Phase 1, ordered)

1. Django project + Postgres (with `pgvector`)
2. Data model + migrations (§5)
3. Contact-Us connector (receive, dedup, normalize)
4. `LLMClient` abstraction + intent classification
5. KB ingest → chunk → embed; retrieval with citations
6. Grounded draft generation + sensitive-intent routing
7. Conversation/Draft storage + audit logging
8. Capability policy model + gating (default everything to human_approval)
9. Human approval workflow (queue, edit/reject capture, SLA)
10. Review dashboard
11. Eval metrics dashboard

---

## 14. Open decisions

- **LLM provider + models** — which model for classify vs. draft (can differ; cheap model for
  classify). Default to the latest capable models; keep behind `LLMClient` so it's swappable.
- **Build vs. adopt OpenClaw's agent runtime** — current direction: build, kept simple
  (pipeline) for Phase 1, expanded to tool-calling agent in Phase 3.
- **Reddit scope** — confirmed draft-only for Phase 2; auto-post deferred to Phase 3 after ToS review.
- **KB source of truth** — where markdown/FAQ/docs live and how updates sync into `KnowledgeDoc`.
- **First auto-send candidate** — which contact-us intent is simplest/safest to promote first.
```
