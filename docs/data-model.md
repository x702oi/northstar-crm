# Data model: structured and unstructured information

Northstar records two independent properties of information:

1. **Data shape** — structured, semi-structured, or unstructured.
2. **Sensitivity** — Public, Internal, Confidential, or Restricted.

A contract PDF, for example, is unstructured in shape and may be Restricted in sensitivity. A contact email is structured but still personal data. The concepts must not be mixed.

## Data-shape inventory

| Data shape | Implemented examples | Storage and processing | Main controls |
|---|---|---|---|
| Structured | Organizations, contacts, leads, stages, opportunities, stakeholders, items, quotes, consent, activities, stage history, snapshot metrics | Typed DocType columns, Link fields and relational child tables; controller validation; permission-aware ORM queries | Required fields, referential checks, numeric ranges, lifecycle rules, DocType permissions and related-record ownership |
| Semi-structured | Lead `score_breakdown`, integration `payload_json` and `response_json`, forecast `stage_breakdown`, document `derived_metadata` | JSON fields inside relational records; deterministic scoring/forecast outputs; versioned integration envelope | JSON-object validation, schema version, unique idempotency key, state machine, explicit supported event types and 1 MB API bound |
| Unstructured | Notes, email bodies, meeting summaries, call transcripts, deal context, quote terms, proposals, contracts, recordings and uploaded files | Text fields plus private Frappe `File` attachments; supported text files are extracted asynchronously into a bounded searchable field | Classification, PII indicator, private-file policy, size limit, SHA-256 checksum, content owner, retention date and legal hold |

## Data-shape flow

```mermaid
flowchart TB
    I["Desk or authenticated API input"]
    S{"Determine data shape"}
    A["Typed fields and child rows"]
    B["JSON envelopes and derived summaries"]
    C["Narrative text and uploaded files"]
    D[("DocType tables")]
    E[("JSON fields")]
    F[("Private files and content fields")]
    W["Queued text extraction"]
    O["Permission-aware views, search and forecasts"]

    I --> S
    S --> A
    S --> B
    S --> C
    A --> D
    B --> E
    C --> F
    F --> W
    W --> F
    D --> O
    E --> O
    F --> O
```

## Commercial core ER model

```mermaid
erDiagram
    CRM_ORGANIZATION ||--o{ CRM_OPPORTUNITY : owns
    CRM_ORGANIZATION o|--o{ CRM_CONTACT : has
    CRM_CONTACT ||--o{ CRM_CONSENT : grants
    CRM_LEAD o|--o| CRM_OPPORTUNITY : converts_to
    CRM_PIPELINE_STAGE ||--o{ CRM_OPPORTUNITY : classifies
    CRM_CONTACT o|--o{ CRM_OPPORTUNITY : primary_contact
    CRM_OPPORTUNITY ||--o{ CRM_OPPORTUNITY_STAKEHOLDER : contains
    CRM_CONTACT ||--o{ CRM_OPPORTUNITY_STAKEHOLDER : participates_as
    CRM_OPPORTUNITY ||--o{ CRM_OPPORTUNITY_ITEM : contains
    CRM_OPPORTUNITY ||--o{ CRM_STAGE_HISTORY : records
    CRM_PIPELINE_STAGE ||--o{ CRM_STAGE_HISTORY : appears_in
    CRM_OPPORTUNITY ||--o{ CRM_QUOTE : priced_by
    CRM_QUOTE ||--|{ CRM_QUOTE_ITEM : contains

    CRM_ORGANIZATION {
        string name PK
        string organization_name
        string account_manager FK
        string lifecycle_stage
    }
    CRM_CONTACT {
        string name PK
        string organization FK
        string email
        string buying_role
    }
    CRM_LEAD {
        string name PK
        string lead_owner FK
        int lead_score
        json score_breakdown
    }
    CRM_OPPORTUNITY {
        string name PK
        string organization FK
        string pipeline_stage FK
        decimal weighted_amount
    }
    CRM_QUOTE {
        string name PK
        string opportunity FK
        string approval_status
        decimal grand_total
    }
```

## Engagement and governance ER model

```mermaid
erDiagram
    CRM_ORGANIZATION o|--o{ CRM_ACTIVITY : groups
    CRM_CONTACT o|--o{ CRM_ACTIVITY : involves
    CRM_ORGANIZATION o|--o{ CRM_DOCUMENT_ASSET : owns
    CRM_DOCUMENT_ASSET o|--o{ CRM_CONSENT : evidences
    CRM_INTEGRATION_EVENT o|--o| CRM_LEAD : may_create
    CRM_INTEGRATION_EVENT o|--o| CRM_ACTIVITY : may_create

    CRM_ACTIVITY {
        string name PK
        string reference_doctype
        string reference_name
        text notes
    }
    CRM_DOCUMENT_ASSET {
        string name PK
        string file_url
        string classification
        text extracted_text
        json derived_metadata
    }
    CRM_CONSENT {
        string name PK
        string contact FK
        string purpose
        string status
    }
    CRM_INTEGRATION_EVENT {
        string name PK
        string idempotency_key UK
        json payload_json
        string status
    }
    CRM_FORECAST_SNAPSHOT {
        string name PK
        date snapshot_date
        decimal weighted_forecast
        json stage_breakdown
    }
    CRM_SETTINGS {
        string name PK
        string default_currency
        int stale_opportunity_days
    }
```

`CRM Activity`, `CRM Document Asset`, and `CRM Integration Event` use Dynamic Links because each may reference several CRM record types. Forecast snapshots and singleton settings are aggregate/configuration records rather than transactional children.

## DocType catalog

| DocType | Kind | Primary purpose | Dominant shape |
|---|---|---|---|
| CRM Organization | Master | Account identity, ownership, value and relationship health | Structured + narrative notes |
| CRM Contact | Master | Person, buying role and communication preference | Structured + narrative notes |
| CRM Lead | Transaction | Prospect qualification, score and conversion | Structured + score JSON |
| CRM Pipeline Stage | Configuration | Ordered probability and won/lost semantics | Structured |
| CRM Opportunity | Transaction | Deal pipeline, value, stakeholders, products and context | Structured + narrative context |
| CRM Opportunity Stakeholder | Child | Buying-committee membership | Structured |
| CRM Opportunity Item | Child | Opportunity product/service value | Structured |
| CRM Activity | Transaction | Interaction/task record and conversation content | Structured + unstructured text |
| CRM Consent | Governance | Purpose/channel permission evidence | Structured |
| CRM Document Asset | Governance | File catalog, classification and extraction | Structured + JSON + unstructured file/text |
| CRM Quote | Submittable transaction | Commercial offer and approval gate | Structured + unstructured terms |
| CRM Quote Item | Child | Priced line, discount and calculated total | Structured |
| CRM Stage History | Audit | Pipeline transition evidence and stage duration | Structured |
| CRM Forecast Snapshot | Aggregate | Daily management forecast record | Structured + breakdown JSON |
| CRM Integration Event | Operational | Idempotent inbound envelope and processing state | Structured + JSON |
| CRM Settings | Singleton configuration | Commercial, content and scoring policies | Structured |

## Unstructured-content pipeline

```mermaid
flowchart TB
    U["Authorized user uploads private file"]
    V["Validate reference, ownership, size and privacy"]
    R[("Document Asset and File records")]
    Q["Queue extraction after commit"]
    T{"Supported text format?"}
    X["Decode, normalize and bound text"]
    M["Manual Review for external processor"]
    S[("Checksum, metadata and searchable text")]

    U --> V
    V --> R
    R --> Q
    Q --> T
    T -->|"Yes"| X
    T -->|"No"| M
    X --> S
    M --> S
```

The application does not automatically delete expired content. `retention_until` and `legal_hold` provide governance evidence for a future organization-approved disposal workflow.
