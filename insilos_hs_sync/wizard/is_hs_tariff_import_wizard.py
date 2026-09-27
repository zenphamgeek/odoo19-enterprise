# -*- coding: utf-8 -*-
# Part of Insilos. See LICENSE file for full copyright and licensing details.

import base64
import csv
import io
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class HSImportTariffWizard(models.TransientModel):
    _name = 'is.hs.tariff.import.wizard'
    _description = 'Bulk Import HS Tariff Schedule from CSV'

    import_file = fields.Binary(string='Upload CSV File', required=True,
                                help='CSV with columns: hs_code, description_vi, description_en, mfn_rate, vat_rate')
    file_name = fields.Char(string='File Name')
    import_mode = fields.Selection([
        ('create_only', 'Create new tariff items only (skip if HS code exists)'),
        ('update_existing', 'Update existing items (match by HS code)'),
        ('create_or_update', 'Create new or update existing (upsert by HS code)'),
    ], string='Import Mode', default='create_or_update', required=True)

    result_created = fields.Integer(string='Records Created', readonly=True)
    result_updated = fields.Integer(string='Records Updated', readonly=True)
    result_skipped = fields.Integer(string='Records Skipped', readonly=True)
    result_errors = fields.Text(string='Errors', readonly=True)
    is_imported = fields.Boolean(string='Import Completed', default=False)

    def action_import(self):
        self.ensure_one()
        if not self.import_file:
            raise UserError(_("Please upload a CSV file."))

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

        # Normalize headers
        header_map = {
            'hs_code': 'hs_code',
            'code': 'hs_code',
            'description_vi': 'description_vi',
            'description': 'description_vi',
            'description_en': 'description_en',
            'mfn_rate': 'mfn_duty_rate',
            'mfn_duty_rate': 'mfn_duty_rate',
            'vat_rate': 'vat_rate',
        }
        normalized = {}
        for h in reader.fieldnames:
            key = h.strip().lower().replace(' ', '_').replace('-', '_')
            if key in header_map:
                normalized[h] = header_map[key]

        if 'hs_code' not in normalized.values():
            raise UserError(_("CSV must have an 'hs_code' or 'code' column."))

        Tariff = self.env['is.hs.tariff']
        created = updated = skipped = 0
        errors = []

        for row_idx, row in enumerate(reader, start=2):
            try:
                vals = {}
                for csv_col, model_field in normalized.items():
                    value = (row.get(csv_col) or '').strip()
                    if not value:
                        continue
                    field_def = Tariff._fields.get(model_field)
                    if field_def and field_def.type == 'float':
                        vals[model_field] = float(value.replace(',', '.').replace('%', ''))
                    else:
                        vals[model_field] = value

                hs_code = vals.get('hs_code')
                if not hs_code:
                    errors.append(_("Row %d: Missing HS code, skipped.") % row_idx)
                    skipped += 1
                    continue

                existing = Tariff.search([('hs_code', '=', hs_code)], limit=1)

                if existing:
                    if self.import_mode == 'create_only':
                        skipped += 1
                        continue
                    existing.write(vals)
                    updated += 1
                else:
                    if self.import_mode == 'update_existing':
                        skipped += 1
                        continue
                    Tariff.create(vals)
                    created += 1

            except Exception as e:
                errors.append(_("Row %d: %s") % (row_idx, str(e)))
                skipped += 1

        self.write({
            'result_created': created,
            'result_updated': updated,
            'result_skipped': skipped,
            'result_errors': '\n'.join(errors) if errors else False,
            'is_imported': True,
        })

        _logger.info("HS Tariff Import: created=%d updated=%d skipped=%d errors=%d",
                      created, updated, skipped, len(errors))

        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_download_template(self):
        """Generate a downloadable CSV template."""
        content = 'hs_code,description_vi,description_en,mfn_rate,vat_rate\n'
        content += '72061000,"Sắt và thép không hợp kim dạng thỏi","Iron and non-alloy steel ingots",5.0,10.0\n'
        content += '76011000,"Nhôm chưa gia công, chưa hợp kim","Unwrought aluminium, not alloyed",3.0,10.0\n'
        encoded = base64.b64encode(content.encode('utf-8'))

        attachment = self.env['ir.attachment'].create({
            'name': 'hs_tariff_import_template.csv',
            'type': 'binary',
            'datas': encoded,
            'mimetype': 'text/csv',
        })
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%d?download=true' % attachment.id,
            'target': 'self',
        }
