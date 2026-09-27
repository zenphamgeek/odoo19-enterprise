# coding: utf-8
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class PosPaymentMethod(models.Model):
    _inherit = 'pos.payment.method'

    def _get_terminal_provider_selection(self):
        return super()._get_terminal_provider_selection() + [('six_iot', 'SIX')]

    def _get_payment_terminal_selection(self):
        return super()._get_payment_terminal_selection() + [('six_iot', 'SIX')] if hasattr(super(), '_get_payment_terminal_selection') else [('six_iot', 'SIX')]
