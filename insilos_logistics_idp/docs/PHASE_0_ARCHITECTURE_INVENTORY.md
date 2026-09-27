# Phase 0 Architecture Inventory

Source: `docs/industries/Insilos_Vertical_IDP_Logistics_SRS_v1.4_Trade_Compliance_MES_Boundary.md` and runtime `models/logistics_idp.py`.
Status: current runtime schema is implemented for synthetic Enterprise R&D sales-demo use. Production, customer acceptance, external OCR acceptance remain deferred.

## Architecture decision

- `logistics.idp.case` is the deterministic IDP aggregate and source of truth.
- A case will link to exactly one `project.task` workspace for chatter, activities, assignment, and exception collaboration. State and verdict derive one-way from the aggregate; `project.task` does not duplicate business rules.
- Existing structured models are required. Properties, tags, and chatter cannot enforce relational integrity, immutable version chains, queryable check matrices, idempotency, provenance, or concurrency constraints.

## Authorized runtime inventory

| Capability | Runtime model/service | Grounded behavior | Status |
|---|---|---|---|
| Case aggregate | `logistics.idp.case` | Unique source identity; correlation; exact/semantic duplicate handling; reconciliation; customs, broker, Shipping Plan, Gate Pass operations | Implemented prototype |
| Immutable evidence | `logistics.idp.evidence` via `logistics.idp.immutable.snapshot` | Canonical JSON, SHA-256, append-only guard, per-case payload dedupe | Implemented prototype |
| Policy decision snapshot | `logistics.idp.policy.decision` | Policy code/version, effective interval, verdict, reason, immutable payload | Implemented prototype |
| MES reference | `logistics.idp.mes.reference` | Versioned inbound-only source identity and provenance; no write-back surface | Implemented prototype |
| Inbound job | `logistics.idp.inbound.job` | Unique source identity, retry/dead-letter state, PostgreSQL `SKIP LOCKED` claim | Implemented prototype |
| Task workspace | `project.task`, `mail.thread`, `mail.activity` | One linked collaboration task per aggregate; one-way state sync | Implemented |
| Files | `documents.document`, `is.attachment` | Original/generated binary storage and native metadata | Reused platform capability |
| ERP references | `purchase.order`, `purchase.order.line`, `account.move`, `account.move.line` | Native links when applicable; external records remain evidence snapshots | Reused platform capability |
| Parties/products | `res.partner`, `product.template`, `product.product`, UoM | Master-data references | Reused platform capability |

## Implemented canonical schema mapping

| Concern | Runtime model | Implemented responsibility | Phase |
|---|---|---|---|
| Document | `logistics.idp.document` | Source attachment/document, type/version/supersedes, SHA-256, MIME/pages/channel, duplicate disposition | 1 |
| Extraction run | `logistics.idp.extraction.run` | Document/run identity, provider/model/schema/prompt/config provenance, timings, raw hash, parsed payload, confidence/source spans | 1–2 |
| Check result | `logistics.idp.check.result` | Immutable required-check row: code, expected/actual/tolerance, verdict, rationale, run/policy linkage | 1–3 |
| Output | `logistics.idp.output` | E13/E15, broker package, Import Declaration, Shipping Plan, Gate Pass version/hash/status, idempotency and supersession | 1–3 |
| Policy source | `logistics.idp.policy.source` | Effective-dated source tier/citation/hash/version and demo lifecycle | 3 |
| Override | `logistics.idp.override` | Authorized reason/approval metadata, prior result linkage, separately hashed resulting decision | 3 |

These runtime models implement the smallest mapping previously authorized by `MODEL_GAP_REPORT.md`; evidence remains synthetic and non-production.

## Claim matrix

| Claim | Enterprise R&D sales-demo | Production/customer acceptance |
|---|---|---|
| Current prototype and synthetic development evidence | Allowed with explicit synthetic/non-production labels | Not sufficient |
| Deterministic offline demo after relevant phase gates pass | Allowed only for implemented, tested capabilities | Not sufficient |
| Legal advice or legal correctness | Prohibited | Deferred to qualified customer/legal review |
| Independent compliance certification/audit | Prohibited | Deferred to independent assessment |
| Formal Golden/UAT acceptance | Prohibited until executable corpus and formal gate exist | Deferred |
| Production readiness, SLA, DR, security certification | Prohibited | Deferred to pilot, hardening, rehearsal, and production gates |

## Phase boundary

Current implementation includes linked tasks, canonical document/run/check/output/policy/override models, Control Tower, authorization hardening, 198-case synthetic UAT with Golden48 subset, deterministic NFR, and local Playwright business E2E. It does not claim formal customer Golden/UAT acceptance, external OCR acceptance, production certification, SLA/DR, independent compliance review, or immutable RC status; checkout hashes remain current-working-tree evidence until committed.
