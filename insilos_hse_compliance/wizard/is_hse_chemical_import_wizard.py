# -*- coding: utf-8 -*-
# Part of Insilos. See LICENSE file for full copyright and licensing details.

import base64
import csv
import io
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

# Column header mapping → model field
_COLUMN_MAP = {
    'chemical_name': 'name',
    'name': 'name',
    'cas_number': 'cas_number',
    'cas': 'cas_number',
    'un_number': 'un_number',
    'formula': 'formula',
    'hazard': 'hazard_classification',
    'hazard_classification': 'hazard_classification',
    'signal_word': 'ghs_signal_word',
    'flammable': 'ghs_flammable',
    'corrosive': 'ghs_corrosive',
    'toxic': 'ghs_toxic',
    'health_hazard': 'ghs_health_hazard',
    'environmental': 'ghs_environmental',
}


class HSEChemicalImportWizard(models.TransientModel):
    _name = 'is.hse.chemical.import.wizard'
    _description = 'Bulk Import Chemical Substances from CSV/Excel'

    import_file = fields.Binary(string='Upload CSV File', required=True,
                                help='CSV file with columns: chemical_name, cas_number, un_number, formula, hazard_classification, signal_word, flammable, corrosive, toxic, health_hazard, environmental')
    file_name = fields.Char(string='File Name')
    import_mode = fields.Selection([
        ('create_only', 'Create new substances only (skip if CAS exists)'),
        ('update_existing', 'Update existing substances (match by CAS)'),
        ('create_or_update', 'Create new or update existing (upsert by CAS)'),
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
        normalized = {}
        for h in reader.fieldnames:
            key = h.strip().lower().replace(' ', '_').replace('-', '_')
            if key in _COLUMN_MAP:
                normalized[h] = _COLUMN_MAP[key]

        if 'name' not in normalized.values():
            raise UserError(_("CSV must have a 'chemical_name' or 'name' column."))

        Substance = self.env['is.hse.chemical.substance']
        created = updated = skipped = 0
        errors = []
        bool_true_values = {'1', 'true', 'yes', 'x', '✓', '✔'}

        for row_idx, row in enumerate(reader, start=2):
            try:
                vals = {}
                for csv_col, model_field in normalized.items():
                    value = (row.get(csv_col) or '').strip()
                    if not value:
                        continue
                    field_def = Substance._fields.get(model_field)
                    if field_def and field_def.type == 'boolean':
                        vals[model_field] = value.lower() in bool_true_values
                    elif field_def and field_def.type == 'selection':
                        valid_keys = [key for key, _label in field_def.selection]
                        if value in valid_keys:
                            vals[model_field] = value
                        else:
                            label_map = {label.lower(): key for key, label in field_def.selection}
                            if value.lower() in label_map:
                                vals[model_field] = label_map[value.lower()]
                            else:
                                raise UserError(_(
                                    "Invalid %(field)s value '%(value)s'."
                                ) % {'field': model_field, 'value': value})
                    else:
                        vals[model_field] = value

                if not vals.get('name'):
                    errors.append(_("Row %d: Missing chemical name, skipped.") % row_idx)
                    skipped += 1
                    continue

                cas = vals.get('cas_number')
                existing = Substance.search([('cas_number', '=', cas)], limit=1) if cas else Substance

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
                    Substance.create(vals)
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

        _logger.info("HSE Chemical Import: created=%d updated=%d skipped=%d errors=%d",
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
        content = 'chemical_name,cas_number,un_number,formula,hazard_classification,signal_word,flammable,corrosive,toxic,health_hazard,environmental\n'
        content += 'Sulfuric Acid,7664-93-9,UN 1830,H2SO4,hazardous_general,danger,0,1,0,0,1\n'
        content += 'Acetone,67-64-1,UN 1090,C3H6O,hazardous_general,warning,1,0,0,0,0\n'
        encoded = base64.b64encode(content.encode('utf-8'))

        attachment = self.env['ir.attachment'].create({
            'name': 'hse_chemical_import_template.csv',
            'type': 'binary',
            'datas': encoded,
            'mimetype': 'text/csv',
        })
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%d?download=true' % attachment.id,
            'target': 'self',
        }
