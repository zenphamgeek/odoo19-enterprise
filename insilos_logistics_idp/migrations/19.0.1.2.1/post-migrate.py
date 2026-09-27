def migrate(cr, version):
    from odoo import api, SUPERUSER_ID

    api.Environment(cr, SUPERUSER_ID, {})['res.users']._normalize_legacy_saigon_timezone()
