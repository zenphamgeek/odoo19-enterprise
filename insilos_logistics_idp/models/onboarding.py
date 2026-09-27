from odoo import api, models


class LogisticsOnboarding(models.Model):
    _inherit = 'onboarding.onboarding'

    @api.model
    def action_close_panel_logistics_idp(self):
        self.action_close_panel('insilos_logistics_idp.onboarding_logistics_idp')


class LogisticsOnboardingStep(models.Model):
    _inherit = 'onboarding.onboarding.step'

    @api.model
    def _open_logistics_cases(self, domain, context=None):
        action = self.env['ir.actions.actions']._for_xml_id('insilos_logistics_idp.action_logistics_cases')
        action.update(domain=domain, context=context or {'search_default_my_cases': 1})
        return action

    @api.model
    def action_open_logistics_intake(self):
        return self._open_logistics_cases([('state', '=', 'intake')])

    @api.model
    def action_open_logistics_collecting(self):
        return self._open_logistics_cases([('state', '=', 'collecting')])

    @api.model
    def action_open_logistics_processing(self):
        return self._open_logistics_cases([('state', '=', 'processing')])

    @api.model
    def action_open_logistics_review(self):
        return self._open_logistics_cases([('state', '=', 'review')])

    @api.model
    def action_open_logistics_exceptions(self):
        return self._open_logistics_cases([('state', 'in', ('blocked', 'waiting_external'))])

    @api.model
    def action_open_logistics_completion(self):
        return self._open_logistics_cases([('state', 'in', ('ready', 'completed'))])
