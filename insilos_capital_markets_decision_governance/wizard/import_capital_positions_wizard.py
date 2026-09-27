# -*- coding: utf-8 -*-
# Part of Insilos. See LICENSE file for full copyright and licensing details.

import base64
import csv
import io
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ImportCapitalPositionsWizard(models.TransientModel):
    _name = 'capital.positions.import.wizard'
    _description = 'Bulk Import Portfolio Positions from Broker CSV'

    portfolio_id = fields.Many2one('capital.portfolio', string='Target Portfolio', required=True)
    import_file = fields.Binary(string='Upload CSV Extract', required=True,
                                help='CSV file with columns: symbol, name, quantity, average_cost, last_price, exchange')
    file_name = fields.Char(string='File Name')
    import_mode = fields.Selection([
        ('upsert', 'Create new or update existing positions'),
        ('create_only', 'Create new positions only (skip if exists)'),
    ], string='Import Mode', default='upsert', required=True)

    result_created = fields.Integer(string='Positions Created', readonly=True)
    result_updated = fields.Integer(string='Positions Updated', readonly=True)
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

        Position = self.env['capital.position']
        Instrument = self.env['capital.instrument']

        created = updated = skipped = 0
        errors = []

        for row_idx, row in enumerate(reader, start=2):
            try:
                symbol = (row.get('symbol') or row.get('ticker') or '').strip().upper()
                name = (row.get('name') or row.get('instrument_name') or symbol).strip()
                exchange = (row.get('exchange') or 'HOSE').strip()
                qty_str = (row.get('quantity') or row.get('qty') or '0').strip()
                cost_str = (row.get('average_cost') or row.get('cost') or '0').strip()
                price_str = (row.get('last_price') or row.get('price') or cost_str).strip()

                if not symbol:
                    errors.append(_("Row %d: Missing symbol/ticker, skipped.") % row_idx)
                    skipped += 1
                    continue

                quantity = float(qty_str.replace(',', ''))
                average_cost = float(cost_str.replace(',', ''))
                last_price = float(price_str.replace(',', ''))

                # Resolve or create instrument
                instrument = Instrument.search([('symbol', '=ilike', symbol)], limit=1)
                if not instrument:
                    instrument = Instrument.create({
                        'symbol': symbol,
                        'name': name or symbol,
                        'exchange': exchange,
                        'currency_id': self.portfolio_id.currency_id.id,
                    })

                # Check existing position in target portfolio
                existing = Position.search([
                    ('portfolio_id', '=', self.portfolio_id.id),
                    ('instrument_id', '=', instrument.id)
                ], limit=1)

                if existing:
                    if self.import_mode == 'create_only':
                        skipped += 1
                        continue
                    existing.write({
                        'quantity': quantity,
                        'average_cost': average_cost,
                        'last_price': last_price,
                    })
                    updated += 1
                else:
                    Position.create({
                        'portfolio_id': self.portfolio_id.id,
                        'instrument_id': instrument.id,
                        'quantity': quantity,
                        'average_cost': average_cost,
                        'last_price': last_price,
                    })
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

        _logger.info("Capital Positions Import: created=%d updated=%d skipped=%d errors=%d",
                      created, updated, skipped, len(errors))

        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_download_template(self):
        """Generate a downloadable CSV template for portfolio positions."""
        content = 'symbol,name,exchange,quantity,average_cost,last_price\n'
        content += 'FPT,"FPT Corporation",HOSE,50000,128000,135000\n'
        content += 'HPG,"Hoa Phat Group",HOSE,100000,28500,29200\n'
        content += 'VCB,"Vietcombank",HOSE,30000,92000,94500\n'
        encoded = base64.b64encode(content.encode('utf-8'))

        attachment = self.env['ir.attachment'].create({
            'name': 'capital_positions_template.csv',
            'type': 'binary',
            'datas': encoded,
            'mimetype': 'text/csv',
        })
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%d?download=true' % attachment.id,
            'target': 'self',
        }
