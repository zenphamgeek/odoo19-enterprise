# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class IsChemicalObligationSimulator(models.TransientModel):
    _name = 'is.chemical.obligation.simulator'
    _description = 'Tra cứu & Giả lập Nghĩa vụ Hóa chất Nhập khẩu (Khung 2026)'

    query_mode = fields.Selection([
        ('by_material', 'Theo Sản phẩm / Vật tư ERP (Material)'),
        ('by_chemical', 'Theo Hóa chất Master (HSE Substance)'),
        ('by_manual', 'Nhập thủ công (CAS, HS Code, Hàm lượng)'),
    ], string='Chế độ tra cứu', default='by_material', required=True)

    product_tmpl_id = fields.Many2one(
        'product.template',
        string='ERP Material',
        help='Chọn mã nguyên vật liệu ERP để tra cứu nghĩa vụ tương ứng'
    )
    chemical_substance_id = fields.Many2one(
        'is.hse.chemical.substance',
        string='Hóa chất Master (HSE)',
        help='Chọn hóa chất trong danh mục HSE'
    )
    cas_number = fields.Char(string='CAS Number', help='Chemical Abstracts Service Registry Number')
    hs_code = fields.Char(string='HS Code', help='Harmonized System Tariff Code')
    commercial_name = fields.Char(string='Commercial Name')
    concentration_percentage = fields.Float(string='Concentration (% wt)', default=100.0)
    purpose_of_use_id = fields.Many2one('is.chemical.purpose.of.use', string='Intended Purpose of Use')
    quantity_estimate_kg = fields.Float(string='Estimated Quantity (kg)', default=1000.0)

    # Simulation Result Fields
    is_simulated = fields.Boolean(string='Is Simulated', default=False)
    result_obligation_category = fields.Selection([
        ('review', 'Cần rà soát chuyên môn'),
        ('specially_controlled_group_1', 'Cờ quy tắc nội bộ: Nhóm kiểm soát 1'),
        ('specially_controlled_group_2', 'Cờ quy tắc nội bộ: Nhóm kiểm soát 2'),
        ('mandatory_nsw_declaration', 'Cờ quy tắc nội bộ: quy trình NSW'),
        ('restricted_chemical_license', 'Cờ quy tắc nội bộ: quy trình giấy phép'),
        ('conditional_chemical_cert', 'Cờ quy tắc nội bộ: điều kiện SXKD'),
        ('precursor_narcotics_explosives', 'Cờ quy tắc nội bộ: tiền chất'),
        ('opcw_scheduled_chemicals', 'Cờ quy tắc nội bộ: hóa chất OPCW'),
        ('sds_ghs_mandatory', 'Cờ quy tắc nội bộ: SDS/GHS'),
        ('prohibited_chemical_block', 'Cờ quy tắc nội bộ: dừng xử lý để rà soát'),
    ], string='Kết quả sàng lọc theo quy tắc nội bộ')

    result_requires_license = fields.Boolean(string='Cần rà soát quy trình giấy phép')
    result_license_type = fields.Char(string='Quy trình được quy tắc nội bộ gợi ý')
    result_licensing_authority = fields.Char(string='Cơ quan tham chiếu trong quy tắc')
    result_nsw_procedure_code = fields.Char(string='Mã quy trình NSW trong quy tắc')
    result_is_prohibited = fields.Boolean(string='Cờ dừng xử lý nội bộ')
    result_notes = fields.Text(string='Ghi chú quy tắc nội bộ và bước rà soát')
    result_rule_id = fields.Many2one('is.chemical.regulatory.rule', readonly=True)

    @api.onchange('query_mode', 'product_tmpl_id', 'chemical_substance_id')
    def _onchange_inputs(self):
        if self.query_mode == 'by_material' and self.product_tmpl_id:
            mapping = self.env['is.chemical.material.mapping'].search([
                ('product_tmpl_id', '=', self.product_tmpl_id.id)
            ], limit=1)
            if mapping:
                self.chemical_substance_id = mapping.chemical_substance_id.id
                self.cas_number = mapping.cas_number or mapping.chemical_substance_id.cas_number
                self.hs_code = getattr(self.product_tmpl_id, 'hs_code', False)
                self.commercial_name = mapping.commercial_name or self.product_tmpl_id.name
                self.concentration_percentage = mapping.concentration_percentage
                self.purpose_of_use_id = mapping.purpose_of_use_id.id
            else:
                self.cas_number = False
                self.hs_code = getattr(self.product_tmpl_id, 'hs_code', False)
                self.commercial_name = self.product_tmpl_id.name
        elif self.query_mode == 'by_chemical' and self.chemical_substance_id:
            self.cas_number = self.chemical_substance_id.cas_number
            self.hs_code = False
            self.commercial_name = self.chemical_substance_id.name

    def action_simulate(self):
        self.ensure_one()
        rule_obj = self.env['is.chemical.regulatory.rule']

        target_cas = self.cas_number or (self.chemical_substance_id and self.chemical_substance_id.cas_number)
        target_hs = self.hs_code

        matched_rule = rule_obj.evaluate_chemical_obligations(
            cas_number=target_cas,
            hs_code=target_hs,
            concentration=self.concentration_percentage,
        )[:1]

        if matched_rule:
            is_lic = matched_rule.required_permit_type in ('restricted_license', 'conditional_cert', 'transport_permit')
            is_proh = matched_rule.rule_category == 'prohibited_chemical_block'
            self.write({
                'is_simulated': True,
                'result_obligation_category': matched_rule.rule_category,
                'result_requires_license': is_lic or matched_rule.rule_category in ('specially_controlled_group_1', 'specially_controlled_group_2'),
                'result_license_type': dict(rule_obj._fields['rule_category'].selection).get(matched_rule.rule_category),
                'result_licensing_authority': False,
                'result_nsw_procedure_code': matched_rule.nsw_procedure_code,
                'result_is_prohibited': is_proh,
                'result_notes': (
                    f"Quy tắc nội bộ khớp: {matched_rule.legal_basis}.\n"
                    f"Ngưỡng cấu hình: >= {matched_rule.threshold_concentration}% (Hàm lượng khai báo: {self.concentration_percentage}%).\n"
                    "Kết quả sàng lọc nội bộ, không xác nhận nghĩa vụ chính thức; cần rà soát trước khi xử lý."
                ),
                'result_rule_id': matched_rule.id,
            })
        else:
            self.write({
                'is_simulated': True,
                'result_obligation_category': 'review',
                'result_requires_license': False,
                'result_license_type': False,
                'result_licensing_authority': False,
                'result_nsw_procedure_code': False,
                'result_is_prohibited': False,
                'result_notes': 'Không có quy tắc nội bộ phù hợp; cần rà soát chuyên môn trước khi xử lý.',
                'result_rule_id': False,
            })

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'is.chemical.obligation.simulator',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_create_dossier_from_simulation(self):
        self.ensure_one()
        rule = self.env['is.chemical.regulatory.rule'].evaluate_chemical_obligations(
            cas_number=self.cas_number or (self.chemical_substance_id and self.chemical_substance_id.cas_number),
            hs_code=self.hs_code,
            concentration=self.concentration_percentage,
        )[:1]
        if not self.is_simulated or not rule or rule != self.result_rule_id:
            raise UserError(_('Cần chạy lại sàng lọc với quy tắc nội bộ đã được phê duyệt trước khi tạo hồ sơ.'))
        if rule.rule_category == 'prohibited_chemical_block':
            raise UserError(_('Cờ dừng xử lý nội bộ đang bật; cần rà soát chuyên môn trước khi tạo hồ sơ.'))

        dossier_type_map = {
            'specially_controlled_group_1': 'specially_controlled_group_1',
            'specially_controlled_group_2': 'specially_controlled_group_2',
            'restricted_chemical_license': 'restricted_license',
            'precursor_narcotics_explosives': 'precursor_permit',
            'mandatory_nsw_declaration': 'nsw_declaration',
        }
        d_type = dossier_type_map.get(rule.rule_category, 'general_compliance')

        product = False
        if self.product_tmpl_id:
            product = self.env['product.product'].search([('product_tmpl_id', '=', self.product_tmpl_id.id)], limit=1)

        t_name = self.commercial_name or (self.product_tmpl_id and self.product_tmpl_id.name) or (self.chemical_substance_id and self.chemical_substance_id.name)
        if not t_name:
            raise UserError(_('Cần tên thương mại hoặc hóa chất trước khi tạo hồ sơ.'))

        line_vals = {
            'product_id': product.id if product else False,
            'trade_name': t_name,
            'chemical_substance_id': self.chemical_substance_id.id if self.chemical_substance_id else False,
            'cas_number': self.cas_number,
            'hs_code': self.hs_code,
            'concentration_percentage': self.concentration_percentage,
            'net_weight_kg': self.quantity_estimate_kg,
            'purpose_of_use_id': self.purpose_of_use_id.id if self.purpose_of_use_id else False,
        }

        dossier = self.env['is.chemical.compliance.dossier'].create({
            'name': _('New'),
            'dossier_type': d_type,
            'nsw_procedure_code': rule.nsw_procedure_code,
            'compliance_notes': rule.legal_basis,
            'line_ids': [(0, 0, line_vals)],
        })

        return {
            'type': 'ir.actions.act_window',
            'name': _('Hồ sơ Tuân thủ Hóa chất Mới Tạo'),
            'res_model': 'is.chemical.compliance.dossier',
            'res_id': dossier.id,
            'view_mode': 'form',
            'target': 'current',
        }
