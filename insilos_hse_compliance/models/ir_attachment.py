# -*- coding: utf-8 -*-
# Part of Insilos. See LICENSE file for full copyright and licensing details.

from odoo import models, _
from odoo.exceptions import UserError


class HSEEvidenceAttachment(models.Model):
    _inherit = 'ir.attachment'

    def _is_governed_evidence(self):
        # The relation is created by this module upgrade; XML attachment loading runs before it exists.
        self.env.cr.execute("SELECT to_regclass('is_hse_obligation_evidence_attachment_rel')")
        if not self.env.cr.fetchone()[0]:
            return False
        protected = self.env['is.hse.obligation'].search([
            ('compliance_status', '=', 'compliant'),
            ('evidence_attachment_ids', 'in', self.ids),
        ])
        if protected:
            return True
        if 'is.esg.facility.scorecard' in self.env:
            return bool(self.env['is.esg.facility.scorecard'].search([
                ('state', 'in', ('audited', 'published')),
                ('evidence_attachment_ids', 'in', self.ids),
            ]))
        return False

    def write(self, vals):
        if self._is_governed_evidence():
            raise UserError(_('Evidence linked to approved HSE obligations or audited ESG scorecards is immutable.'))
        return super().write(vals)

    def unlink(self):
        if self._is_governed_evidence():
            raise UserError(_('Evidence linked to approved HSE obligations or audited ESG scorecards cannot be deleted.'))
        return super().unlink()
