# Model Gap Report — Trade Compliance durable activation

**Trạng thái:** `BLOCKED_MODEL_GAP_APPROVAL` cho riêng durable four-eyes activation và activation-grade immutable preview binding. Không chặn WP4 ephemeral impact preview. Mọi activation mới fail closed cho toàn bộ authority class và user, kể cả Customer Reference/Demo/manager/admin/integration; native form không có Activate. Existing active Customer Reference chỉ tiếp tục read-only operational runtime; retire bị giới hạn rõ state/class/group. Không thêm schema/model/table.

**Authority:** [Trade Compliance Governed Policy execution plan](../../../../.trae/documents/trade_compliance_governed_policy_execution_plan.md), mục Model Gap trigger, WP4–WP5, migration/rollback và blocker handling.

## 1. Kết luận model — lịch sử quyết định, nay đã triển khai

**Có, model mới thực sự cần thiết và đã được phê duyệt/triển khai** để chứng minh đồng thời các invariant bắt buộc sau tại DB/transaction boundary:

1. maker và checker là hai actor khác nhau, đúng role và company;
2. checker phê duyệt đúng bytes của candidate policy, semantic diff và đúng immutable preview;
3. preview được bind bằng hash tới candidate/active policy, payload, cutoff và event activation cụ thể;
4. approval không thể bị sửa, xóa, dùng lại hoặc áp vào payload/preview đã thay đổi;
5. một activation event chỉ có một identity, retry idempotent, concurrent activation không tạo hai active version hoặc partial lifecycle;
6. predecessor chỉ bị retire/supersede trong cùng transaction sau khi mọi gate còn hợp lệ.

Không có yêu cầu durable activation thì không cần model. WP4 vẫn có thể tính read-only preview và ghi generic immutable evidence phục vụ phân tích/G4; chỉ đường dùng preview đó để authorize activation bị chặn.

## 2. Bằng chứng registry/field đã thử

Đối chiếu source hiện tại ngày 2026-08-12:

| Registry/model | Field/cơ chế hiện hữu đã thử | Khả năng dùng lại | Gap còn lại |
|---|---|---|---|
| `logistics.idp.policy.source` | `company_id`, `code`, `version`, `jurisdiction`, `regime`, `source_tier`, `citation`, `provenance`, `effective_from`, `effective_to`, `state`, `supersedes_id`; inherited `payload`, `payload_hash`, `audit_actor_id`, `audit_service`, `audit_input_hash` | Candidate bytes/hash, authority, effective window, lifecycle policy | Không có maker/checker, approval timestamp/reason, preview hash, event identity. `action_activate` hiện chỉ kiểm tra manager + overlap rồi ghi `state='active'`. |
| `logistics.idp.immutable.snapshot` | canonical JSON; SHA-256 `payload_hash`; controlled create; external `write`/`unlink` bị chặn | Nền append-only phù hợp cho artifact | Một snapshot đơn không có typed FK/constraint cho hai actor, policy/company/status/event identity; inherited internal write path vẫn không thay thế lifecycle event riêng. |
| `logistics.idp.evidence` | `case_id`, `category`, `source_reference`, `status`; unique `(case_id, category, payload_hash)` | Generic immutable WP4 preview evidence theo case | Preview policy có thể bao phủ nhiều case hoặc zero case; bắt buộc `case_id`; uniqueness không bind policy/event; JSON không tạo FK/DB CHECK maker ≠ checker. |
| `logistics.idp.policy.decision` | `case_id`, `policy_code`, `policy_version`, effective range, `verdict`, `reason`, immutable payload/hash | Snapshot quyết định của từng case sau evaluation | Không phải policy approval; bắt buộc case; không có candidate FK, actor pair, preview/event identity. |
| `logistics.idp.check.result` | `case_id`, `policy_source_id`, `code`, `verdict`, `rationale`, `citation`; unique `audit_input_hash` | Immutable result cho một compliance input | Là evaluation result theo case, không phải approval/activation. Một hash duy nhất không biểu diễn actor separation, lifecycle hoặc exact preview binding. |
| `logistics.idp.exception` | Workflow exception hiện hữu | Điều phối review ngoại lệ | Mutable workflow record; semantics không phải immutable policy activation event. |
| `mail.activity`, chatter/`mail.message` | assignee, completion, author/time, text | Nhắc việc và cộng tác | Activity có thể reassigned/completed/cancelled; chatter là narrative. Không có typed policy/preview hashes, NULL-safe event uniqueness, maker/checker CHECK, atomic state transition hoặc replay prevention. |
| ACL/record rules | Reviewer, manager, auditor, admin; policy company rule global/company; policy source manager create-only, auditor read-only | Actor authorization và tenant visibility cơ sở | Group membership chỉ chứng minh role tại lúc gọi; không lưu durable role/company evidence của cả hai actor trong event. |

Nguồn: [`models/logistics_idp.py`](../models/logistics_idp.py), [`security/is.model.access.csv`](../security/is.model.access.csv), [`security/logistics_idp_security.xml`](../security/logistics_idp_security.xml), [`MODEL_REUSE_MAP.md`](MODEL_REUSE_MAP.md).

## 3. Vì sao JSON/activity/chatter/case evidence/decision/check không enforce được

- **Policy JSON:** canonical hash bảo vệ bytes, không tạo FK tới users/company/policy/preview; PostgreSQL không thể áp `maker_id <> checker_id`, role/company validity, event uniqueness hoặc lock lifecycle lên key nằm trong free-form JSON một cách an toàn qua ORM.
- **`mail.activity`/chatter:** workflow collaboration, không phải authorization ledger. Completion/message không atomically khóa exact policy/preview hash; record có lifecycle riêng, quyền sửa/xóa, reassignment và không có constraint chống replay/concurrency.
- **Case evidence:** yêu cầu `case_id`; preview là tập tác động policy-level. Nhét approval vào evidence làm sai ownership, không thể enforce một approval cho một candidate/event, đặc biệt preview zero-case.
- **Policy decision:** kết quả case-level, được tạo sau evaluation; dùng làm approval đảo chiều dependency và trộn governance event với business verdict.
- **Check result:** typed cho rule evaluation, không cho activation lifecycle; `audit_input_hash` uniqueness không chứng minh hai actor hoặc event transition.
- **Thêm field trực tiếp vào `policy.source`:** tối thiểu về số table nhưng phá append-only semantics vì submit/approve/activate cần mutate cùng row; không lưu được failed/rejected/reversion attempts; stale/replay audit mơ hồ; concurrent actor updates khó ràng buộc thành một immutable event.

Kết luận: payload tự do chỉ là evidence content. Nó không thay thế typed relational integrity/security boundary.

## 4. Schema tuyệt đối tối thiểu đã được duyệt và triển khai

Một model duy nhất **`logistics.idp.policy.activation`**, kế thừa `logistics.idp.immutable.snapshot`. Không thêm model preview/approval riêng.

### Exact fields

| Field | Type/required | Mục đích |
|---|---|---|
| `event_uuid` | UUID/Char, required, readonly | Stable external/idempotency event identity. |
| `company_id` | Many2one `rs.company`, required, readonly, index | Tenant boundary được chụp tại event. Global policy activation vẫn diễn ra dưới một company quản trị rõ ràng. |
| `policy_source_id` | Many2one `logistics.idp.policy.source`, required, readonly, `ondelete='restrict'`, index | Exact candidate row. |
| `predecessor_policy_id` | Many2one cùng model policy source, optional, readonly, `ondelete='restrict'` | Exact active rollback/supersession target tại submit. |
| `policy_hash` | Char(64), required, readonly, index | Copy exact candidate `payload_hash`, recheck trước approve/activate. |
| `payload_hash` | Char(64), required, readonly | Hash canonical activation payload gồm diff/citation/effective metadata; không đồng nghĩa policy hash. |
| `preview_hash` | Char(64), required, readonly, index | Hash canonical immutable WP4 preview bytes. |
| `preview_input_hash` | Char(64), required, readonly | Bind candidate hash, active/predecessor hash, cutoff/domain/context snapshot. |
| `maker_id` | Many2one `rs.users`, required, readonly, index | Actor submit. |
| `maker_at` | Datetime, required, readonly | Transaction time submit. |
| `checker_id` | Many2one `rs.users`, required, readonly, index | Actor approve. |
| `checked_at` | Datetime, required, readonly | Transaction time approve. |
| `reason` | Text, required, readonly | Approval rationale; không chứa secret/PII. |
| `status` | Selection `activated|rejected|failed`, required, readonly, index | Terminal append-only outcome. Không dùng mutable `draft/submitted/approved`. |
| `activated_at` | Datetime, optional, readonly | Bắt buộc iff `status='activated'`. |
| `failure_code` | Char, optional, readonly | Machine-safe reason cho rejected/failed; không log secret. |

Inherited fields giữ nguyên: canonical `payload`, `payload_hash`, `audit_actor_id`, `audit_service`, `audit_input_hash`. Nếu framework không cho khai báo lại `payload_hash`, dùng inherited field làm activation payload hash; không tạo field trùng.

**Deliberate minimum:** submit/approve intent trước terminal event nằm trong transient request/native activity. Chỉ khi checker hành động mới append một terminal immutable record và, nếu hợp lệ, activate atomically. Không cần mutable approval-request model. Nếu yêu cầu durable pending queue/withdrawal/SLA độc lập xuất hiện, phải mở Model Gap khác.

### Constraints bắt buộc

DB constraints, không chỉ Python:

1. `CHECK (maker_id <> checker_id)`.
2. `UNIQUE (event_uuid)` chống duplicate event/retry.
3. `UNIQUE (company_id, policy_source_id, policy_hash, preview_hash) WHERE status = 'activated'` hoặc equivalent partial unique index: cùng exact approval không activate hai lần.
4. SHA-256 format checks cho `policy_hash`, `payload_hash`, `preview_hash`, `preview_input_hash`: 64 lowercase hex.
5. Terminal-time consistency: `status='activated'` iff `activated_at IS NOT NULL`; rejected/failed không có `activated_at`; `checked_at >= maker_at`; `activated_at >= checked_at` khi activated.
6. Candidate khác predecessor: `predecessor_policy_id IS NULL OR predecessor_policy_id <> policy_source_id`.
7. FK `restrict`; model-level transactional checks xác nhận policy/company/jurisdiction/regime/effective identity và current hashes. Cross-table role/company/state invariants không thể là plain CHECK nên phải recheck dưới lock trong service.
8. Existing active non-overlap phải được nâng thành DB exclusion/partial constraint theo NULL-safe company + code + jurisdiction + regime + date range nếu PostgreSQL/framework migration cho phép; nếu chưa có, activation dùng advisory/key lock và locked conflict query. G5 không được PASS chỉ bằng pre-write `search_count`.

### Indexes tối thiểu

- Unique B-tree `event_uuid`.
- Composite B-tree `(company_id, policy_source_id, status)`.
- B-tree `policy_hash`, `preview_hash` phục vụ audit/reconciliation.
- Partial unique activated identity như trên.
- Không index `reason`, payload JSON hoặc actor/time riêng ngoài maker/checker nếu chưa có query thực tế.

## 5. Append-only lifecycle và atomic activation

1. Maker tạo canonical candidate/diff/preview input; WP4 preview evidence immutable được băm. Không đổi policy state.
2. Checker request activation bằng `event_uuid`, exact hashes, reason. Service xác thực group/company và `maker_id <> checker_id`.
3. Trong **một DB transaction**, lấy key-level advisory lock hoặc lock candidate + conflicting active rows theo deterministic order.
4. Re-read candidate; xác nhận còn `draft`, exact `policy_hash`, citation/effective date, preview hash/input hash, predecessor, không blocker/overlap, role/company hiện hành.
5. Append terminal `logistics.idp.policy.activation` record. Với outcome activated, retire predecessor, set supersession và activate candidate trong cùng transaction. Bất kỳ lỗi nào rollback toàn bộ; predecessor giữ active. Với business rejection cần durable evidence, append `rejected` nhưng không đổi policy.
6. Retry cùng `event_uuid` trả đúng terminal record; event UUID khác cho cùng exact activated identity bị unique constraint chặn.
7. `write()`/`unlink()` luôn bị từ chối, kể cả admin thông thường. Sửa sai bằng candidate/event mới; không sửa lịch sử.

Không lưu intermediate mutable status. Đây là trần tối giản; thêm request model chỉ khi pending approval phải durable/queryable trước checker action.

## 6. ACL và record rules

- Operator, Integration: không read/create/write/unlink.
- Reviewer: read trong allowed companies; không direct create/write/unlink. Chỉ controlled activation service nhận checker action.
- Manager: read; không direct create/write/unlink. Maker submission không tự cấp quyền activate.
- Auditor: read-only trong allowed companies.
- Vertical Administrator: read-only mặc định; không bypass maker/checker hoặc immutability.
- Controlled service: create-only qua unforgeable internal context; actor lấy từ authenticated `env.user`, không nhận actor IDs từ client.
- Global record rule: `[('company_id', 'in', company_ids)]`. Policy global không cho event global/NULL company.
- Export/chatter phải redaction; không ghi token, credential, signed/query URL, raw restricted policy bytes.

## 7. Migration, rollout, rollback

### Migration/rollout

1. Chỉ sau explicit approval: backup + rehearsal; inventory policy rows/states/hashes, overlap, historical decisions, current ACL.
2. Tạo table/constraints/indexes/ACL/rule. Không backfill approval cho activation cũ: provenance hai actor và preview binding không tồn tại, không được suy diễn.
3. Existing active policies giữ nguyên, gắn trạng thái migration là **legacy active/unattested** trong rollout artifact, không tạo giả event.
4. Mọi activation mới bắt buộc đi service mới; khóa direct `action_activate` cũ. Verify row counts/hashes, orphan/FK, ACL negatives, self-approval/replay/cross-company/concurrency.
5. Chỉ nâng G5 sau approved policy dataset/oracle và machine evidence pass.

### Rollback

- Trước production: downgrade/restore rehearsal riêng, xác nhận policy rows/hashes/history không mất.
- Runtime rollback policy: tạo corrective/reversion candidate và activation event mới qua four-eyes; không delete/modify activation/policy history.
- Schema rollback chỉ khi chưa có durable events. Khi đã có event, giữ table read-only; không drop làm mất audit chain. Code rollback phải fail closed, không bật lại manager-only direct activation.
- Failed deployment/transaction giữ predecessor active; không partial retire/activate.

## 8. Alternatives bị loại

| Alternative | Lý do loại |
|---|---|
| Chỉ canonical JSON trong `logistics.idp.evidence` | Không có policy-level ownership/FK, actor CHECK, event uniqueness, typed ACL; bắt buộc case. |
| `mail.activity` + chatter làm approval ledger | Mutable/reassignable; không hash-bind preview/policy; không atomic với activation; không chống replay/race. |
| Thêm maker/checker/preview fields vào `policy.source` | Mutate source row, mất attempts/history; stale approval và concurrency khó chứng minh; trộn artifact với event. |
| Dùng `policy.decision` | Case verdict semantics; bắt buộc case; sai lifecycle và dependency. |
| Dùng `check.result` | Rule evaluation semantics; không có dual-control/event lifecycle. |
| Hai model request + approval/activation | Enforce được nhưng vượt minimum hiện tại. Chỉ cần nếu pending approval phải durable/queryable. |
| Không persist, chỉ transaction log | Không audit/reconcile durable; log không FK/ACL/immutability contract. |

## 9. Approval checkpoint — đã giải quyết cho cơ chế

**Quyết định lịch sử:** model duy nhất `logistics.idp.policy.activation` cùng constraints/ACL/migration đã được phê duyệt và triển khai. Checkpoint cũ `BLOCKED_MODEL_GAP_APPROVAL` không còn là trạng thái mechanism.

Hiện tại:

- G5 mechanism `DONE_RUNTIME` local; terminal-only append-only event và signed transient envelope đã triển khai;
- concurrency evidence chứng minh same-event idempotency, overlap serialization, blocker/activation ordering, approve/reject race và atomic rollback;
- WP4 preview được hash-bind vào activation envelope/event; không có mutable pending approval row;
- historical active rows không bị sửa/xóa hoặc suy diễn approval;
- `BLOCKED_APPROVED_POLICY_DATASET` vẫn áp dụng cho legal content/oracle;
- day-10 runtime/SRS hiện dùng `today >= deadline` là overdue, trong khi legal correctness chưa được authority độc lập xác minh; unresolved, không chọn runtime làm legal truth;
- không tuyên bố production compliance. Module `19.0.1.2.0`.
