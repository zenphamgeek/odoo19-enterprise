from odoo import SUPERUSER_ID, api
from odoo.addons.insilos_logistics_idp.schema import ensure_database_invariants
from odoo.addons.insilos_logistics_idp.models.logistics_idp import _INTERNAL_POLICY_LOADER_TOKEN


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    env['logistics.idp.policy.source'].with_context(
        _logistics_policy_loader_token=_INTERNAL_POLICY_LOADER_TOKEN)._upgrade_effective_policy_history()
    ensure_database_invariants(cr)
