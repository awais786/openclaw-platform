# OpenClaw — Architecture & Sequence Diagrams

Visual companion to `openclaw-plan.md`. Diagrams are Mermaid (render in GitHub / most viewers).

---

## 1. System architecture (components)

Where OpenClaw stops and Django begins — the tool interface is the only boundary.

```mermaid
flowchart TB
    subgraph Channels["Customer Channels"]
        CU["Contact-Us (Phase 1)"]
        EM["Email (Phase 2)"]
        RD["Reddit (Phase 2, draft-only)"]
    end

    CON["Channel Connectors<br/>(receive · dedup · normalize · publish)"]

    subgraph OC["OpenClaw Engine (Celery workers in Django)"]
        PL["Planner<br/>(fixed plan in Phase 1)"]
        RT["Retriever"]
        TE["Tool Executor<br/>★ gating · idempotency · audit choke point"]
        RG["Response Generator<br/>(grounded, cited draft)"]
        PL --> RT --> TE --> RG
    end

    subgraph DJ["Django Backend"]
        TOOLS["Tool implementations<br/>(read + write/action)"]
        WF["Approval workflow"]
        ADMIN["Admin / Dashboards"]
        API["REST APIs · Auth · RBAC"]
    end

    DB[("PostgreSQL + pgvector")]
    LLM["LLMClient<br/>(provider-agnostic)"]

    Channels --> CON --> OC
    TE -- "tool calls only" --> TOOLS
    PL -. classify .-> LLM
    RG -. draft .-> LLM
    TOOLS --> DB
    WF --> DB
    ADMIN --> DB
    API --> DB

    classDef star fill:#fde68a,stroke:#b45309,color:#000;
    class TE star;
```

> The agent knows **only tool schemas**. Every side effect crosses into Django through the Tool
> Executor → tool implementations. Swap the agent or the DB and the other side is unaffected.

---

## 2. Pipeline flow (per inbound message)

```mermaid
flowchart TD
    A["Connector receives / polls message"] --> B{"Seen before?<br/>(external_id dedup)"}
    B -- yes --> Z1["Drop (idempotent)"]
    B -- no --> C["Normalize → NormalizedMessage"]
    C --> D["Classify intent (LLM #1)"]
    D --> E{"Low confidence<br/>OR sensitive intent?"}
    E -- yes --> H["route_to_human<br/>(skip auto-draft)"]
    E -- no --> F["Retrieve knowledge<br/>(pgvector top-k + sources)"]
    F --> G{"Any hit above<br/>similarity threshold?"}
    G -- no --> H2["Flag needs_human<br/>(never answer from memory)"]
    G -- yes --> I["Draft response (LLM #2)<br/>grounded + cited"]
    I --> J{"Capability gate:<br/>action auto-eligible?"}
    J -- no --> K["Store Draft = pending_review"]
    K --> L["Human approves / edits / rejects"]
    J -- yes --> M["Store Draft = auto_approved"]
    L -- approve --> N["publish_reply (idempotent)"]
    M --> N
    L -- reject --> R["Capture reason → eval signal"]
    N --> O["Mark sent · AuditLog · ToolCall · EvalMetric"]

    classDef guard fill:#fde68a,stroke:#b45309,color:#000;
    class J,E,G guard;
```

---

## 3. Agent runtime ↔ tool boundary

```mermaid
flowchart LR
    subgraph OpenClaw["OpenClaw (reasoning side)"]
        direction TB
        P["Planner"] --> R["Retriever"] --> X["Tool Executor"]
        X --> RGen["Response Generator"]
    end

    subgraph Django["Django (authority side)"]
        direction TB
        RTools["Read tools<br/>get_customer · search_kb<br/>get_conversation · lookup_subscription<br/>refund_eligibility"]
        WTools["Write/action tools<br/>save_draft · publish_reply<br/>create_github_issue · create_jira_ticket<br/>issue_refund · route_to_human"]
        GATE{"CapabilityPolicy<br/>auto / human_approval / never_auto"}
    end

    X -- "read (safe)" --> RTools
    X -- "write (gated)" --> GATE
    GATE -- allowed --> WTools
    GATE -- blocked --> Q["Queue for approval<br/>or refuse (never_auto)"]
    RTools --> DB[("Postgres + pgvector")]
    WTools --> DB

    classDef star fill:#fde68a,stroke:#b45309,color:#000;
    class X,GATE star;
```

> Security consequence: because every action flows through gated Django-side tools, prompt
> injection can at worst yield a **draft** or a **safe read** — never an unauthorized action.

---

## 4. Sequence — propose-then-approve loop (Contact-Us, Phase 1)

```mermaid
sequenceDiagram
    autonumber
    actor Cust as Customer
    participant Conn as Contact-Us Connector
    participant OC as OpenClaw (Planner/Retriever/Generator)
    participant TE as Tool Executor
    participant DJ as Django Tools
    participant DB as Postgres+pgvector
    participant Rev as Reviewer (human)

    Cust->>Conn: Submit contact-us message
    Conn->>TE: save_conversation(...) [idempotency_key]
    TE->>DJ: dedup + persist
    DJ->>DB: insert Message/Conversation
    OC->>OC: classify intent (LLM #1)
    alt low confidence / sensitive
        OC->>TE: route_to_human(intent, reason)
        TE->>DJ: enqueue for human
    else proceed
        OC->>TE: search_kb(query, intent)
        TE->>DJ: retrieve
        DJ->>DB: top-k vector search
        DB-->>OC: chunks + source ids
        alt no hit above threshold
            OC->>TE: save_draft(status=needs_human)
        else grounded
            OC->>OC: draft reply (LLM #2, cited)
            OC->>TE: save_draft(status=pending_review)
        end
    end
    TE->>DB: log ToolCall(gate_decision)
    Rev->>DJ: review queue → approve / edit / reject
    alt approved (or edited)
        Rev->>TE: approve → publish_reply [idempotency_key]
        TE->>DJ: gate check (publish allowed?)
        DJ-->>Cust: send reply
        TE->>DB: AuditLog + EvalMetric (approval, edit_distance)
    else rejected
        Rev->>DB: review_note → eval signal
    end
```

---

## 5. Capability gating — decision per action

```mermaid
flowchart TD
    A["Agent requests a write/action tool"] --> B{"Action in<br/>never_auto hard-wall?<br/>(refund · legal · pricing · security)"}
    B -- yes --> H["Require human · always<br/>(metrics cannot override)"]
    B -- no --> C{"CapabilityPolicy mode<br/>for channel + intent?"}
    C -- human_approval --> H2["Queue for reviewer"]
    C -- auto --> D{"Public channel?<br/>(e.g. Reddit post)"}
    D -- yes --> H3["Extra guard:<br/>manual sign-off until ToS-cleared"]
    D -- no --> E["Execute (idempotent)"]
    H2 -- approved --> E
    E --> F["Log ToolCall(gate_decision) + AuditLog"]

    classDef wall fill:#fecaca,stroke:#b91c1c,color:#000;
    class B,H wall;
```

> Promotion `human_approval → auto` happens only when measured approval rate + edit distance
> meet the criteria for that channel + intent (see `openclaw-plan.md` §6, §9).
```
