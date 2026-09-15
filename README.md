# Northstar CRM for Frappe v16

Northstar CRM is an enterprise-style B2B customer relationship management application built for Frappe Framework v16. It turns the CRM idea—maintaining a reliable history of every customer relationship and coordinating the work needed to grow it—into an installable Desk application.

The release includes 16 custom DocTypes, a responsive Sales Cockpit, authenticated APIs, explainable lead scoring, pipeline forecasting, controlled quotes, consent and document governance, integrations, background jobs, row-level security, demo data, tests, an ARM64 free-cloud deployment kit, and an Azure Container Registry remote-build path.

## What is implemented

| Area | Current implementation |
|---|---|
| Sales Cockpit | Monthly or quarterly metrics, weighted forecast, ordered pipeline columns, stage moves, stale-deal indicators, and next activities |
| Lead management | Manual and API capture, deterministic 0–100 scoring, configurable ratings, qualification rules, and conversion |
| Customer records | Organizations, contacts, account ownership, buying roles, communication preferences, and relationship context |
| Customer 360 | Permission-aware API aggregating an organization, its contacts, opportunities, activities, and governed documents |
| Opportunities | Configurable stages, stage history, probability-derived value, stakeholders, line items, loss controls, and realtime refresh |
| Quotes | Versioned, submittable quotes; calculated discounts, tax, totals; configurable discount/high-value manager gate with approval invalidation when commercial terms change |
| Engagement | Calls, emails, meetings, tasks, notes, transcripts, outcomes, next actions, and latest-contact propagation |
| Privacy and content | Purpose/channel consent, expiry and revocation, PII flag, content classification, private-file policy, retention date, and legal hold |
| Document intelligence | Searchable register, checksums, file metadata, and queued text extraction for text, Markdown, CSV, JSON, XML, and log files |
| Integrations | Idempotent, size-bounded inbound events with queued handlers for `lead.created` and `activity.logged` |
| Forecasting | Permission-aware monthly/quarterly forecasts and daily company snapshots |
| Security | Five CRM roles, DocType permissions, field permission levels, and owner/account-manager row restrictions across related records |

This is an operational CRM foundation, not yet a marketing automation, customer-support, invoicing, or ERP suite. The exact implemented boundary and extension roadmap are documented in [System architecture](docs/architecture.md).

## Quick start

Requirements: a working Frappe v16 Bench site, Python 3.11+, database, Redis, workers, scheduler, and Node tooling expected by Frappe.

```bash
cd /path/to/frappe-bench
bench get-app /absolute/path/to/frappe-northstar-crm
bench --site crm.example.test install-app northstar_crm
bench --site crm.example.test migrate
bench build --app northstar_crm
bench start
```

For a persistent free-cloud demo, use the Oracle Ampere A1 deployment kit in [`deploy/oracle-arm64`](deploy/oracle-arm64/README.md). It builds an immutable Frappe v16 ARM64 image, keeps database and site data in named volumes, and terminates HTTPS with Traefik.

For Azure Container Apps, use [`deploy/azure-container-apps`](deploy/azure-container-apps/README.md). Its AMD64 image can be built inside Azure Container Registry from browser-based Azure Cloud Shell, so Docker is not required on the Windows client.

Then:

1. Assign one or more Northstar roles to users.
2. Open `/desk/sales-cockpit`.
3. Optionally create sample organizations and opportunities:

```bash
bench --site crm.example.test execute northstar_crm.install.seed_demo_data
```

Run the test suite with:

```bash
bench --site crm.example.test run-tests --app northstar_crm
```

## Roles

| Role | Intended responsibility |
|---|---|
| CRM Sales User | Work assigned leads, accounts, contacts, opportunities, activities, documents, and quotes |
| CRM Sales Manager | See the full sales estate, reassign ownership, approve discounts, administer the pipeline, and report |
| CRM Analyst | Read and report across commercial records without transactional write access |
| CRM Compliance Manager | Review governed customer/content records and restricted identity fields |
| CRM Integration User | Submit and inspect authenticated integration events |

`System Manager` retains platform administration rights.

## Project map

```text
frappe-northstar-crm/
├── northstar_crm/
│   ├── api.py                         # Authenticated GET/POST methods
│   ├── permissions.py                 # Related-record row security
│   ├── install.py                     # Roles, stages, and initial settings
│   ├── demo.py                        # Idempotent sample records
│   ├── tasks.py                       # Scheduler maintenance and snapshots
│   ├── events/                        # Stage, activity, file, and integration hooks
│   ├── services/                      # Scoring, forecasting, extraction, integrations
│   ├── fixtures/                      # Portable role definitions
│   ├── tests/                         # Unit and Frappe integration tests
│   └── northstar_crm/
│       ├── doctype/                   # 16 DocTypes and controllers
│       └── page/sales_cockpit/        # Desk frontend
├── docs/                              # DFDs, ER model, security, API, deployment
├── deploy/oracle-arm64/               # OCI ARM64 Compose, bootstrap, TLS, backups
├── deploy/azure-container-apps/        # Azure remote image build files
├── .github/workflows/                 # Immutable AMD64/ARM64 image publishing
├── examples/                          # Integration payload examples
└── pyproject.toml
```

## Documentation

- [System architecture and DFDs](docs/architecture.md)
- [Structured, semi-structured, and unstructured data](docs/data-model.md)
- [Security and governance](docs/security.md)
- [API reference](docs/api.md)
- [Deployment and operations](docs/deployment.md)

## Important operating notes

- Customer flows in the DFD are indirect: this version has no public customer portal, email sender, or electronic signature channel.
- Quote submission creates an internal CRM activity; it does not generate or deliver a PDF.
- Built-in extraction intentionally handles safe text formats only. PDF, Office, image, and audio files move to `Manual Review` for an external processor.
- Forecast totals assume one reporting currency. Add an exchange-rate normalization service before mixing currencies in management totals.
- Retention and legal-hold fields are implemented, but automated disposal is deliberately left for a policy-approved extension.

## License

MIT
