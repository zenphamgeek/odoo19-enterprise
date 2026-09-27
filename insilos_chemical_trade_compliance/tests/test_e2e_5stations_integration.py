# -*- coding: utf-8 -*-
# Part of Insilos. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.addons.insilos_chemical_trade_compliance.models.is_chemical_permit_quota import _CUSTOMS_CLEARANCE_CAPABILITY
from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install', 'insilos_chemical_trade_compliance')
class TestE2E5StationsIntegration(TransactionCase):

    def setUp(self):
        super().setUp()
        self.company = self.env.company

        # 1. HSE Master & Facility
        self.facility = self.env['is.hse.facility'].create({
            'name': 'Nhà máy Phân tích Hóa nghiệm Miền Nam',
            'code': 'FAC-HCM-E2E-01',
            'address': 'KCN Hiệp Phước, TP. Hồ Chí Minh',
        })

        self.substance = self.env['is.hse.chemical.substance'].create({
            'name': 'Sulfuric Acid 98% Industrial E2E',
            'cas_number': 'TEST-7664-93-9-E2E',
            'formula': 'H2SO4',
            'un_number': 'UN 1830',
            'hazard_classification': 'conditional',
            'ghs_corrosive': True,
            'ghs_toxic': True,
        })

        self.permit = self.env['is.hse.product.permit'].create({
            'name': 'Giấy phép Nhập khẩu Hóa chất Điều kiện 2026 E2E',
            'permit_number': 'GP-BCT-E2E-2026-01',
            'permit_type': 'conditional_cert',
            'chemical_substance_id': self.substance.id,
            'is_perpetual': True,
        })

        # 2. HS Tariff & Customs Ruling
        self.tariff = self.env['is.hs.tariff'].create({
            'hs_code': '2807.00.00',
            'description_vi': 'Axit sunphuric; oleum',
            'import_duty_rate': 0.0,
            'vat_rate': 10.0,
        })

        # 3. Product Template & Chemical Mapping
        self.product = self.env['product.template'].create({
            'name': 'Axit Sunfuric Kỹ thuật H2SO4 98% Phuy 250kg',
            'type': 'consu',
            'is_hazardous_chemical': True,
            'chemical_substance_id': self.substance.id,
            'hs_code_customs': '2807.00.00',
        })

        self.purpose = self.env['is.chemical.purpose.of.use'].create({
            'code': 'E2E-MFG',
            'name': 'Sản xuất công nghiệp & Xử lý nước thải',
            'industry_category': 'water_treatment',
        })

        self.mapping = self.env['is.chemical.material.mapping'].create({
            'product_tmpl_id': self.product.id,
            'chemical_substance_id': self.substance.id,
            'commercial_name': 'H2SO4 98% Pure Industrial',
            'concentration_percentage': 98.0,
            'uom_to_kg_ratio': 250.0,
            'purpose_of_use_id': self.purpose.id,
        })

        # 4. Quota Ledger
        self.quota = self.env['is.chemical.permit.quota']._create_from_customs_workflow({
            'permit_id': self.permit.id,
            'chemical_substance_id': self.substance.id,
            'allocated_quota_kg': 50000.0,
        }, _CUSTOMS_CLEARANCE_CAPABILITY)

        # 5. Partner & PO
        self.supplier = self.env['res.partner'].create({
            'name': 'Mitsui Chemical Global Exporter',
            'supplier_rank': 1,
        })

    def test_01_e2e_station1_idp_to_station3_chemical_dossier(self):
        """Test E2E Station 1 (Logistics IDP) auto-generates Chemical Compliance Dossier."""
        # 1. Create Logistics IDP Case
        case = self.env['logistics.idp.case'].create({
            'name': 'CASE-IDP-LOG-E2E-2026',
            'po_reference': 'PO-E2E-999',
            'supplier_reference': 'Mitsui Chemical Global Exporter',
            'shipment_reference': 'BL-TYO-SGN-2026',
        })

        # 2. Trigger automated Chemical Dossier Generation from IDP Case
        action = case.action_generate_chemical_dossier_from_idp()
        self.assertEqual(action['res_model'], 'is.chemical.compliance.dossier')
        dossier_id = action['res_id']
        dossier = self.env['is.chemical.compliance.dossier'].browse(dossier_id)

        self.assertTrue(dossier)
        self.assertEqual(dossier.case_id.id, case.id)
        self.assertTrue(len(dossier.line_ids) > 0)
        self.assertEqual(dossier.state, 'draft')
        self.assertFalse(dossier.nsw_payload_json)

    def test_02_e2e_station3_customs_clearance_refuses_quota_deduction(self):
        """Test an internal customs number cannot deduct permit quota."""
        dossier = self.env['is.chemical.compliance.dossier'].create({
            'name': 'DOSSIER-E2E-CLEARANCE-01',
            'importer_company_id': self.company.id,
            'customs_declaration_no': 'TKHQ-105599882200',
        })

        self.env['is.chemical.compliance.dossier.line'].create({
            'dossier_id': dossier.id,
            'product_id': self.product.product_variant_id.id if self.product.product_variant_id else False,
            'trade_name': 'H2SO4 98% Pure Industrial',
            'chemical_substance_id': self.substance.id,
            'permit_id': self.permit.id,
            'concentration_percentage': 98.0,
            'net_weight_kg': 5000.0,
        })

        initial_remaining = self.quota.remaining_quota_kg

        # Test-only predecessor setup.
        models.Model.write(dossier, {'state': 'internally_approved'})
        with self.assertRaisesRegex(UserError, 'immutable externally verified customs receipt'):
            dossier.action_deduct_permit_quota()
        self.assertEqual(dossier.state, 'internally_approved')
        self.quota._compute_quota_metrics()
        self.assertEqual(self.quota.consumed_quota_kg, 0.0)
        self.assertEqual(self.quota.remaining_quota_kg, initial_remaining)

    def test_03_e2e_station4_hse_to_station5_fsm_task_usage(self):
        """Test E2E HSE safety check on FSM Task and automatic 5-stage usage logging upon completion."""
        # 1. Create FSM Task at HSE Facility
        project = self.env['project.project'].create({
            'name': 'Dự án Bảo trì Hệ thống Xử lý Hóa chất',
        })

        task = self.env['project.task'].create({
            'name': 'Bảo trì Bồn chứa Axit Sunfuric Nhà máy Hiệp Phước',
            'project_id': project.id,
            'hse_facility_id': self.facility.id,
            'chemical_substance_ids': [(6, 0, [self.substance.id])],
        })

        # 2. Check safety permits on Task
        res = task.action_check_safety_permits()
        self.assertEqual(res['type'], 'ir.actions.client')

        # 3. View SDS Cards Action
        sds_action = task.action_view_sds_cards()
        self.assertEqual(sds_action['res_model'], 'is.hse.chemical.substance')

        # 4. Mark Task as Done -> Triggers automatic 5-stage usage tracking
        task.write({'state': '1_done'})

        # Verify 5-stage usage tracking record
        current_year = fields.Date.today().year
        tracking = self.env['is.chemical.usage.tracking'].search([
            ('chemical_substance_id', '=', self.substance.id),
            ('reporting_year', '=', current_year),
        ], limit=1)
        self.assertTrue(tracking)

    def test_04_unified_command_center_hub_action(self):
        """Verify the Unified 5-Station Operations Hub view and action."""
        hub = self.env.ref('insilos_chemical_trade_compliance.action_is_unified_operations_hub')
        self.assertTrue(hub)
        self.assertEqual(hub.res_model, 'res.config.settings')
        self.assertEqual(hub.view_mode, 'form')
