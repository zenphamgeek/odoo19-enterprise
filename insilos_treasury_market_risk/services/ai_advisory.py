# Part of Insilos. See LICENSE file for full copyright and licensing details.
"""AI-001..005: the numbers an advisory answer is allowed to contain.

A language model can phrase an answer any way it likes, but it must not be the
thing that decides what the market did or how large a hedge should be. These
functions produce the classification, the attribution and the arithmetic, each
carrying its own evidence, so an ungrounded sentence has nowhere to hide.
"""

# AI-001: a closed taxonomy. A regime label outside this set is not a nuance,
# it is an invention.
REGIME_TAXONOMY = ('risk_off', 'high_volatility', 'stress', 'neutral')
MODEL_VERSION = 'insilos-regime-rules-1'

# AI-002: the four ways today's numbers hurt are not interchangeable. A P&L
# loss is realised money, a concentration breach is a policy state, an FX move
# is a balance-sheet translation and a liquidity gap is a future funding need.
ATTRIBUTION_KINDS = ('pnl_loss', 'concentration_breach', 'balance_sheet_exposure', 'funding_risk')


def market_regime(features):
    """Classify the session from observed features only.

    `features` carries what was actually measured: index_change_pct,
    worst_name_change_pct, volume_ratio, as_of, and a list of evidence
    references. Anything absent stays absent; it is never assumed.
    """
    missing = [key for key in ('index_change_pct', 'as_of') if features.get(key) is None]
    if missing:
        # AI-003: without an observation there is no regime, and inventing one
        # would be the single most damaging thing this function could do.
        return {
            'regime': None, 'confidence': 0.0, 'model_version': MODEL_VERSION,
            'as_of': features.get('as_of'), 'evidence': features.get('evidence') or [],
            'unavailable_inputs': missing,
        }
    index = features['index_change_pct']
    worst = features.get('worst_name_change_pct', 0.0)
    volume_ratio = features.get('volume_ratio', 1.0)
    if index <= -2.0 and worst <= -5.0:
        regime, confidence = 'risk_off', 0.8 if volume_ratio >= 1.5 else 0.6
    elif worst <= -5.0 or volume_ratio >= 2.0:
        regime, confidence = 'high_volatility', 0.6
    elif index <= -5.0:
        regime, confidence = 'stress', 0.7
    else:
        regime, confidence = 'neutral', 0.5
    return {
        'regime': regime, 'confidence': confidence, 'model_version': MODEL_VERSION,
        'as_of': features['as_of'], 'evidence': features.get('evidence') or [],
        'observed': {'index_change_pct': index, 'worst_name_change_pct': worst, 'volume_ratio': volume_ratio},
        'unavailable_inputs': [],
    }


def risk_attribution(drivers):
    """AI-002: one row per driver, each kept in its own category.

    `drivers`: [{'name', 'kind', 'amount', 'source'}]. Ranking happens inside a
    category only, because ranking a funding gap against a P&L loss produces a
    league table of unrelated things and a confidently wrong headline.
    """
    unknown = sorted({driver['kind'] for driver in drivers} - set(ATTRIBUTION_KINDS))
    if unknown:
        raise ValueError('Unknown attribution kind(s): %s' % ', '.join(unknown))
    by_kind = {}
    for driver in drivers:
        by_kind.setdefault(driver['kind'], []).append(driver)
    return {
        kind: sorted(rows, key=lambda row: abs(row['amount']), reverse=True)
        for kind, rows in by_kind.items()
    }


def primary_pnl_driver(drivers):
    """The largest realised loss, and only that. Nothing else is 'the loss'."""
    losses = risk_attribution(drivers).get('pnl_loss') or []
    return losses[0] if losses else None


def market_data_availability(mark_status, last_valid_as_of):
    """AI-003: what may be said when the feed is down.

    Returns the sentence's ingredients, never a price. A caller that wants a
    current quote from a stale book gets `quote: None`, on purpose.
    """
    usable = mark_status == 'fresh'
    return {
        'usable': usable,
        'mark_status': mark_status,
        'last_valid_as_of': last_valid_as_of,
        'quote': None if not usable else 'use the marked price',
        'statement': 'Market data is %s. Last valid timestamp: %s.' % (mark_status, last_valid_as_of or 'none'),
    }


def hedge_recommendation(eligible_exposure, existing_hedge, target_ratio_pct, sources):
    """AI-005: an amount that carries its own derivation.

    Every field in `basis` is an input a reader can check, and `additional_hedge`
    is nothing but arithmetic over them.
    """
    target_amount = eligible_exposure * target_ratio_pct / 100.0
    additional = max(target_amount - existing_hedge, 0.0)
    return {
        'additional_hedge': additional,
        'basis': {
            'eligible_exposure': eligible_exposure,
            'existing_hedge': existing_hedge,
            'target_ratio_pct': target_ratio_pct,
            'target_amount': target_amount,
        },
        'sources': list(sources),
    }


def hedge_alternatives(eligible_exposure, existing_hedge, spot, shock_pct, ratios=(70.0, 80.0, 100.0), sources=()):
    """FX-004: the same exposure priced at several hedge ratios.

    Choosing between 70, 80 and 100 percent is a policy and cost judgement, so
    the choice is left to a person. The arithmetic behind each option is not a
    judgement, so it is computed here rather than written in prose.
    """
    rate_delta = spot * shock_pct / 100.0
    options = []
    for ratio in ratios:
        required = eligible_exposure * ratio / 100.0
        residual = eligible_exposure - required
        options.append({
            'ratio_pct': ratio,
            'required_hedge': required,
            'incremental_hedge': max(required - existing_hedge, 0.0),
            'residual_exposure': residual,
            'stress_loss': residual * rate_delta,
        })
    return {
        'options': options,
        'basis': {
            'eligible_exposure': eligible_exposure, 'existing_hedge': existing_hedge,
            'spot': spot, 'shock_pct': shock_pct, 'rate_delta': rate_delta,
        },
        'sources': list(sources),
    }


def is_grounded(recommendation):
    """A recommendation with no source, or a number with no basis, is not usable."""
    basis = recommendation.get('basis') or {}
    return bool(recommendation.get('sources')) and all(value is not None for value in basis.values())
