# API reference

All methods require an authenticated Frappe session or token. Read operations allow `GET`; mutations allow `POST`. Normal Frappe REST DocType endpoints remain available according to DocType and row permissions, while these methods package domain operations that need validation or aggregation.

## Domain methods

| Method | Verb | Purpose | Primary authorization |
|---|---|---|---|
| `northstar_crm.api.get_sales_cockpit` | GET | Forecast, ordered stages, open deals and next activities | Read CRM Opportunity and related records |
| `northstar_crm.api.create_lead` | POST | Controlled lead capture | Create CRM Lead |
| `northstar_crm.api.convert_lead` | POST | Create/link account and contact, create deal, close lead | Write source lead and create related records |
| `northstar_crm.api.move_opportunity` | POST | Validate and apply a pipeline stage; require loss reason when needed | Write opportunity |
| `northstar_crm.api.get_customer_360` | GET | Safe-field aggregate for one accessible account | Read organization and each related row |
| `northstar_crm.api.search_document_assets` | GET | Permission-aware title/tag/extracted-text search | Read document asset |
| `northstar_crm.api.add_note` | POST | Create a completed note activity on a CRM record | Read reference and create activity |
| `northstar_crm.api.decide_quote` | POST | Approve or reject a pending quote and write an audit activity | Sales Manager/System Manager plus quote write |
| `northstar_crm.api.ingest_integration_event` | POST | Accept an idempotent inbound JSON envelope | Integration User/System Manager |
| `northstar_crm.install.seed_demo_data` | POST | Add deterministic sample organizations and deals | System Manager |

Frappe wraps method output under `message` in the HTTP response.

## Authentication example

```bash
curl --request GET \
  --header "Authorization: token API_KEY:API_SECRET" \
  "https://crm.example.com/api/method/northstar_crm.api.get_sales_cockpit?period=quarter"
```

Keep API secrets outside source control and send them only over TLS.

## Create a lead

```bash
curl --request POST \
  --header "Authorization: token API_KEY:API_SECRET" \
  --header "Content-Type: application/json" \
  --data '{
    "data": {
      "lead_name": "Aisha Alharbi",
      "organization_name": "Horizon Industries",
      "email": "aisha@example.com",
      "source": "Website",
      "business_need": "Unify customer operations",
      "estimated_value": 325000
    }
  }' \
  "https://crm.example.com/api/method/northstar_crm.api.create_lead"
```

## Move an opportunity

```bash
curl --request POST \
  --header "Authorization: token API_KEY:API_SECRET" \
  --header "Content-Type: application/json" \
  --data '{
    "opportunity_name": "OPP-2026-00001",
    "pipeline_stage": "Negotiation"
  }' \
  "https://crm.example.com/api/method/northstar_crm.api.move_opportunity"
```

Moving to a stage marked Lost also requires `loss_reason`.

## Decide a quote

```bash
curl --request POST \
  --header "Authorization: token MANAGER_KEY:MANAGER_SECRET" \
  --header "Content-Type: application/json" \
  --data '{
    "quote_name": "QTN-2026-00001",
    "decision": "Approved"
  }' \
  "https://crm.example.com/api/method/northstar_crm.api.decide_quote"
```

For `Rejected`, include a non-empty `rejection_reason`.

## Ingest an event

```bash
curl --request POST \
  --header "Authorization: token INTEGRATION_KEY:INTEGRATION_SECRET" \
  --header "Content-Type: application/json" \
  --data @examples/lead.created.json \
  "https://crm.example.com/api/method/northstar_crm.api.ingest_integration_event"
```

The same `idempotency_key` returns the existing event instead of creating a second CRM record. Accepted types are:

| Event type | Result |
|---|---|
| `lead.created` | Creates a CRM Lead |
| `activity.logged` | Creates a CRM Activity after reference validation |
| Any other value | Retained as `Manual Review` without applying business data |

## Error behavior

Validation and permission failures use Frappe's standard exception response. Clients should treat an initial `Received` response as acceptance, not completed processing; poll the permitted `CRM Integration Event` resource or add an approved outbound callback extension.
