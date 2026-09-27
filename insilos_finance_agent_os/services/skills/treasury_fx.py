# Part of Insilos. See LICENSE file for full copyright and licensing details.
"""Treasury & FX agent pack (E06) — AI giải thích engine, không thay engine.

Bốn engine deterministic (`exposure`, `liquidity`, `risk`, `scenario`) là
nguồn sự thật. Skill ở đây làm đúng một việc: gọi engine, đóng kết quả vào
fact có ref, và **không đụng vào con số**. Engine trả X thì agent nói X —
không làm tròn, không "ước lượng lại cho hợp lý".

Chiều ngược lại cũng được giữ: engine hỏng thì skill báo engine hỏng như một
sự kiện có cấu trúc (`engine_errors`), không bịa số thế chỗ — cùng họ với
bất biến "AI hỏng không dừng Treasury" đã gác ở chaos test domain.
"""

import json

from odoo.exceptions import UserError
from odoo.addons.insilos_treasury_market_risk.services import (
    ai_advisory,
    exposure_engine,
    liquidity_engine,
    risk_engine,
)

from . import base
from .base import skill

MODULE = 'insilos_treasury_market_risk'


def _engine_ref(engine_name, function_name):
    return 'engine:%s.%s' % (engine_name, function_name)


def _run(report, engine_name, function_name, func, *args, **kwargs):
    """Chạy một hàm engine; kết quả thành fact có ref, lỗi thành sự kiện.

    Một engine chết không được kéo cả báo cáo chết — và cũng không được im
    lặng: mục `engine_errors` là phần người đọc phải thấy trước tiên.
    """
    ref = _engine_ref(engine_name, function_name)
    try:
        value = func(*args, **kwargs)
    except Exception as exc:
        report['engine_errors'].append({
            'ref': ref,
            'error': '%s: %s' % (type(exc).__name__, exc),
        })
        return None
    report['facts'].append({'label': function_name, 'value': value, 'ref': ref})
    return value


@skill(base.READ)
def explain_fx_exposure(ctx, company, as_of=None):
    """Bức tranh FX exposure — từng số một là output engine nguyên trạng."""
    company.ensure_one()
    report = {'company': f'{company._name},{company.id}', 'facts': [], 'engine_errors': []}
    ids = [company.id]
    _run(report, 'exposure_engine', 'net_open_position',
         exposure_engine.net_open_position, ctx.env, ids, as_of=as_of)
    _run(report, 'exposure_engine', 'commitments',
         exposure_engine.commitments, ctx.env, ids, as_of=as_of)
    _run(report, 'exposure_engine', 'entity_exposure',
         exposure_engine.entity_exposure, ctx.env, ids, as_of=as_of)
    return report


@skill(base.READ)
def explain_liquidity(ctx, company):
    """Thanh khoản: opening + ladder + survival horizon, verbatim từ engine."""
    company.ensure_one()
    report = {'company': f'{company._name},{company.id}', 'facts': [], 'engine_errors': []}
    ids = [company.id]
    opening = _run(report, 'liquidity_engine', 'opening_liquidity',
                   liquidity_engine.opening_liquidity, ctx.env, ids)
    ladder = _run(report, 'liquidity_engine', 'ladder',
                  liquidity_engine.ladder, ctx.env, ids)
    if opening is not None and ladder is not None:
        # opening_liquidity trả list theo company; tổng là input mà
        # survival_horizon định nghĩa. Đây là phép cộng cấu trúc dữ liệu để
        # nối hai hàm engine, không phải "tính lại" số engine.
        opening_total = sum(row['amount'] for row in opening)
        _run(report, 'liquidity_engine', 'survival_horizon',
             liquidity_engine.survival_horizon,
             opening_total, ladder,
             liquidity_engine.min_cash_buffer(ctx.env, company))
    return report


@skill(base.READ)
def explain_portfolio_risk(ctx, company):
    """Risk metrics + limit utilization — cặp hàm engine, đúng thứ tự engine định."""
    company.ensure_one()
    report = {'company': f'{company._name},{company.id}', 'facts': [], 'engine_errors': []}
    metrics = _run(report, 'risk_engine', 'portfolio_metrics',
                   risk_engine.portfolio_metrics, ctx.env, company)
    if metrics is not None:
        _run(report, 'risk_engine', 'limit_utilization',
             risk_engine.limit_utilization, ctx.env, company, metrics)
    return report


@skill(base.DRAFT)
def stage_fx_hedge_proposal(ctx, project, eligible_exposure, existing_hedge,
                            spot, shock_pct, sources):
    """Tính alternatives bằng engine deterministic; chỉ dựng Decision Proposal."""
    alternatives = ai_advisory.hedge_alternatives(
        eligible_exposure, existing_hedge, spot, shock_pct, sources=sources)
    if not ai_advisory.is_grounded(alternatives):
        raise UserError('FX hedge proposal requires source references.')
    stage = ctx.env.ref(f'{MODULE}.stage_decision_proposal')
    return ctx.create_draft('project.task', {
        'name': 'FX hedge proposal',
        'project_id': project.id,
        'stage_id': stage.id,
        'description': 'Deterministic FX hedge alternatives; human selection required.',
        'treasury_recommendation': 'Human selection required; no execution requested.',
        'treasury_alternatives': json.dumps(alternatives, sort_keys=True),
        'treasury_evidence_references': '\n'.join(sources),
    })

