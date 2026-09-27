from odoo import api, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    @api.model
    def _load_pos_data_fields(self, config):
        return [
            *super()._load_pos_data_fields(config),
            "specific_property_product_pricelist",
        ]

    @api.model
    def _load_pos_data_read(self, records, config):
        return super()._load_pos_data_read(
            records.with_company(config.company_id),
            config,
        )
