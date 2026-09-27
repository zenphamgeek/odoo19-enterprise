from werkzeug.exceptions import BadRequest

from odoo.addons.web.controllers.report import ReportController
from odoo.http import request


class ChemicalComplianceReportController(ReportController):

    def report_routes(self, reportname, docids=None, converter=None, **data):
        if reportname in {
            'insilos_hse_compliance.report_hse_product_permit_doc',
            'insilos_chemical_trade_compliance.report_chemical_dossier_application_doc',
            'insilos_chemical_trade_compliance.report_chemical_usage_tracking_doc',
            'insilos_chemical_trade_compliance.report_chemical_nsw_declaration_doc',
            'insilos_chemical_trade_compliance.report_chemical_permit_quota_doc',
        } and docids:
            ids = docids.split(',')
            if not all(id_.isdigit() for id_ in ids):
                raise BadRequest('Invalid report document IDs.')
            records = request.env[
                request.env['ir.actions.report']._get_report_from_name(reportname).model
            ].browse([int(id_) for id_ in ids])
            records.check_access('read')
            records.check_access_rule('read')
            if reportname in {
                'insilos_chemical_trade_compliance.report_chemical_usage_tracking_doc',
                'insilos_chemical_trade_compliance.report_chemical_nsw_declaration_doc',
                'insilos_chemical_trade_compliance.report_chemical_permit_quota_doc',
            }:
                raise BadRequest('This report is unavailable until governed evidence and publication controls exist.')
            if reportname == 'insilos_chemical_trade_compliance.report_chemical_dossier_application_doc':
                records.filtered(lambda dossier: dossier.state != 'draft')._check_regulatory_review()
        return super().report_routes(reportname, docids, converter, **data)
