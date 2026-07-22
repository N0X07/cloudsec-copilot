# CloudSec Copilot

CloudSec Copilot is a portfolio project that turns AWS security events into
auditable incident reports. It combines deterministic detection rules with a
tool-using AI analyst, while keeping every high-risk action behind explicit
human approval.

## Problem

Cloud security logs are detailed but time-consuming to investigate. Analysts
need to collect related events, identify the affected identity and resource,
consult response playbooks, and document their conclusions. This project
automates the repetitive parts without allowing the AI layer to make
uncontrolled changes to cloud resources.

## MVP scope

The first usable version will:

1. Import synthetic AWS CloudTrail-style JSON events.
2. Normalize and store the events in PostgreSQL.
3. Detect at least five suspicious event patterns with deterministic rules.
4. Let an AI analyst call allow-listed tools to collect supporting evidence.
5. Retrieve relevant response guidance from a small playbook knowledge base.
6. Produce a structured incident report with severity, confidence, evidence,
   ATT&CK mapping, and recommended actions.
7. Require human approval before any simulated remediation action.
8. Record every analysis, tool call, and approval decision in an audit log.

## Initial detection scenarios

- Root account login without MFA
- CloudTrail logging disabled
- Public S3 bucket configuration
- Risky security-group ingress on port 22 or 3389
- IAM privilege escalation or policy modification
- Repeated failed authentication attempts

## Planned architecture

```text
CloudTrail-style events
        |
        v
Ingestion API -> PostgreSQL -> Rule engine -> Incident
                                      |
                                      v
                              AI analyst tools
                              /      |       \
                         event    identity   playbook
                         search    context    search
                              \      |       /
                                      v
                         Structured incident report
                                      |
                                      v
                         Human approval + audit log
```

The local MVP will run with FastAPI, PostgreSQL, and Docker Compose. AWS
deployment, Terraform, CI/CD, and cloud monitoring will be added only after the
local detection and evaluation pipeline is reliable.

## Implemented local API

The current backend includes:

- Idempotent import of CloudTrail-style `Records` envelopes
- Normalized event fields plus retention of the original JSON event
- Event listing and lookup endpoints
- Five deterministic AWS security detection rules
- Idempotent incident creation with evidence and human-approval metadata
- Structured incident reports with MITRE ATT&CK context and response steps
- Optional OpenAI Responses API analyst with two allow-listed read-only tools
- Per-tool-call audit records, bounded agent steps, and incident-scoped access
- One-time human approval or rejection without automatic cloud remediation
- PostgreSQL runtime configuration and temporary SQLite test databases

### Endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Service health and environment |
| `POST` | `/api/v1/events/import` | Validate and import a CloudTrail envelope |
| `GET` | `/api/v1/events` | List stored events |
| `GET` | `/api/v1/events/{event_id}` | Retrieve one event |
| `POST` | `/api/v1/events/{event_id}/analyze` | Run deterministic detection |
| `POST` | `/api/v1/events/{event_id}/analyze-all` | Run all detection rules |
| `GET` | `/api/v1/incidents` | List generated incidents |
| `GET` | `/api/v1/incidents/{incident_id}/report` | Build an auditable incident report |
| `POST` | `/api/v1/incidents/{incident_id}/agent-analysis` | Run the bounded AI analyst |
| `GET` | `/api/v1/incidents/{incident_id}/audit` | List agent and approval audit records |
| `POST` | `/api/v1/incidents/{incident_id}/approval` | Approve or reject proposed response work |

## Local development

Python 3.12 or newer is required.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

The API is available at `http://localhost:8000`, with interactive documentation
at `http://localhost:8000/docs`. Without `DATABASE_URL`, local development uses
`sqlite:///./cloudsec.db`.

Validate the labeled dataset without third-party dependencies:

```powershell
python scripts/validate_dataset.py
```

The deterministic API works without an OpenAI key. To enable the optional
agent-analysis endpoint, copy `.env.example` to `.env`, set `OPENAI_API_KEY`,
and load those environment variables before starting the API. The default model
is `gpt-5.6-terra` and can be changed with `OPENAI_MODEL`.

## Agent safety boundary

The model can call only `get_event_context` and `get_incident_report`. Both are
read-only, validate that requested IDs belong to the active incident, and write
their inputs, outputs, and success state to the audit table. Raw log fields are
explicitly marked as untrusted data. The loop stops after `MAX_AGENT_STEPS`
(default 4, hard maximum 8), and no remediation tool is exposed to the model.

Human approval changes only the incident workflow state. Even an approved
decision is reported as `approved_not_executed`; this MVP never changes AWS
resources.

## Docker Compose

Start the API and PostgreSQL together:

```powershell
docker compose up --build
```

The Compose password is intentionally development-only. Production secrets must
come from a managed secret store and must never be committed.

## Continuous integration

`.github/workflows/ci.yml` installs the project on Python 3.12, validates all
labeled events, runs the full test suite, compiles the source tree, and builds
the production container. It uses read-only repository permissions and never
receives an OpenAI API key; the Agent loop is tested with a deterministic fake
client instead of making paid external calls.

## Security principles

- Deterministic rules remain the source of truth for the initial detections.
- AI tools are allow-listed and validated with strict input schemas.
- Log content is treated as untrusted data, never as instructions.
- Conclusions must reference stored evidence.
- Tool calls and approval decisions are auditable.
- High-risk actions require human approval and are simulated in the MVP.
- Secrets are never committed to the repository.

## Milestones

- [x] Define project goal, MVP boundary, and security principles.
- [x] Create and label synthetic CloudTrail-style events.
- [ ] Build and verify the FastAPI ingestion endpoint and PostgreSQL schema.
- [x] Implement and verify the first rule: root login without MFA.
- [x] Expand to five labeled AWS security detection rules.
- [x] Generate evidence-backed incident reports with ATT&CK mappings.
- [ ] Run automated tests for ingestion and detection.
- [x] Add bounded AI analyst tools and per-call audit records.
- [x] Add a one-time human approval/rejection workflow.
- [ ] Add playbook retrieval and evaluation.
- [ ] Containerize and deploy to AWS with Terraform and CI/CD.
- [ ] Publish architecture, results, and a short demonstration video.

## MVP completion criteria

The MVP is complete when it can be started from a clean environment, import a
labeled event set, detect the supported scenarios, generate evidence-backed
reports, pass automated tests, and show evaluation results without performing
unapproved cloud actions.

## Current status

The ingestion API, database models, five detection rules, incident persistence,
structured reports, bounded AI analyst, audit trail, approval workflow, Docker
configuration, and API tests are implemented. All five rules have been verified
against 18 labeled events using dependency-free unit tests. Full API,
PostgreSQL, and live-model integration tests remain pending until the Python
dependencies, container images, and optional API key are available locally.
