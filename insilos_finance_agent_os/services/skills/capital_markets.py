# Part of Insilos. See LICENSE file for full copyright and licensing details.
"""Capital Markets agent pack (E05) — agent chỉ nói điều domain đã ghi.

Luật duy nhất, áp cho mọi skill trong pack: một con số chỉ được phát ngôn
khi nó trỏ về một record domain hoặc một kết quả MCP có lineage. Con số
không nguồn không được "đánh dấu là chưa chắc" — nó bị **từ chối phát ngôn**
(`UserError`), vì một báo cáo trộn số thật với số bịa độc hơn không có báo
cáo.
"""

from odoo.exceptions import UserError

from . import base
from .base import skill
from .. import decision_packet


def _fact(label, value, ref):
    """Một phát ngôn có nguồn. `ref` rỗng thì từ chối ngay tại chỗ tạo fact."""
    if not str(ref or '').strip():
        raise UserError(
            'Refusing to state %r: no evidence ref backs this figure.' % label)
    return {'label': label, 'value': value, 'ref': ref}


@skill(base.READ)
def explain_limit_breach(ctx, rule):
    """Giải thích một alert rule đã trigger — từ chính số liệu rule đã ghi.

    Chưa trigger thì không có gì để giải thích: trả lời thẳng, không suy
    diễn "có thể sắp breach".
    """
    rule.ensure_one()
    ref = f'{rule._name},{rule.id}'
    if not rule.triggered:
        return {'record': ref, 'triggered': False,
                'statement': 'Rule %s has not triggered; there is no breach to explain.' % rule.name}
    facts = [
        _fact('threshold', rule.threshold, ref),
        _fact('observed_value', rule.last_triggered_value, ref),
        _fact('triggered_on', str(rule.last_triggered_on), ref),
    ]
    return {
        'record': ref,
        'triggered': True,
        'kind': rule.kind,
        'portfolio': f'{rule.portfolio_id._name},{rule.portfolio_id.id}',
        'facts': facts,
        'statement': 'Rule %s (%s) breached: threshold %s, observed %s. '
                     'This is a threshold breach, not a recommendation.'
                     % (rule.name, rule.kind, rule.threshold, rule.last_triggered_value),
    }


@skill(base.DRAFT)
def prepare_ic_case(ctx, project, position, thesis):
    """Chuẩn bị case cho IC: draft ở stage đầu + decision packet đính kèm.

    Mọi số trong packet đọc từ `capital.position`; thesis là chữ của người,
    được ghi là chữ của người — không phải fact. Case nằm ở stage đầu và
    toàn bộ đường tới Execution vẫn thuộc về stage gate domain.
    """
    position.ensure_one()
    pos_ref = f'{position._name},{position.id}'
    inputs = [
        _fact('symbol', position.symbol, pos_ref),
        _fact('quantity', position.quantity, pos_ref),
        _fact('average_cost', position.average_cost, pos_ref),
        _fact('market_value', position.market_value, pos_ref),
        _fact('mark_status', position.mark_status, pos_ref),
    ]
    if position.mark_status != 'fresh':
        # Mark cũ vẫn được đưa vào case — nhưng phải nói thẳng, vì IC quyết
        # trên số này.
        inputs.append(_fact('mark_caveat',
                            'mark_status=%s; figures may not reflect the market' % position.mark_status,
                            pos_ref))
    case = ctx.create_draft('project.task', {
        'name': 'IC case: %s' % position.symbol,
        'project_id': project.id,
        'stage_id': project.type_ids[:1].id,
        'description': thesis,
    })
    packet = decision_packet.build(
        inputs,
        {'action': 'submit_to_ic', 'thesis': thesis},
        {'skill': 'prepare_ic_case', 'mode': base.DRAFT, 'case': f'{case._name},{case.id}'},
    )
    decision_packet.attach(ctx.env, case, packet)
    return case
