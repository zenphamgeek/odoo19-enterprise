from werkzeug.exceptions import BadRequest

from odoo.addons.web.controllers.report import ReportController
from odoo.exceptions import AccessError, ValidationError
from odoo.http import request


class ESGReportController(ReportController):

    def report_routes(self, reportname, docids=None, converter=None, **data):
        if reportname in {
            'insilos_esg_bridge.report_esg_facility_scorecard_doc',
            'insilos_esg_bridge.report_esg_cbam_declaration_doc',
            'insilos_esg_bridge.report_esg_freight_carbon_doc',
        } and docids:
            ids = docids.split(',')
            if not all(id_.isdigit() for id_ in ids):
                raise BadRequest('Invalid report document IDs.')
            records = request.env[
                request.env['ir.actions.report']._get_report_from_name(reportname).model
            ].browse([int(id_) for id_ in ids])
            records.check_access('read')
            records.check_access_rule('read')
            if reportname == 'insilos_esg_bridge.report_esg_facility_scorecard_doc':
                if records.filtered(lambda scorecard: scorecard.state != 'published'):
                    raise AccessError('Only published ESG scorecards can be rendered as reports.')
                for scorecard in records:
                    scorecard._check_source_provenance()
            else:
                raise ValidationError(
                    'This internal estimate report is unavailable until governed source, evidence, '
                    'independent review, and publication controls exist.'
                )
        return super().report_routes(reportname, docids, converter, **data)
