from werkzeug.exceptions import BadRequest

from odoo.addons.web.controllers.report import ReportController
from odoo.exceptions import AccessError
from odoo.http import request


class HSEReportController(ReportController):

    def report_routes(self, reportname, docids=None, converter=None, **data):
        if reportname in {
            'insilos_hse_compliance.report_hse_product_permit_doc',
            'insilos_hse_compliance.report_hse_chemical_safety_sop_doc',
            'insilos_hse_compliance.report_hse_legal_compliance_audit_doc',
            'insilos_hse_compliance.report_hse_safety_data_sheet_doc',
        } and docids:
            ids = docids.split(',')
            if not all(id_.isdigit() for id_ in ids):
                raise BadRequest('Invalid report document IDs.')
            records = request.env[
                request.env['ir.actions.report']._get_report_from_name(reportname).model
            ].browse([int(id_) for id_ in ids])
            records.check_access('read')
            records.check_access_rule('read')
            if reportname == 'insilos_hse_compliance.report_hse_safety_data_sheet_doc':
                raise AccessError(
                    'SDS export is unavailable until supplier source, version, immutable content hash, '
                    'independent review, and publication controls exist.'
                )
            if reportname == 'insilos_hse_compliance.report_hse_legal_compliance_audit_doc':
                for register in records.filtered(lambda record: record.state != 'draft'):
                    unsupported = register.obligation_ids.filtered(
                        lambda obligation: (
                            obligation.compliance_status == 'not_assessed'
                            or not obligation.provision_id
                            or not obligation.document_id.has_governed_provenance()
                            or not (obligation.evidence_summary or '').strip()
                            or not obligation.evidence_attachment_ids
                            or (
                                obligation.compliance_status == 'compliant'
                                and not obligation.compliance_approved_by_id
                            )
                        )
                    )
                    if not register.obligation_ids or unsupported:
                        raise AccessError(
                            'Non-draft internal HSE reviews require governed sources and approved compliance assessments.'
                        )
        return super().report_routes(reportname, docids, converter, **data)
