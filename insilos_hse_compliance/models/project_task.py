# -*- coding: utf-8 -*-
# Part of Insilos. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class ProjectTask(models.Model):
    _inherit = 'project.task'

    hse_facility_id = fields.Many2one('is.hse.facility', string='HSE Facility',
                                      tracking=True, index=True,
                                      help='Industrial plant, chemical warehouse, or facility where maintenance takes place.')
    
    has_hazardous_materials = fields.Boolean(string='Requires Hazardous Chemical Safety Protocols',
                                             compute='_compute_hazardous_materials', store=True)
    chemical_substance_ids = fields.Many2many('is.hse.chemical.substance',
                                              'project_task_chemical_substance_rel',
                                              'task_id', 'substance_id',
                                              string='Relevant Chemical Substances & SDS',
                                              compute='_compute_hazardous_materials', store=True)
    
    permit_warning = fields.Char(string='Safety & Permit Status Warning', compute='_compute_permit_warning')

    @api.depends('hse_facility_id')
    def _compute_hazardous_materials(self):
        for task in self:
            chemicals = self.env['is.hse.chemical.substance']
            # 1. Check from task materials / products used in FSM if present
            if hasattr(task, 'material_line_ids') and task.material_line_ids:
                for mat in task.material_line_ids:
                    prod = getattr(mat, 'product_id', False)
                    if prod and getattr(prod, 'chemical_substance_id', False):
                        chemicals |= prod.chemical_substance_id
            
            # 2. Check from product template linkages
            if hasattr(task, 'product_id') and task.product_id:
                if getattr(task.product_id, 'chemical_substance_id', False):
                    chemicals |= task.product_id.chemical_substance_id

            # 3. Check from facility registered chemicals
            if not chemicals and task.hse_facility_id:
                pass  # Facility context

            task.chemical_substance_ids = [(6, 0, chemicals.ids)]
            task.has_hazardous_materials = bool(chemicals)

    def _compute_permit_warning(self):
        for task in self:
            warning = False
            if task.chemical_substance_ids and task.hse_facility_id:
                # ponytail: internal metadata only; use an approved legal dataset before external validity checks.
                untracked_chems = []
                for chem in task.chemical_substance_ids:
                    permits = self.env['is.hse.product.permit'].search([
                        ('chemical_substance_id', '=', chem.id),
                    ])
                    if not permits:
                        untracked_chems.append(chem.name)
                if untracked_chems:
                    warning = _("YÊU CẦU RÀ SOÁT NỘI BỘ: Hóa chất [%s] chưa có bản ghi giấy phép/cấu hình nội bộ; không thể kết luận nghĩa vụ hoặc hiệu lực.") % (", ".join(untracked_chems))
            task.permit_warning = warning

    def action_view_sds_cards(self):
        """View all SDS and GHS safety cards associated with this FSM task."""
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('insilos_hse_compliance.action_is_hse_chemical_substance')
        action['domain'] = [('id', 'in', self.chemical_substance_ids.ids)]
        action['context'] = {'default_company_id': self.company_id.id if self.company_id else self.env.company.id}
        return action

    def action_check_safety_permits(self):
        """Validate safety permits prior to dispatching hazardous site work."""
        self.ensure_one()
        if not self.hse_facility_id:
            raise UserError(_("Vui lòng chọn Cơ sở / Kho bãi HSE (Facility) trước khi kiểm tra an toàn!"))
        
        if self.permit_warning:
            raise UserError(self.permit_warning)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("Đã hoàn tất rà soát bản ghi nội bộ"),
                'message': _("Không phát hiện thiếu bản ghi giấy phép/cấu hình nội bộ; chưa xác nhận nghĩa vụ pháp lý hoặc hiệu lực bên ngoài."),
                'type': 'warning',
                'sticky': False,
            }
        }
