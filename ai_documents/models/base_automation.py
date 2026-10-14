# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)


class BaseAutomation(models.Model):
    _inherit = "base.automation"

    ai_autosort_folder_id = fields.Many2one(
        "documents.document",
        string="Sorted Folder",
        domain=[("type", "=", "folder"), ("shortcut_document_id", "=", False)],
    )

    _unique_ai_autosort_folder_id = models.Constraint(
        "UNIQUE(ai_autosort_folder_id)",
        "Only one automation rule can be used to sort with AI a given folder",
    )

    def _process(self, records, domain_post=None, *args, **kwargs):
        # Disallow unprivileged RPC context from suppressing automation rules
        skip_autosort = (
            self.env.context.get("ai_documents_skip_autosort")
            and (self.env.is_system() or self.env.user.has_group("base.group_system"))
        )
        executable_rules = self
        if skip_autosort and records and getattr(records, "_name", None) == "documents.document":
            executable_rules = self.filtered(lambda r: not r.ai_autosort_folder_id)
        if not executable_rules:
            return False
        return super(BaseAutomation, executable_rules)._process(records, domain_post, *args, **kwargs)
