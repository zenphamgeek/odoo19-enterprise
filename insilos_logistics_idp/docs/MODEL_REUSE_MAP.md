# Model Reuse Map

Phase 0 decision: reuse native platform capabilities where they preserve ownership and invariants; authorize dedicated Logistics schema where properties or generic attachments cannot.

## Aggregate and reuse boundary

`logistics.idp.case` is the source of truth. One linked `project.task` is the human workspace. Case state, verdict, checks, decisions, and outputs remain aggregate-owned; task stages/properties must not become a second workflow.

| Logical entity/capability | Reused or dedicated model | Mapping | Status |
|---|---|---|---|
| Logistics Case | `logistics.idp.case` | Source identity, correlation, state/verdict, duplicate relation, evidence/decision/MES relations | Authorized; runtime prototype |
| Collaboration workspace | `project.task`, `mail.thread`, `mail.activity` | One `task_id` per case; chatter, activity, assignment, exception collaboration; one-way aggregate synchronization | Planned Phase 1 |
| Document binary | `documents.document`, `is.attachment` | Binary, native checksum/index, preview, access linkage | Reuse |
| Canonical document | planned `logistics.idp.document` | Case/source link, type, version/supersedes, content hash, MIME/pages/channel, duplicate status | Planned Phase 1 |
| Extraction run | planned `logistics.idp.extraction.run` | Document link; provider/model/schema/prompt/config versions; times; raw hash; parsed payload; confidence/source spans | Planned Phases 1–2 |
| Existing generic evidence | `logistics.idp.evidence` | Immutable canonical JSON snapshot and payload hash; retained for current prototype/general evidence | Authorized; runtime prototype |
| Check result | planned `logistics.idp.check.result` | Case/run/policy links; code, required, expected/actual/tolerance, verdict, rationale; immutable current/prior runs | Planned Phases 1–3 |
| Existing policy decision | `logistics.idp.policy.decision` | Immutable case verdict snapshot with policy version/effective interval/reason | Authorized; runtime prototype |
| Policy source | planned `logistics.idp.policy.source` | Effective-dated tier, citation, hash, version, supersedes, draft/active/retired demo lifecycle | Planned Phase 3 |
| Override | planned `logistics.idp.override` | Prior failed check/decision, reviewer/manager, mandatory reason and approval metadata, resulting decision hash | Planned Phase 3 |
| Output | planned `logistics.idp.output` | Type/version/hash/status/source run, idempotency key, supersession for customs and logistics outputs | Planned Phases 1–3 |
| Inbound processing | `logistics.idp.inbound.job` | Source idempotency, retry/dead-letter, worker claim | Authorized; runtime prototype |
| MES reference evidence | `logistics.idp.mes.reference` | Inbound source/version/effective provenance only; no execution/write-back | Authorized; runtime prototype |
| Supplier/customer/broker | `res.partner` | Identity and contact master data | Reuse |
| Material/UoM | `product.template`, `product.product`, UoM | Product and unit master data | Reuse |
| PO/PO line | `purchase.order`, `purchase.order.line` | Native transaction links when owned locally; external snapshots remain evidence | Reuse |
| Invoice/invoice line | `account.move`, `account.move.line` | Native vendor bill links when applicable; external snapshots remain evidence | Reuse |
| Email | `mail.message`, aliases, chatter | Original message metadata, attachments, thread collaboration | Reuse |

## Why properties are insufficient

Properties/tags remain suitable for presentation metadata. They do not provide typed one-to-many rows, foreign keys, immutable append-only history, effective-dated policy lineage, source-span provenance, output idempotency/supersession, required-check querying, or database concurrency constraints. Dedicated models are therefore justified for the six planned concerns above.

## Authorization boundary

This map authorizes the current runtime schema and the planned ownership boundaries. It does not assert planned models or `task_id` exist. Each later phase must satisfy its implementation and test gate before any capability claim.

## Trade Compliance WP0 field-level freeze

| Requirement | Existing model/field | Use | Current gap after WP1 |
|---|---|---|---|
| `TC-GOV-001` | `logistics.idp.policy.source.source_tier`, `citation`, `provenance`, `jurisdiction`, `regime`, `version`, `effective_from`, `effective_to`, `state`, `supersedes_id`, inherited `payload`, `payload_hash`, `audit_*` | WP2 imports bounded, validated, canonical candidates as draft only; company/global identity uses separate NULL-safe DB uniqueness; effective range has DB CHECK | Approval and activation remain later governed work |
| `TC-GOV-002` | `logistics.idp.case.company_id`, `effective_date`, `imported_at`, `provenance`; `logistics.idp.document.content_hash`, `current_run_id`; immutable `logistics.idp.evidence.payload/payload_hash` | Import validates existing canonical Compliance Context plus policy payload; deterministic structural diff reports candidate/selected-active hashes without mutation | Persisted execution snapshots remain later governed work; no new model justified |
| `TC-GOV-008` | Case/document company relations; record rules/ACL; immutable snapshot controlled create/write/unlink; payload SHA-256 | Trust-boundary size/shape/company/tier/citation/provenance/range checks; same identity+hash returns existing; conflicting hash rejected; race guarded by DB uniqueness | Four-eyes and activation remain later governed work |
| `TC-GOV-004` | `logistics.idp.case.evaluate_compliance_deadlines`; `logistics.idp.policy.source.select_effective_pack`; `logistics.idp.document.current_run_id/content_hash` | VN counterpart deadline only; normalized trigger/role/evidence context; exact policy/rule/cutoff hash; invalid or overlapping selected pack fails closed | No WP4+ family or external authority ingestion |
| `TC-GOV-007` | `logistics.idp.check.result` inherited `payload`, `payload_hash`, `audit_input_hash`; `policy_source_id`; immutable write/unlink; SQL unique audit input | Retry returns same snapshot; concurrent duplicate rejected; changed cutoff/context/policy creates immutable new result | No new model/table |
| `TC-GOV-005` | `logistics.idp.policy.source.preview_impact`; existing case/document/evidence fields and record rules | Ephemeral read-only WP4 preview compares exact draft/active hashes; explicit valid cutoff, horizon and record limit; all same-company non-terminal cases through the candidate window, including predating open cases; deterministic four outcomes/reasons; versioned input manifest binds case/document/run/evidence/policy/domain/output identity; separate output hash | VN counterpart rules only; no tariff/sanctions; UI remains deferred because no native action securely supplies explicit cutoff/context |
| `TC-GOV-006/008` | `logistics.idp.policy.activation`, policy ACL/record rules, immutable policy fields | Approved activation model implemented: manager submits signed transient envelope without a pending row; reviewer decision appends one immutable terminal event; activation/retirement is atomic; retry, tamper, self-approval, stale binding, blocker and concurrent overlap/decision races are covered | G5 mechanism `DONE_RUNTIME` local; legal content/oracle remains `BLOCKED_APPROVED_POLICY_DATASET`; production not claimed |

Historical decision context: WP1–WP4 deliberately kept direct activation fail-closed while `MODEL_GAP_REPORT` awaited explicit model approval. That decision was correct for those revisions; it is superseded for mechanism status by the approved and implemented single terminal-event model, not erased.

Runtime evidence 2026-08-12: module upgrade PASS; configuration activation lifecycle/replay/tamper/blocker tests and process-level concurrency evidence PASS; atomic rollback on terminal insert failure covered; legal correctness and production readiness not established; module `19.0.1.2.0`.

G0 baseline unchanged: 310 unique SRS IDs = 198 explicit + 112 stable unnumbered; 18 achieved/covered + 114 partial/not-covered + 178 missing. Existing gaps do not make a WP0–WP1 invariant impossible; no `MODEL_GAP_REPORT` update.
