# -*- coding: utf-8 -*-
# Part of Insilos. See LICENSE file for full copyright and licensing details.

import base64
import csv
import io
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class LogisticsIDPImportWizard(models.TransientModel):
    _name = 'logistics.idp.import.wizard'
    _description = 'Bulk Import Logistics Manifest & IDP Cases from CSV'

    import_file = fields.Binary(string='Upload CSV Manifest', required=True,
                                help='CSV file with columns: case_name, document_type, reference_number, partner_name, transport_mode, total_amount, currency, weight')
    file_name = fields.Char(string='File Name')
    project_id = fields.Many2one('project.project', string='Target Logistics Project',
                                 help='Optional default project to assign imported IDP cases')

    result_cases_created = fields.Integer(string='Cases Created', readonly=True)
    result_docs_created = fields.Integer(string='Documents Created', readonly=True)
    result_skipped = fields.Integer(string='Records Skipped', readonly=True)
    result_errors = fields.Text(string='Errors', readonly=True)
    is_imported = fields.Boolean(string='Import Completed', default=False)

    def action_import(self):
        self.ensure_one()
        if not self.import_file:
            raise UserError(_("Please upload a CSV manifest file."))

        try:
            raw = base64.b64decode(self.import_file)
            text = raw.decode('utf-8-sig')
        except UnicodeDecodeError:
            try:
                text = raw.decode('latin-1')
            except Exception:
                raise UserError(_("Cannot decode file. Please use UTF-8 or Latin-1 encoding."))

        reader = csv.DictReader(io.StringIO(text))
        if not reader.fieldnames:
            raise UserError(_("CSV file appears empty or has no header row."))

        Case = self.env['logistics.idp.case']
        Doc = self.env['logistics.idp.document']
        Partner = self.env['res.partner']

        cases_created = 0
        docs_created = 0
        skipped = 0
        errors = []

        # Get or create default project if not provided
        default_project = self.project_id
        if not default_project:
            default_project = self.env['project.project'].search([('name', 'ilike', 'Logistics')], limit=1)
            if not default_project:
                default_project = self.env['project.project'].search([], limit=1)

        case_map = {}

        for row_idx, row in enumerate(reader, start=2):
            try:
                case_name = (row.get('case_name') or row.get('bl_number') or row.get('name') or '').strip()
                doc_type = (row.get('document_type') or row.get('type') or 'bill_of_lading').strip().lower()
                ref_no = (row.get('reference_number') or row.get('ref') or case_name).strip()
                partner_name = (row.get('partner_name') or row.get('supplier') or '').strip()
                transport_mode = (row.get('transport_mode') or 'ocean').strip().lower()
                weight_str = (row.get('weight') or '0').strip()

                if not case_name:
                    errors.append(_("Row %d: Missing case_name / bl_number, skipped.") % row_idx)
                    skipped += 1
                    continue

                # Find or create case
                case = case_map.get(case_name)
                if not case:
                    existing_case = Case.search([('name', '=', case_name)], limit=1)
                    if existing_case:
                        case = existing_case
                    else:
                        case_vals = {
                            'name': case_name,
                            'company_id': self.env.company.id,
                            'project_id': default_project.id if default_project else False,
                            'transport_mode': transport_mode if transport_mode in ['ocean', 'air', 'road', 'rail'] else 'ocean',
                        }
                        try:
                            case_vals['cargo_weight'] = float(weight_str)
                        except (ValueError, TypeError):
                            pass
                        case = Case.create(case_vals)
                        cases_created += 1
                    case_map[case_name] = case

                # Resolve partner
                partner = False
                if partner_name:
                    partner = Partner.search([('name', '=ilike', partner_name)], limit=1)

                # Create IDP Document record
                doc_vals = {
                    'name': f"{doc_type.upper()}: {ref_no}",
                    'case_id': case.id,
                    'document_type': doc_type if doc_type in ['bill_of_lading', 'commercial_invoice', 'packing_list', 'customs_declaration', 'certificate_of_origin'] else 'bill_of_lading',
                    'extracted_partner_name': partner_name or (partner.name if partner else False),
                    'extracted_reference': ref_no,
                    'state': 'draft',
                }
                Doc.create(doc_vals)
                docs_created += 1

            except Exception as e:
                errors.append(_("Row %d: %s") % (row_idx, str(e)))
                skipped += 1

        self.write({
            'result_cases_created': cases_created,
            'result_docs_created': docs_created,
            'result_skipped': skipped,
            'result_errors': '\n'.join(errors) if errors else False,
            'is_imported': True,
        })

        _logger.info("Logistics IDP Manifest Import: cases=%d docs=%d skipped=%d errors=%d",
                      cases_created, docs_created, skipped, len(errors))

        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_download_template(self):
        """Generate a downloadable CSV template for logistics document manifest."""
        content = 'case_name,document_type,reference_number,partner_name,transport_mode,total_amount,currency,weight\n'
        content += 'BL-HAPAG-2026-0881,bill_of_lading,HLCUBSC26081234,Hapag-Lloyd Vietnam,ocean,4500.0,USD,24.5\n'
        content += 'BL-HAPAG-2026-0881,commercial_invoice,INV-2026-0988,Samsung Electronics,ocean,125000.0,USD,24.5\n'
        content += 'BL-HAPAG-2026-0881,packing_list,PL-2026-0988,Samsung Electronics,ocean,0,USD,24.5\n'
        encoded = base64.b64encode(content.encode('utf-8'))

        attachment = self.env['ir.attachment'].create({
            'name': 'logistics_idp_manifest_template.csv',
            'type': 'binary',
            'datas': encoded,
            'mimetype': 'text/csv',
        })
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%d?download=true' % attachment.id,
            'target': 'self',
        }
