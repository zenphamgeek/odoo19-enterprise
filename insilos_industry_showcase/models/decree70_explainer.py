# -*- coding: utf-8 -*-
# Part of Insilos. See LICENSE file for full copyright and licensing details.

import html
import logging
import re

from odoo.exceptions import AccessError

try:
    from odoo import api, fields, models
except (ImportError, Exception):
    class models:
        class AbstractModel:
            _name = None
            _description = None
        class Model:
            _name = None
            _inherit = None
            _description = None

    class fields:
        @staticmethod
        def Char(*args, **kwargs):
            return None

    class api:
        @staticmethod
        def model(f):
            return f

_logger = logging.getLogger(__name__)

# Prompt injection markers pattern (case-insensitive)
PROMPT_INJECTION_PATTERN = re.compile(
    r"(?i)(ignore\s+previous\s+instructions|system\s*:|assistant\s*:|user\s*:|\[system\]|<prompt>|</prompt>|&lt;prompt&gt;|&lt;/prompt&gt;|output\s+internal|disclose)"
)


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _sanitize_timesheet_description(self, raw_text: str) -> str:
        """
        Sanitize timesheet description:
        1. HTML escape special characters.
        2. Filter prompt injection markers to '[FILTERED_INVARIANT]'.
        3. Slice output to max 300 characters.
        """
        if not raw_text:
            return ""
        escaped = html.escape(str(raw_text))
        filtered = PROMPT_INJECTION_PATTERN.sub("[FILTERED_INVARIANT]", escaped)
        return filtered[:300]

    def generate_decree70_ai_explanation(self) -> str:
        """
        Constructs safe prompt string for Decree 70 AI explanation from validated timesheet entries:
        - Asserts self.company_id == current_company.
        - Queries timesheet lines strictly with ('company_id', '=', current_company.id) and ('invoice_id', '=', self.id).
        - Asserts line.project_id.company_id matches current_company.
        - Wraps entries in <item hours='...' desc='...' /> inside <timesheet_manifest company_id='...'>.
        - Returns constructed safe prompt string.
        """
        self.ensure_one()
        current_company = self.env.company

        if self.company_id and self.company_id != current_company:
            raise AccessError(
                f"Cross-company tenant violation: invoice company {self.company_id.id} "
                f"does not match current company {current_company.id}"
            )
        assert self.company_id == current_company, "Invoice company does not match current company."

        timesheet_model = None
        if hasattr(self.env, 'get'):
            timesheet_model = self.env.get('account.analytic.line', None)
        if timesheet_model is None:
            try:
                timesheet_model = self.env['account.analytic.line']
            except (KeyError, Exception):
                timesheet_model = None

        if timesheet_model is not None and hasattr(timesheet_model, 'search'):
            lines = timesheet_model.search([
                ('company_id', '=', current_company.id),
                ('invoice_id', '=', self.id),
            ])
        else:
            lines = []

        items = []
        for line in lines:
            if hasattr(line, 'project_id') and line.project_id and hasattr(line.project_id, 'company_id') and line.project_id.company_id:
                if line.project_id.company_id != current_company:
                    raise AccessError(
                        f"Cross-company project violation: line project company {line.project_id.company_id.id} "
                        f"does not match current company {current_company.id}"
                    )
                assert line.project_id.company_id == current_company, "Project company does not match current company."

            hours = getattr(line, 'unit_amount', 0.0)
            raw_desc = getattr(line, 'name', '') or ''
            clean_desc = self._sanitize_timesheet_description(raw_desc)
            items.append(f"<item hours='{hours}' desc='{clean_desc}' />")

        manifest = (
            f"<timesheet_manifest company_id='{current_company.id}'>\n"
            + "\n".join(items)
            + ("\n" if items else "")
            + "</timesheet_manifest>"
        )
        prompt = (
            f"Decree 70 AI Explanation for Invoice {self.name or self.id} (Company {current_company.id}):\n"
            f"{manifest}"
        )
        return prompt
