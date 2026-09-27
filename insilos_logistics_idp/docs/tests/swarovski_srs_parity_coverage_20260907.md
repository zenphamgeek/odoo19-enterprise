# Swarovski SRS parity coverage — 2026-09-07

## Kết quả

| Metric | Strict coverage | Evidence class | Verdict |
|---|---:|---|---|
| Requirement mapping/test coverage | **136/138 = 98.55%** | Synthetic, non-production | Executable baseline; 2 partial |
| Detailed UAT | **198/198 = 100%** | Synthetic ORM business acceptance | Pass |
| Golden UAT | **46/48 = 95.83%** | Synthetic ORM business acceptance | Partial; formal acceptance false |
| Internal reference-readiness | **PASS** | Synthetic self-oracle | Deterministic local readiness; không phải external parity |
| Observed Swarovski/reference parity | **N/A — blocked** | Authenticated external reference | Không được claim |

Không có tỷ lệ tổng hợp: gộp synthetic với observed/reference parity sẽ che blocker oracle/reference.

## Coverage calculation

- Requirement denominator: 138 requirement có `detailed_test_id`; 136 `passed`, 2 `partial`, 0 failed/not-run/skipped/unmapped.
- Golden denominator: 48; strict numerator chỉ gồm 46 `passed`. Hai `partial` là `UAT-40` và `UAT-41`.
- Mapping gate: `4A.6 → UAT-40/UAT-41`; `4A.5` không có Golden mapping. Gate fail-closed ngăn drift giữa deferred requirement và Golden IDs.
- Internal readiness self-oracle: SHA-256 oracle của 198 case synthetic; PASS khi corpus/manifest/UAT hashes khớp, Detailed 198/198, Golden 46 pass/2 partial, runtime Playwright PASS và claim boundary giữ `not_claimable`.
- Observed/reference denominator: chưa tồn tại. Cần expected fixture đã sanitize, phê duyệt độc lập, UI oracle, G4 strata no-attachment/one-PDF/multi-attachment.

## Partial requirements

| ID | Requirement | Reason |
|---|---|---|
| 4A.5 | Regulatory change lifecycle | Local lifecycle/re-evaluation có test; approved legal source, full lifecycle oracle và external evidence chưa có. |
| 4A.6 | Bitemporal/effective-date behavior | Local effective/recorded selection có test; external independent oracle chưa có. |

## Verification

| Gate | Result |
|---|---|
| `build_sanitized_corpus.py --verify` | PASS — detailed=198, Golden=48; deferred mapping gate PASS |
| `verify_reference_corpus_registry.py` | PASS |
| `development_uat_harness.py` | PASS — detailed=198 |
| `development_uat_harness.py --golden` | PASS — 46 pass, 2 partial |
| Playwright business | PASS — 74 checks; 375/768/1440, console/page/network errors `0` |
| Authenticated read-only exporter canary | PASS — source invariant unchanged |

## Authenticated reference evidence

Read-only authenticated exports ran against 100 source records:

- `exactly-one` stratum: 100 records, 100 attachments downloaded, 0 rejected; source invariant unchanged.
- `multi` stratum: 0 observed; no records exported.
- `zero` canary: source invariant unchanged; no selected records.
- API/UI field parity: not evaluated. Chưa có independently-approved expected fixture/UI oracle.

Artifacts nằm ngoài Git/quarantine:

- [One-attachment report](file:///home/zen/insilos-migration-quarantine/digiforce-idp-g4-one/report-snapshot.json)
- [Multi-attachment report](file:///home/zen/insilos-migration-quarantine/digiforce-idp-g4-multi/report-snapshot.json)
- [Zero-attachment report](file:///home/zen/insilos-migration-quarantine/digiforce-idp-g4/report-snapshot.json)

## Screenshot evidence

Artifact local, synthetic Playwright fixture, không phải evidence functional parity Swarovski:

- [Desktop screenshot](file:///tmp/swarovski-parity-evidence-final/overview-desktop.png)
- [Mobile screenshot](file:///tmp/swarovski-parity-evidence-final/overview-mobile.png)
- [Events](file:///tmp/swarovski-parity-evidence-final/events.json)
- [SHA-256 manifest](file:///tmp/swarovski-parity-evidence-final/sha256.json)

## Claim boundary

SRS nguồn [SRS v1.4](file:///home/zen/insilos_ee/docs/industries/Insilos_Vertical_IDP_Logistics_SRS_v1.4_Trade_Compliance_MES_Boundary.md#L306-L318). Có read-only external retrieval evidence, nhưng không có multi-attachment stratum hoặc independent expected/UI oracle. Kết luận đúng: **98.55% executable synthetic requirement coverage**, không phải “Swarovski parity achieved”.
