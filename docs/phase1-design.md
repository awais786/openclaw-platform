# AI Customer Engagement Platform — Phase 1 Design (Revised)

> Revision of the MVP scope in *AI Customer Engagement Platform - Implementation Plan*.
> Incorporates review fixes: pipeline-vs-agent decision, grounded retrieval, prompt-injection
> handling, idempotency, and evaluation moved into Phase 1.

## 1. Goal & non-goals

**Goal:** A reliable pipeline that ingests Email and Reddit messages, classifies intent,
retrieves grounded company knowledge, drafts a response, and publishes it **only after human
approval**. Optimize for predictability, auditability, and a fast review loop.

**Non-goals for Phase 1:**
- Autonomous multi-step tool-calling / planning (deferred to Phase 2 once GitHub/Jira/CRM tools exist).
- Auto-send without human approval.
- Additional channels beyond Email + Reddit.

## 2. Key decision: deterministic pipeline, not an autonomous agent

Phase 1 is a **deterministic RAG pipeline with a human gate**, orchestrated by Django + Celery.
The LLM is invoked at exactly two well-defined steps — **classify** and **draft** — rather than
running a free-form agent loop.

Rationale: predictable cost, easy to test and eval, simple to debug, and no loop/runaway-cost
control needed. The "agent" framing (planning, tool-calling) is reintroduced in Phase 2 when
tool integrations make multi-step reasoning genuinely useful. The model provider is abstracted
behind an `LLMClient` interface so the pipeline is provider-agnostic.

## 3. Pipeline flow

```
Channel poller (Celery beat)
   │  fetch new messages
   ▼
Dedup / idempotency check ──(already seen)──▶ drop
   │ new
   ▼
Normalize → NormalizedMessage
   │
   ▼
Classify intent (LLM call #1)
   │
   ├─ low confidence / sensitive intent ──▶ route to human, skip auto-draft
   │
   ▼
Retrieve knowledge (pgvector, top-k with sources)
   │
   ▼
Draft response (LLM call #2, grounded + citations)
   │
   ▼
Store Conversation + Draft (status = pending_review)
   │
   ▼
Human approval (Django Admin / dashboard)
   ├─ reject  → capture reason, store as eval signal
   ├─ edit    → capture edit diff, store as eval signal
   └─ approve → Publish (idempotent) → mark sent
```

## 4. Data model (Postgres)

| Model | Key fields |
|---|---|
| `Channel` | type (email/reddit), config, enabled |
| `Customer` | external_ids (email, reddit username), name, metadata |
| `Conversation` | customer, channel, thread_key, status, created_at |
| `Message` | conversation, direction (inbound/outbound), external_id **(unique per channel)**, raw_payload, normalized_text, received_at |
| `Draft` | message (inbound), generated_text, model, prompt_version, retrieved_sources (FK list), confidence, status (pending/approved/rejected/edited), reviewer, review_note, final_text, edit_diff |
| `KnowledgeDoc` | title, source_uri, content, kind (markdown/faq/doc) |
| `KnowledgeChunk` | doc, chunk_text, **embedding (pgvector)**, token_count |
| `AuditLog` | actor (human/system), action, target, before/after, timestamp |

**Idempotency:** `Message.external_id` is unique per channel (email `Message-ID`, Reddit fullname
e.g. `t1_xxx` / `t3_xxx`). Publish writes an idempotency key so a retried Celery task can't
double-post.

## 5. Retrieval & grounding

- Use **`pgvector`** in the existing Postgres — no second datastore.
- KB docs are chunked and embedded on ingest; retrieval is top-k cosine similarity, optionally
  filtered by intent.
- The draft prompt receives only retrieved chunks as the knowledge source, and the model is
  instructed to **answer only from provided context and cite the source `KnowledgeChunk` ids**.
- If retrieval returns nothing above a similarity threshold, the draft is flagged
  `needs_human` rather than the model answering from parametric memory. This is the primary
  hallucination guard for policy/refund questions.

## 6. Safety & prompt injection (highest risk)

Inbound email/Reddit text is **untrusted input**. Controls:

1. **Data, not instructions.** Channel content is inserted into clearly delimited
   "untrusted message" sections of the prompt; system instructions explicitly state that
   message content can never change the assistant's rules or trigger actions.
2. **No privileged actions from inbound text.** Phase 1 has no tools the model can call, so the
   only "action" is producing a draft — which a human must approve. This structurally neutralizes
   injection-to-action in the MVP.
3. **Sensitive-intent routing.** Refund, legal, complaint, account-security intents auto-route to
   a human and skip auto-drafting (or draft with a prominent warning).
4. **PII handling.** Log redaction for emails/PII in `AuditLog`; raw payloads access-controlled.
5. **Human approval gate** as the final backstop for everything above.

## 7. Human approval loop

- Drafts land in a review queue (Django Admin in MVP; dedicated dashboard view next).
- Reviewer can **approve / edit-and-approve / reject-with-reason**.
- **Every edit and rejection is captured** (`edit_diff`, `review_note`) — this is the cheapest,
  highest-signal eval/training dataset.
- **SLA:** drafts older than a configurable threshold (Reddit/email are time-sensitive) surface as
  overdue. Stale Reddit threads may be skipped to respect community norms.

## 8. Channel-specific notes (don't let "normalize" hide these)

**Reddit**
- Automated posting is governed by Reddit ToS + per-subreddit rules; respect rate limits and
  account karma/age gating. Confirm the use case is ToS-compliant before enabling auto-publish.
- Thread model = comment tree; `thread_key` = submission/comment fullname.

**Email**
- Handle HTML + quoted replies, attachments, threading via `In-Reply-To` / `References`.
- Outbound deliverability: SPF/DKIM/DMARC on the sending domain.

## 9. Evaluation (moved into Phase 1)

Track from first deployment:
- **Approval rate** (approved / total drafts)
- **Edit distance** between draft and final sent text
- **Grounding/citation rate** and retrieval hit rate
- **Intent-classification accuracy** (spot-checked against reviewer corrections)
- Per-message **cost and latency**

These metrics + captured edits/rejections drive prompt iteration (versioned via `Draft.prompt_version`).

## 10. Architecture / deployment

- **MVP:** run the pipeline as **Celery workers inside the Django project** rather than a separate
  agent service. Fewer moving parts and no agent↔Django auth boundary to secure yet.
- Extract a standalone agent service in Phase 2 when tool-calling and planning justify it; the
  `LLMClient` and pipeline-step boundaries already make this a clean later split.

## 11. Phase 1 deliverables (revised, ordered)

1. Django project + Postgres (with `pgvector`) setup
2. Data model + migrations (§4)
3. Email connector (poll, dedup, normalize, publish)
4. Reddit connector (poll, dedup, normalize, publish — ToS-aware)
5. `LLMClient` abstraction + intent classification step
6. KB ingest + chunk + embed; retrieval with citations
7. Grounded draft generation with sensitive-intent routing
8. Conversation/Draft storage + audit logging
9. Human approval workflow (review queue, edit/reject capture, SLA)
10. Review dashboard for viewing conversations & drafts
11. Eval metrics dashboard (§9)

## 12. Open questions

- What is **OpenClaw** concretely (framework vs. internal service)? Determines §10 and the LLM provider.
- Which model provider/model for classify vs. draft? (Can differ — cheap model for classify.)
- Is Reddit auto-publishing in-scope, or draft-only for Reddit in Phase 1?
- KB source of truth — where do markdown/FAQ/docs live, and how are updates synced?
```
