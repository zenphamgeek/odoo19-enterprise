# Part of Insilos. See LICENSE file for full copyright and licensing details.
"""Bốn skill lõi (E04) — mỗi skill là một mức quyền, không hơn.

Mọi con số trả về đều đọc từ field của model domain, kèm tham chiếu record.
Skill không tính lại và không suy diễn: nếu domain không có số, câu trả lời
là "không có số", không phải một ước lượng.
"""

import json

from odoo.exceptions import UserError

from .. import capability
from . import base
from .base import skill


@skill(base.READ)
def explain_position(ctx, position):
    """Giải thích một vị thế bằng chính số liệu governed của nó.

    READ: không ghi gì. Mọi giá trị kèm nguồn (field nào, record nào) để
    người đọc — và decision packet — truy ngược được.
    """
    position.ensure_one()
    return {
        'record': f'{position._name},{position.id}',
        'symbol': position.symbol,
        'quantity': position.quantity,
        'average_cost': position.average_cost,
        'last_price': position.last_price,
        'mark_status': position.mark_status,
        'market_value': position.market_value,
        'unrealised_pnl': position.unrealised_pnl,
        'price_source': position.price_source or None,
        'price_as_of': str(position.price_as_of) if position.price_as_of else None,
        # Giá thiếu là khoảng trống được nói thẳng, không phải số 0.
        'caveats': [] if position.mark_status == 'fresh' else
                   ['mark_status is %s — figures may not reflect the market' % position.mark_status],
    }


@skill(base.REPORT)
def evidence_pack(ctx, work_item, title, facts):
    """Đóng gói facts thành evidence gắn vào work item (project.task).

    REPORT: được ghi attachment + message, không hơn. Mỗi fact bắt buộc có
    `ref` trỏ về record nguồn — fact không nguồn bị từ chối cả gói, vì một
    evidence pack lẫn một số mồ côi là thứ tệ hơn không có pack.
    """
    work_item.ensure_one()
    orphans = [f for f in facts if not str(f.get('ref') or '').strip()]
    if orphans:
        raise UserError(
            'Evidence pack refused: %d fact(s) carry no source ref.' % len(orphans))
    payload = json.dumps({'title': title, 'facts': facts}, sort_keys=True,
                         ensure_ascii=False, indent=2)
    return ctx.post_evidence(
        work_item,
        body='Evidence pack: %s (%d facts, all source-referenced)' % (title, len(facts)),
        attachment_name='evidence_pack.json',
        attachment_raw=payload.encode(),
    )


@skill(base.DRAFT)
def draft_proposal(ctx, project, name, rationale):
    """Dựng một decision case nháp ở stage đầu tiên của workflow.

    DRAFT: tạo bản ghi thật nhưng ở trạng thái mà mọi bước tiếp theo đều cần
    người. Stage đích cố định là stage đầu — skill không được chọn stage.
    """
    capability.require(ctx.env, 'work_item')
    first_stage = project.type_ids[:1]
    return ctx.create_draft('project.task', {
        'name': name,
        'project_id': project.id,
        'stage_id': first_stage.id,
        'description': rationale,
    })


@skill(base.CONTROLLED)
def execute_governed_action(ctx, record, method_name, *args, **kwargs):
    """Chạy một governed action — dưới đầy đủ gate của domain.

    CONTROLLED: mức cao nhất của skill, và vẫn thấp hơn con người. Không
    sudo, không đổi user; stage gate/ACL từ chối thì exception nổ ra ngoài.
    """
    return ctx.run_governed(record, method_name, *args, **kwargs)
