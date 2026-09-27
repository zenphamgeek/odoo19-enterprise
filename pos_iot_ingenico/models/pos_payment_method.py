from odoo import models


class PosPaymentMethod(models.Model):
    _inherit = 'pos.payment.method'

    def _get_terminal_provider_selection(self):
        return super()._get_terminal_provider_selection() + [('ingenico', 'Ingenico')]

    def _get_payment_terminal_selection(self):
        return super()._get_payment_terminal_selection() + [('ingenico', 'Ingenico')] if hasattr(super(), '_get_payment_terminal_selection') else [('ingenico', 'Ingenico')]
