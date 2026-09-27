# Part of Insilos. See LICENSE file for full copyright and licensing details.
"""Alias -> real model, resolved at runtime instead of hard-coded (E02).

The agent layer must not name `capital.position` or `project.task` directly.
A tenant that installed a different mix of addons would then hit an
`KeyError` deep inside a skill, at the worst possible moment: mid-decision.

So each capability is asked for by alias. Two failure modes, deliberately
different:

- a **required** alias missing means the tenant cannot be written to safely.
  We do not guess an alternative table; we force the whole layer read-only.
  Guessing is how a governed system quietly grows a second, ungoverned
  ledger.
- an **optional** alias missing disables exactly one feature and says which.

`REGISTRY` is the only place a real model name appears in this layer.
"""

from odoo.exceptions import UserError

READ = 'READ'
WRITE = 'WRITE'


class Capability:
    """A resolved alias: which model backs it, and whether it is writable."""

    __slots__ = ('alias', 'models', 'required', 'feature')

    def __init__(self, alias, models, required, feature):
        self.alias = alias
        self.models = tuple(models)
        self.required = required
        self.feature = feature

    @property
    def model(self):
        """Primary model. Aliases backed by several models list the main one first."""
        return self.models[0]

    def __repr__(self):
        return f'Capability({self.alias}={self.models!r})'


# alias -> (candidate models, required, feature lost when absent)
#
# Candidates are tried in order; the first present in the registry wins, so a
# tenant with a partial install degrades instead of exploding. `required=True`
# entries have no fallback by design: if `rs.users` is gone we are not in an
# Insilos database at all.
SEMANTIC_ALIASES = (
    'business_record', 'document_evidence', 'conversation_audit',
    'task_or_review', 'approval_request', 'authorized_action_stage',
)

REGISTRY = {
    'business_record': (('capital.position',), True, None),
    'document_evidence': (('documents.document', 'ir.attachment'), True, None),
    'conversation_audit': (('mail.message',), True, None),
    'task_or_review': (('project.task',), True, None),
    'approval_request': (('project.task',), True, None),
    'authorized_action_stage': (('project.task',), True, None),
    'identity': (('res.users',), True, None),
    'party': (('res.partner',), True, None),
    'work_item': (('project.task',), True, None),
    'reporting': (('ir.actions.report',), True, None),
    'configuration': (('ir.config_parameter',), True, None),
    'automation': (('base.automation',), False, 'rule_automation'),
    'rule_target': (('capital.risk.limit', 'capital.alert.rule'), False, 'limit_rules'),
    'accounting_target': (('account.move.line',), False, 'ledger_drilldown'),
}

REQUIRED_ALIASES = tuple(a for a, (_m, req, _f) in REGISTRY.items() if req)


def resolve(env, alias):
    """First candidate model present in the registry, or None.

    Unknown alias is a programming error, not a tenant state: raise rather
    than return None, otherwise a typo reads as "capability absent" and the
    caller degrades for the wrong reason.
    """
    try:
        candidates, required, feature = REGISTRY[alias]
    except KeyError:
        raise UserError('Unknown capability alias: %s' % alias)
    present = [name for name in candidates if env.registry.get(name) is not None]
    if not present:
        return None
    return Capability(alias, present, required, feature)


def require(env, *aliases):
    """Resolve aliases or raise. Use before doing anything that writes."""
    resolved, missing = {}, []
    for alias in aliases:
        capability = resolve(env, alias)
        if capability is None:
            missing.append(alias)
        else:
            resolved[alias] = capability
    if missing:
        raise UserError(
            'Finance Agent OS capability missing: %s. The layer stays read-only '
            'until the backing model is installed.' % ', '.join(sorted(missing))
        )
    return resolved


def missing_required(env):
    return sorted(a for a in REQUIRED_ALIASES if resolve(env, a) is None)


def degraded_modes(env):
    """Optional alias missing -> the one feature that turns off."""
    return {
        alias: feature
        for alias, (_c, required, feature) in REGISTRY.items()
        if not required and resolve(env, alias) is None
    }


def is_read_only(env):
    return bool(missing_required(env))


def assert_writable(env):
    """Gate every write path in this layer.

    This is the teeth behind `on_missing_required_capability: read_only`.
    A log line would not be: code downstream would carry on and write.
    """
    missing = missing_required(env)
    if missing:
        raise UserError(
            'Finance Agent OS is read-only: required capability missing (%s).'
            % ', '.join(missing)
        )
