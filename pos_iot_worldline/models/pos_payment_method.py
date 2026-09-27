from odoo import models


class PosPaymentMethod(models.Model):
    _inherit = 'pos.payment.method'

    def _get_terminal_provider_selection(self):
        return super()._get_terminal_provider_selection() + [('worldline', 'Worldline')]

    def _get_payment_terminal_selection(self):
        return super()._get_payment_terminal_selection() + [('worldline', 'Worldline')] if hasattr(super(), '_get_payment_terminal_selection') else [('worldline', 'Worldline')]
