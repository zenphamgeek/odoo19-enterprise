# -*- coding: utf-8 -*-
import hashlib
import logging
from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class PinnedConversionCron(models.AbstractModel):
    _name = "insilos.pinned.conversion.cron"
    _description = "24/7 Pinned Conversion Runner with Pre-Flight CRM Safety Guard"

    @api.model
    def run_247_pinned_conversions(self):
        """
        Entrypoint for 24/7 Pinned Conversions cron.
        Enforces tenant boundaries and transaction-scoped advisory locks.
        """
        companies = self.env["res.company"].search([("active", "=", True)])
        _logger.info("Starting 24/7 Pinned Conversions across %d active companies", len(companies))

        for company in companies:
            # CRM Pre-Flight Gate: Challenge-and-Response verification
            if not self._pre_flight_safety_check(company):
                _logger.warning("[CRM SCRUB] Aborting conversion cycle for company %s (%d): Checklist failed", company.name, company.id)
                continue

            self._execute_company_conversion_isolated(company)

    @api.model
    def _pre_flight_safety_check(self, company) -> bool:
        """
        Aviation-Grade Pre-Flight Challenge/Response Checklist.
        Validates:
        1. Non-empty company identifier and currency assignment.
        2. Transaction-scoped non-blocking advisory lock availability.
        """
        if not company or not company.currency_id:
            return False

        # Deterministic 64-bit signed advisory lock via SHA-256 (CWE-328 / CWE-400 / CWE-662)
        lock_bytes = hashlib.sha256(f"pinned_conversion_{company.id}".encode("utf-8")).digest()[:8]
        lock_id = int.from_bytes(lock_bytes, byteorder="big", signed=True)
        self.env.cr.execute("SELECT pg_try_advisory_xact_lock(%s);", (lock_id,))
        res = self.env.cr.fetchone()
        acquired = bool(res and res[0])

        if not acquired:
            _logger.info("[LOCK SKIP] Company %s (%d) currently processed by another worker", company.name, company.id)
            return False

        return True

    @api.model
    def _execute_company_conversion_isolated(self, company):
        """
        Executes conversion math under explicit company scope and database savepoint.
        """
        with self.env.cr.savepoint():
            company_env = self.with_company(company)
            _logger.info("Executing isolated pinned conversion for company: %s", company.name)
            company_env._process_tenant_pinned_rates(company)

    @api.model
    def _process_tenant_pinned_rates(self, company):
        """
        Implementation of rates calculation strictly bound to company.
        Safely dispatches to sale.order and al2c.timesheet.staging under with_company(company).
        """
        if 'sale.order' in self.env:
            try:
                sale_model = self.env['sale.order'].with_company(company)
                if hasattr(sale_model, 'cron_process_pinned_conversions'):
                    sale_model.cron_process_pinned_conversions()
                elif hasattr(sale_model, '_cron_process_pinned_conversions'):
                    sale_model._cron_process_pinned_conversions()
            except Exception as exc:
                _logger.error("Failed to process pinned conversions for sale.order on company %s: %s", company.id, exc)

        if 'al2c.timesheet.staging' in self.env:
            try:
                staging_model = self.env['al2c.timesheet.staging'].with_company(company)
                if hasattr(staging_model, '_cron_process_pinned_conversions'):
                    staging_model._cron_process_pinned_conversions()
                elif hasattr(staging_model, 'cron_process_pinned_conversions'):
                    staging_model.cron_process_pinned_conversions()
            except Exception as exc:
                _logger.error("Failed to process pinned conversions for al2c.timesheet.staging on company %s: %s", company.id, exc)

        if 'insilos.pinned.conversion.runner' in self.env:
            try:
                runner_model = self.env['insilos.pinned.conversion.runner'].with_company(company)
                if hasattr(runner_model, '_process_company_cellular'):
                    runner_model._process_company_cellular(company.id)
            except Exception as exc:
                _logger.error("Failed to process cellular conversions for insilos.pinned.conversion.runner on company %s: %s", company.id, exc)

        return True

