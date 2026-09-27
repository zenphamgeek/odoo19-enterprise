from odoo import models


class PosSession(models.Model):
    _inherit = "pos.session"

    def load_data(self, models_to_load):
        self.ensure_one()
        data = super(
            PosSession,
            self.with_company(self.company_id),
        ).load_data(models_to_load)

        if not models_to_load or "account.fiscal.position" in models_to_load:
            fiscal_position = self.config_id.default_fiscal_position_id
            if fiscal_position and fiscal_position.id not in {
                record["id"]
                for record in data["account.fiscal.position"]
            }:
                data["account.fiscal.position"].extend(
                    fiscal_position._load_pos_data_read(
                        fiscal_position,
                        self.config_id,
                    )
                )

        return data
