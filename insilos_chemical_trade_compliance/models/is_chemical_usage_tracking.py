# -*- coding: utf-8 -*-
# Part of Insilos. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class ChemicalUsageTracking(models.Model):
    _name = 'is.chemical.usage.tracking'
    _description = 'Chemical Usage & Inbound/Inventory Tracking Report (Bảng theo dõi sử dụng hóa chất)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'reporting_year desc, id desc'

    name = fields.Char(string='Report Code', compute='_compute_name', store=True, precompute=True)
    chemical_substance_id = fields.Many2one('is.hse.chemical.substance', string='Chemical Substance', required=True, index=True, tracking=True)
    cas_number = fields.Char(related='chemical_substance_id.cas_number', string='CAS Registry No.', store=True)
    
    reporting_year = fields.Integer(string='Reporting Year', required=True, default=lambda self: fields.Date.today().year, tracking=True)
    reporting_period = fields.Selection([
        ('annual', 'Annual Report (Cả năm)'),
        ('semi_annual_1', '1st Half Year (6 tháng đầu năm)'),
        ('semi_annual_2', '2nd Half Year (6 tháng cuối năm)'),
        ('q1', 'Quarter 1'),
        ('q2', 'Quarter 2'),
        ('q3', 'Quarter 3'),
        ('q4', 'Quarter 4'),
    ], string='Reporting Period', default='annual', required=True, tracking=True)

    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    facility_id = fields.Many2one('is.hse.facility', string='Operating Facility')

    # The 5-stage Data Chain: Demand -> Import -> Domestic -> Usage -> Inventory
    planned_demand_kg = fields.Float(string='1. Planned Demand (kg)', tracking=True,
                                     help='Approved estimated consumption demand for the reporting period.')
    imported_volume_kg = fields.Float(string='2. Imported Volume (kg)', compute='_compute_usage_chain', store=True, tracking=True)
    domestic_purchased_kg = fields.Float(string='3. Domestic Purchase (kg)', compute='_compute_usage_chain', store=True, tracking=True)
    total_inbound_volume_kg = fields.Float(string='Total Inflow (kg)', compute='_compute_usage_chain', store=True)

    consumed_in_production_kg = fields.Float(string='4. Consumed in Manufacturing (kg)', compute='_compute_usage_chain', store=True, tracking=True)
    current_stock_kg = fields.Float(string='5. Current Inventory (kg)', compute='_compute_usage_chain', store=True, tracking=True)
    
    calculated_balance_kg = fields.Float(string='Calculated Balance (kg)', compute='_compute_usage_chain', store=True)
    loss_or_evaporation_kg = fields.Float(string='Process Evaporation Loss (kg)', default=0.0)

    purpose_of_use_ids = fields.Many2many('is.chemical.purpose.of.use', 'chem_usage_purpose_rel',
                                          'tracking_id', 'purpose_id', string='Purposes of Use (Mục đích sử dụng)')

    line_ids = fields.One2many('is.chemical.usage.tracking.line', 'tracking_id', string='Detailed Inflow & Usage Logs')
    notes = fields.Text(string='Auditor & Technical Explanations')

    def action_sync_from_erp_stock_moves(self):
        """
        Tự động quét các stock.move đã hoàn thành (state='done') của các mã Material
        có ánh xạ tới hóa chất này để tổng hợp tự động vào chuỗi dữ liệu 5 bước.
        """
        self.ensure_one()
        mapping_obj = self.env['is.chemical.material.mapping']
        stock_move_obj = self.env['stock.move']

        # Tìm các mã sản phẩm gắn với hóa chất này
        mappings = mapping_obj.search([
            ('chemical_substance_id', '=', self.chemical_substance_id.id),
        ])
        if not mappings:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Thông báo Đồng bộ'),
                    'message': _('Không tìm thấy Material Mapping nào cho hóa chất này.'),
                    'type': 'warning',
                    'sticky': False,
                }
            }

        product_tmpl_ids = mappings.mapped('product_tmpl_id.id')
        mapping_by_tmpl = {m.product_tmpl_id.id: m for m in mappings}

        # Lấy các stock.move trong năm báo cáo
        start_date = f"{self.reporting_year}-01-01"
        end_date = f"{self.reporting_year}-12-31"

        moves = stock_move_obj.search([
            ('product_tmpl_id', 'in', product_tmpl_ids),
            ('company_id', '=', self.company_id.id),
            ('state', '=', 'done'),
            ('date', '>=', start_date),
            ('date', '<=', end_date),
        ])

        created_count = 0
        existing_move_ids = set(self.line_ids.mapped('source_stock_move_id').ids)

        for move in moves:
            if move.id in existing_move_ids:
                continue
            doc_ref = move.picking_id.name or move.reference or f"MOVE-{move.id}"

            mapping = mapping_by_tmpl.get(move.product_tmpl_id.id)
            ratio = mapping.uom_to_kg_ratio if mapping and mapping.uom_to_kg_ratio > 0 else 1.0
            qty_kg = move.product_uom_qty * ratio

            # Phân loại flow_type
            if move.location_id.usage == 'supplier':
                is_foreign = move.picking_id.partner_id.country_id and move.picking_id.partner_id.country_id.code != 'VN'
                flow = 'import' if is_foreign else 'domestic_purchase'
            elif move.location_dest_id.usage in ('production', 'inventory', 'customer'):
                flow = 'production_consumption'
            else:
                flow = 'import'

            self.env['is.chemical.usage.tracking.line'].with_context(
                _chemical_usage_sync=_USAGE_SYNC_CAPABILITY
            ).create({
                'tracking_id': self.id,
                'source_stock_move_id': move.id,
                'date': move.date.date() if hasattr(move.date, 'date') else move.date,
                'flow_type': flow,
                'document_ref': doc_ref,
                'partner_id': move.picking_id.partner_id.id if move.picking_id else False,
                'quantity_kg': qty_kg,
                'purpose_of_use_id': mapping.purpose_of_use_id.id if mapping and mapping.purpose_of_use_id else False,
                'remarks': f"Tự động đồng bộ từ ERP Stock Move #{move.id} ({move.product_id.display_name})",
            })
            created_count += 1
            existing_move_ids.add(move.id)

        self.message_post(
            body=f"Đã hoàn thành đồng bộ tự động từ ERP Stock: thêm mới {created_count} bản ghi luân chuyển hóa chất."
        )

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Đồng bộ Hoàn tất'),
                'message': _('Đã đồng bộ %s phiếu xuất nhập kho ERP vào Bảng theo dõi sử dụng.') % created_count,
                'type': 'success',
                'sticky': False,
            }
        }

    @api.depends('chemical_substance_id.name', 'reporting_year', 'reporting_period')
    def _compute_name(self):
        for rec in self:
            c_name = rec.chemical_substance_id.name or 'CHEMICAL'
            rec.name = f"USAGE-{rec.reporting_year}-{rec.reporting_period}-{c_name}"

    @api.depends('line_ids.quantity_kg', 'line_ids.flow_type', 'loss_or_evaporation_kg')
    def _compute_usage_chain(self):
        for rec in self:
            imported = sum(l.quantity_kg for l in rec.line_ids if l.flow_type == 'import')
            domestic = sum(l.quantity_kg for l in rec.line_ids if l.flow_type == 'domestic_purchase')
            consumed = sum(l.quantity_kg for l in rec.line_ids if l.flow_type == 'production_consumption')
            inventory = sum(l.quantity_kg for l in rec.line_ids if l.flow_type == 'stock_inventory')

            rec.imported_volume_kg = imported
            rec.domestic_purchased_kg = domestic
            rec.total_inbound_volume_kg = imported + domestic
            rec.consumed_in_production_kg = consumed
            rec.current_stock_kg = inventory if inventory > 0 else max(0.0, (imported + domestic) - consumed - rec.loss_or_evaporation_kg)
            rec.calculated_balance_kg = (imported + domestic) - consumed


class ChemicalUsageTrackingLine(models.Model):
    _name = 'is.chemical.usage.tracking.line'
    _description = 'Chemical Usage Tracking Ledger Line'
    _order = 'date desc, id desc'

    _sql_constraints = [
        ('chemical_usage_source_stock_move_unique', 'unique(source_stock_move_id)',
         'An ERP stock move can only be synchronized once.'),
    ]

    tracking_id = fields.Many2one('is.chemical.usage.tracking', string='Usage Tracking Report', required=True, ondelete='cascade', index=True)
    source_stock_move_id = fields.Many2one('stock.move', string='ERP Source Stock Move', readonly=True, copy=False, index=True)
    date = fields.Date(string='Transaction Date', default=fields.Date.today, required=True)
    
    flow_type = fields.Selection([
        ('import', 'Import Inbound (Nhập khẩu)'),
        ('domestic_purchase', 'Domestic Purchase (Mua trong nước)'),
        ('production_consumption', 'Production Consumption (Xuất dùng sản xuất)'),
        ('stock_inventory', 'Physical Inventory Count (Kiểm kê tồn kho)'),
    ], string='Flow Type', required=True, default='import')

    document_ref = fields.Char(string='Document Reference', required=True)
    partner_id = fields.Many2one('res.partner', string='Partner')
    quantity_kg = fields.Float(string='Quantity (kg)', required=True, default=0.0)
    
    purpose_of_use_id = fields.Many2one('is.chemical.purpose.of.use', string='Purpose of Use')

    @api.model_create_multi
    def create(self, vals_list):
        if any('source_stock_move_id' in vals for vals in vals_list) and self.env.context.get('_chemical_usage_sync') is not _USAGE_SYNC_CAPABILITY:
            raise AccessError(_('ERP source linkage is managed by the ERP synchronization action.'))
        return super().create(vals_list)

    def write(self, vals):
        if self.filtered('source_stock_move_id'):
            raise ValidationError(_('ERP-synchronized usage lines are immutable; create a correction line instead.'))
        if 'source_stock_move_id' in vals:
            raise AccessError(_('ERP source linkage is immutable.'))
        return super().write(vals)

    def unlink(self):
        if self.filtered('source_stock_move_id'):
            raise ValidationError(_('ERP-synchronized usage lines are immutable; create a correction line instead.'))
        return super().unlink()

    @api.constrains('tracking_id', 'purpose_of_use_id')
    def _check_purpose_company(self):
        for line in self:
            if line.purpose_of_use_id and line.purpose_of_use_id.company_id != line.tracking_id.company_id:
                raise ValidationError(_('Purpose must belong to the usage tracking company.'))
    remarks = fields.Char(string='Remarks')
