from werkzeug.exceptions import BadRequest

from odoo.addons.web.controllers.report import ReportController
from odoo.http import request


class LogisticsIdpReportController(ReportController):

    def report_routes(self, reportname, docids=None, converter=None, **data):
        if reportname == 'insilos_logistics_idp.report_logistics_idp_case_dossier_doc' and docids:
            ids = docids.split(',')
            if not all(id_.isdigit() for id_ in ids):
                raise BadRequest('Invalid report document IDs.')
            records = request.env['logistics.idp.case'].browse([int(id_) for id_ in ids])
            records.check_access('read')
            records.check_access_rule('read')
            release_cases = records.filtered(lambda case: case.state in ('ready', 'completed') or case.verdict == 'pass')
            if release_cases.filtered(lambda case: not case._has_governed_screening_result(require_release=True)):
                raise BadRequest('Release-ready reports require a governed immutable screening result.')
        return super().report_routes(reportname, docids, converter, **data)
