def migrate(cr, version):
    from odoo import api, SUPERUSER_ID
    from odoo.addons.insilos_logistics_idp.models.logistics_idp import _INTERNAL_POLICY_LOADER_TOKEN

    api.Environment(cr, SUPERUSER_ID, {})['logistics.idp.policy.source'].with_context(
        _logistics_policy_loader_token=_INTERNAL_POLICY_LOADER_TOKEN)._upgrade_effective_policy_history()
