# System architecture and data-flow diagrams

## Architectural intent

Northstar CRM uses Frappe DocTypes as the transactional system of record, controllers for domain invariants, permission hooks for related-record row security, whitelisted methods for intentional frontend/integration operations, and Redis-backed workers for asynchronous extraction, integration handling, and scoring.

## DFD notation

| Shape | Meaning |
|---|---|
| Rectangle | External actor or system |
| Rounded process | Transformation performed by Northstar CRM |
| Cylinder | Persistent Frappe data store |
| Solid arrow | Implemented direct data flow |
| Dotted arrow | Indirect/manual flow in this release |

## DFD Level 0 — System context

```mermaid
flowchart TB
    C["Prospect or customer"]
    P0(("0. Northstar CRM"))
    U["Sales users and managers"]
    G["Analysts, compliance and administrators"]
    X["Authenticated source systems"]

    C -.->|"Identity, enquiry, consent and interaction data relayed by staff or integrations"| P0
    P0 -.->|"Quotes and follow-up records used for manual delivery"| C
    U <-->|"Leads, activities, opportunities, quotes and pipeline actions"| P0
    G <-->|"Configuration, approvals, forecasts and governance records"| P0
    X -->|"Inbound lead or activity JSON events"| P0
    P0 -->|"Event state and created-record reference"| X
```

The dotted customer flows are indirect. Northstar does not yet provide a customer portal, campaign sender, email delivery service, or electronic signature channel.

## DFD Level 1 — Implemented processes and stores

```mermaid
flowchart TB
    subgraph External["External actors"]
        U["Sales staff"]
        M["Managers, analysts and compliance"]
        X["Inbound source systems"]
        C["Prospect or customer"]
    end

    subgraph Processes["Northstar CRM processes"]
        P1(("1. Capture and qualify leads"))
        P2(("2. Maintain customer 360"))
        P3(("3. Drive opportunity pipeline"))
        P4(("4. Calculate and gate quotes"))
        P5(("5. Record activities and content"))
        P6(("6. Integrate, automate and forecast"))
    end

    subgraph Stores["Frappe data stores"]
        D1[("D1 Leads")]
        D2[("D2 Organizations, contacts and consent")]
        D3[("D3 Opportunities, child rows and stage history")]
        D4[("D4 Quotes and quote items")]
        D5[("D5 Activities, files and extracted content")]
        D6[("D6 Integration events, snapshots and settings")]
    end

    U <-->|"Capture, qualification and conversion"| P1
    C -.->|"Enquiry and identity information"| P1
    P1 <--> D1
    P1 -->|"Converted party records"| P2
    P2 <--> D2
    U <-->|"Account and relationship updates"| P2

    P2 -->|"Organization and contact context"| P3
    U <-->|"Value, stage, stakeholders and outcome"| P3
    P3 <--> D3
    P3 -->|"Commercial context"| P4
    U <-->|"Items, discounts and submission"| P4
    M <-->|"Approval decision"| P4
    P4 <--> D4

    U <-->|"Calls, meetings, notes and documents"| P5
    C -.->|"Conversation and file content"| P5
    P5 <--> D5
    P5 -->|"Recency and engagement signals"| P1
    P5 -->|"Last activity and stage evidence"| P3

    X -->|"Idempotent inbound JSON event"| P6
    P6 -->|"Create lead"| P1
    P6 -->|"Create activity"| P5
    D3 -->|"Pipeline facts"| P6
    P6 -->|"Event state and daily aggregates"| D6
    P6 -->|"Forecasts and exceptions"| M
```

## Component architecture

```mermaid
flowchart TB
    subgraph Clients["Clients"]
        U["Frappe Desk users"]
        X["Authenticated source systems"]
    end

    subgraph Application["Northstar CRM application"]
        UI["Sales Cockpit and standard forms"]
        API["Whitelisted GET and POST API"]
        DOM["Controllers, permissions and domain services"]
        AUTO["Doc events, scheduler and queued jobs"]
    end

    subgraph Runtime["Frappe runtime"]
        ORM["Frappe ORM and 16 custom DocTypes"]
        Q["Redis queues and realtime events"]
        STORE[("Site database and private file storage")]
    end

    U --> UI
    X --> API
    UI --> API
    UI --> DOM
    API --> DOM
    DOM --> ORM
    ORM --> STORE
    DOM --> AUTO
    AUTO --> Q
    Q --> DOM
    Q -.->|"Pipeline refresh"| UI
```

## Runtime sequence — inbound integration event

```mermaid
sequenceDiagram
    participant X as Source system
    participant A as Frappe API
    participant E as Integration Event
    participant Q as Worker queue
    participant D as CRM DocType

    X->>A: POST event and token
    A->>A: Validate role, JSON and 1 MB bound
    A->>E: Insert unique idempotency key
    E->>Q: Enqueue after commit
    Q->>E: Mark Processing
    Q->>D: Create lead or activity
    Q->>E: Store Applied state and reference
    A-->>X: Event name and current state
```

## Implemented boundary and roadmap

| Implemented now | Extension roadmap |
|---|---|
| Lead capture, scoring, qualification and conversion | Campaigns, audience segments, journeys and attribution models |
| Organizations, contacts and consent evidence | Customer portal and preference center |
| Opportunities, stages, stakeholders, items and history | Territory hierarchy, team quotas and formal sales methodologies |
| Quote calculations and server-enforced discount approval | Generated PDFs, outbound delivery, e-signature and contracts |
| Calls, meetings, tasks, notes and transcripts | Calendar, email, telephony and messaging connectors |
| Text-file extraction, checksums and document search | PDF/Office extraction, OCR, transcription and semantic search |
| Two inbound event types and idempotency | Outbound webhooks, dead-letter handling and ERP synchronization |
| Forecast calculations and daily snapshots | FX normalization, scenarios, quotas and historical charts |
| Classification, retention, legal hold and consent status | Policy-driven disposal, subject-access workflows, DLP and SIEM export |
| Quote-to-activity audit events | Products, contracts, orders, invoices, payments, cases and renewals |
