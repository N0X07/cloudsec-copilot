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
- [ ] Build the FastAPI ingestion endpoint and PostgreSQL schema.
- [ ] Implement the first rule: root login without MFA.
- [ ] Add automated tests for ingestion and detection.
- [ ] Add AI analyst tools and structured incident reports.
- [ ] Add playbook retrieval and evaluation.
- [ ] Containerize and deploy to AWS with Terraform and CI/CD.
- [ ] Publish architecture, results, and a short demonstration video.

## MVP completion criteria

The MVP is complete when it can be started from a clean environment, import a
labeled event set, detect the supported scenarios, generate evidence-backed
reports, pass automated tests, and show evaluation results without performing
unapproved cloud actions.

## Current status

Milestones 1 and 2 are complete. The next step is to build the FastAPI ingestion
endpoint and PostgreSQL schema for the labeled CloudTrail-style event set.
