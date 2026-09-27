# -*- coding: utf-8 -*-
import ast
from pathlib import Path
from xml.etree import ElementTree

from odoo.tests.common import TransactionCase, tagged
from odoo.exceptions import UserError

@tagged('post_install', '-at_install', 'insilos_chemical_trade_compliance')
class TestDossierReportsAndSimulator(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))

        # 1. Chemical Master (is.hse.chemical.substance)
        cls.chem_toluene = cls.env['is.hse.chemical.substance'].create({
            'name': 'Toluene C7H8 99.8% Test',
            'cas_number': 'TEST-108-88-3-SIM',
            'hazard_classification': 'hazardous_general',
        })
        cls.chem_h2so4 = cls.env['is.hse.chemical.substance'].create({
            'name': 'Sulfuric Acid H2SO4 98% Test',
            'cas_number': 'TEST-7664-93-9-SIM',
            'hazard_classification': 'restricted',
        })
        cls.chem_aldrin = cls.env['is.hse.chemical.substance'].create({
            'name': 'Aldrin Prohibited Test',
            'cas_number': 'TEST-309-00-2-SIM',
            'hazard_classification': 'prohibited',
        })

        # 2. Material Products
        cls.product_toluene = cls.env['product.template'].create({
            'name': 'Toluene Industrial Drum 200L',
            'type': 'consu',
            'is_hazardous_chemical': True,
            'chemical_substance_id': cls.chem_toluene.id,
        })
        cls.product_h2so4 = cls.env['product.template'].create({
            'name': 'Sulfuric Acid 98% IBC Tank',
            'type': 'consu',
            'is_hazardous_chemical': True,
            'chemical_substance_id': cls.chem_h2so4.id,
        })

        # 3. Purpose of Use
        cls.purpose_paint = cls.env['is.chemical.purpose.of.use'].create({
            'name': 'Dung môi pha chế sơn & phủ công nghiệp',
            'code': 'PURPOSE-PAINT-TEST-SIM',
            'max_annual_demand_kg': 50000.0,
        })

        # 4. Material Mapping
        cls.mapping_toluene = cls.env['is.chemical.material.mapping'].create({
            'product_tmpl_id': cls.product_toluene.id,
            'chemical_substance_id': cls.chem_toluene.id,
            'commercial_name': 'Toluene Solv 200L',
            'uom_to_kg_ratio': 173.0,
            'purpose_of_use_id': cls.purpose_paint.id,
            'concentration_percentage': 99.8,
        })

        # 5. Regulatory Rules
        cls.legal_document = cls.env['is.hse.legal.document'].create({
            'name': 'Official simulator rule test source', 'code': 'TEST-SIM-CHEM-2026',
            'issuer': 'Test Authority', 'issued_date': '2026-01-01',
            'effective_date': '2026-01-01',
            'source_url': 'https://official.example.test/simulator-chemical-rule',
            'source_content_sha256': 'c' * 64, 'source_version': '2026.1',
        })
        cls.legal_document.action_activate()
        cls.rule_nsw = cls.env['is.chemical.regulatory.rule'].create({
            'name': 'Khai báo Hóa chất NSW Toluene Sim',
            'chemical_substance_id': cls.chem_toluene.id,
            'cas_number': 'TEST-108-88-3-SIM',
            'rule_category': 'mandatory_nsw_declaration',
            'threshold_concentration': 1.0,
            'nsw_procedure_code': 'BCT00001',
            'legal_basis': 'Official test provision',
            'legal_document_id': cls.legal_document.id,
            'effective_from': '2026-01-01',
            'effective_to': '2026-12-31',
        })
        cls.rule_group1 = cls.env['is.chemical.regulatory.rule'].create({
            'name': 'Giấy phép Nhóm 1 H2SO4 Sim',
            'chemical_substance_id': cls.chem_h2so4.id,
            'cas_number': 'TEST-7664-93-9-SIM',
            'rule_category': 'specially_controlled_group_1',
            'threshold_concentration': 50.0,
            'required_permit_type': 'restricted_license',
            'nsw_procedure_code': 'BCT00002',
            'legal_basis': 'Official test provision',
            'legal_document_id': cls.legal_document.id,
            'effective_from': '2026-01-01',
            'effective_to': '2026-12-31',
        })
        cls.rule_aldrin = cls.env['is.chemical.regulatory.rule'].create({
            'name': 'Chất Cấm Aldrin Phụ lục III Sim',
            'chemical_substance_id': cls.chem_aldrin.id,
            'cas_number': 'TEST-309-00-2-SIM',
            'rule_category': 'prohibited_chemical_block',
            'threshold_concentration': 0.1,
            'legal_basis': 'Official test provision',
            'legal_document_id': cls.legal_document.id,
            'effective_from': '2026-01-01',
            'effective_to': '2026-12-31',
        })
        rules = cls.rule_nsw + cls.rule_group1 + cls.rule_aldrin
        rules.action_submit_for_review()
        approver = cls.env['res.users'].create({
            'name': 'Simulator Rule Approver', 'login': 'simulator-rule-approver@example.test',
            'group_ids': [(6, 0, [
                cls.env.ref('insilos_chemical_trade_compliance.group_chemical_compliance_manager').id,
                cls.env.ref('insilos_hse_compliance.group_hse_manager').id,
            ])],
        })
        rules.with_user(approver).action_activate()

    def test_00_simulator_runtime_copy_is_internal_screening_only(self):
        module = Path(__file__).parents[1]
        simulator = (module / 'wizard' / 'is_chemical_obligation_simulator.py').read_text()
        view = (module / 'wizard' / 'is_chemical_obligation_simulator_views.xml').read_text()
        for text in (
            'Kết quả sàng lọc nội bộ, không xác nhận nghĩa vụ chính thức',
            'Cờ dừng xử lý nội bộ',
            'Kết quả không xác nhận nghĩa vụ, cấm đoán hoặc giấy phép chính thức',
        ):
            self.assertIn(text, simulator + view)
        for text in (
            'EVALUATE LEGAL OBLIGATIONS INSTANTLY',
            'CẢNH BÁO: HÓA CHẤT CẤM!',
            'Hệ thống tự động kích hoạt chốt chặn và từ chối xử lý hồ sơ.',
        ):
            self.assertNotIn(text, simulator + view)

    def test_01_obligation_simulator_by_material(self):
        """Test simulation by Material ERP product"""
        sim = self.env['is.chemical.obligation.simulator'].create({
            'query_mode': 'by_material',
            'product_tmpl_id': self.product_toluene.id,
        })
        sim._onchange_inputs()
        self.assertEqual(sim.cas_number, 'TEST-108-88-3-SIM')
        self.assertEqual(sim.chemical_substance_id.id, self.chem_toluene.id)

        sim.action_simulate()
        self.assertTrue(sim.is_simulated)
        self.assertEqual(sim.result_obligation_category, 'mandatory_nsw_declaration')
        self.assertEqual(sim.result_nsw_procedure_code, self.rule_nsw.nsw_procedure_code)
        self.assertIn(self.rule_nsw.legal_basis, sim.result_notes)
        self.assertFalse(sim.result_requires_license)
        self.assertFalse(sim.result_is_prohibited)

    def test_02_obligation_simulator_group1_and_dossier_creation(self):
        """Test simulation for Group 1 chemical and 1-click dossier creation"""
        sim = self.env['is.chemical.obligation.simulator'].create({
            'query_mode': 'by_chemical',
            'chemical_substance_id': self.chem_h2so4.id,
            'concentration_percentage': 98.0,
            'quantity_estimate_kg': 5000.0,
        })
        sim.action_simulate()
        self.assertEqual(sim.result_obligation_category, 'specially_controlled_group_1')
        self.assertTrue(sim.result_requires_license)

        action = sim.action_create_dossier_from_simulation()
        dossier = self.env['is.chemical.compliance.dossier'].browse(action['res_id'])
        self.assertEqual(dossier.dossier_type, 'specially_controlled_group_1')
        self.assertEqual(len(dossier.line_ids), 1)
        self.assertEqual(dossier.line_ids[0].net_weight_kg, 5000.0)
        self.assertEqual(dossier.nsw_procedure_code, self.rule_group1.nsw_procedure_code)
        self.assertEqual(dossier.compliance_notes, self.rule_group1.legal_basis)
        self.assertEqual(dossier.line_ids[0].regulatory_status, 'review')
        self.assertFalse(dossier.line_ids[0].quantity)
        self.assertFalse(dossier.line_ids[0].package_type)

    def test_03_obligation_simulator_unmatched_requires_legal_review(self):
        sim = self.env['is.chemical.obligation.simulator'].create({
            'query_mode': 'by_manual',
            'cas_number': 'TEST-NO-RULE-SIM',
            'commercial_name': 'Unmatched Test Chemical',
        })
        sim.action_simulate()
        self.assertEqual(sim.result_obligation_category, 'review')
        self.assertFalse(sim.result_rule_id)
        with self.assertRaises(UserError):
            sim.action_create_dossier_from_simulation()

    def test_04_obligation_simulator_prohibited_block(self):
        """Test simulator blocks creation of dossier for prohibited chemicals"""
        sim = self.env['is.chemical.obligation.simulator'].create({
            'query_mode': 'by_manual',
            'cas_number': 'TEST-309-00-2-SIM',
            'hs_code': '2903.82.00',
            'concentration_percentage': 100.0,
        })
        sim.action_simulate()
        self.assertTrue(sim.result_is_prohibited)
        self.assertEqual(sim.result_obligation_category, 'prohibited_chemical_block')

        with self.assertRaises(UserError):
            sim.action_create_dossier_from_simulation()

    def test_04_forged_simulator_result_cannot_create_dossier(self):
        sim = self.env['is.chemical.obligation.simulator'].create({
            'query_mode': 'by_manual',
            'cas_number': 'TEST-NO-RULE-FORGED-SIM',
            'commercial_name': 'Forged rule chemical',
        })
        sim.write({
            'is_simulated': True,
            'result_obligation_category': 'mandatory_nsw_declaration',
            'result_rule_id': self.rule_nsw.id,
            'result_nsw_procedure_code': self.rule_nsw.nsw_procedure_code,
        })
        with self.assertRaises(UserError):
            sim.action_create_dossier_from_simulation()

    def test_04_usage_tracking_erp_sync(self):
        """Test automated ERP stock move synchronization on 5-stage usage tracking"""
        facility = self.env['is.hse.facility'].create({
            'name': 'Nhà máy Test BH2 Sim',
            'code': 'FAC-TEST-SIM-01',
        })
        tracking = self.env['is.chemical.usage.tracking'].create({
            'chemical_substance_id': self.chem_toluene.id,
            'reporting_year': 2026,
            'facility_id': facility.id,
            'planned_demand_kg': 35000.0,
        })

        # Run stock move sync
        res = tracking.action_sync_from_erp_stock_moves()
        self.assertEqual(res['type'], 'ir.actions.client')

    def test_05_quick_fix_mapping_action(self):
        """Test quick fix mapping action on exception"""
        prod_unmapped = self.env['product.template'].create({
            'name': 'Unmapped Raw Solvent X',
            'type': 'consu',
            'is_hazardous_chemical': True,
        })
        exc = self.env['is.chemical.compliance.exception'].create({
            'name': 'Missing Mapping Test',
            'exception_type': 'missing_mapping',
            'severity': 'critical',
            'product_tmpl_id': prod_unmapped.id,
        })

        action = exc.action_quick_fix_mapping()
        self.assertEqual(action['res_model'], 'is.chemical.material.mapping')
        self.assertEqual(action['context']['default_product_tmpl_id'], prod_unmapped.id)

    def test_06_report_route_enforces_record_read_access(self):
        source = Path(__file__).parents[1] / 'controllers' / 'report.py'
        self.assertIn("records.check_access('read')", source.read_text())
        self.assertIn("records.check_access_rule('read')", source.read_text())

    def test_07_report_guard_covers_qweb_pdf_actions(self):
        module = Path(__file__).parents[1]
        report_files = (
            (module / 'reports' / 'is_chemical_dossier_reports.xml', None),
            (module.parent / 'insilos_hse_compliance' / 'reports' / 'is_hse_report_actions.xml', 'action_report_hse_product_permit'),
        )
        guarded_names = {
            node.value
            for node in ast.walk(ast.parse((module / 'controllers' / 'report.py').read_text()))
            if isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and node.value.startswith(('insilos_chemical_trade_compliance.', 'insilos_hse_compliance.'))
        }
        for report_file, eligible_action_id in report_files:
            for action in ElementTree.parse(report_file).findall(".//record[@model='ir.actions.report']"):
                fields = {field.get('name'): (field.text or '').strip() for field in action}
                if fields.get('report_type') != 'qweb-pdf' or (
                    eligible_action_id and action.get('id') != eligible_action_id
                ):
                    continue
                self.assertIn(fields['report_name'], guarded_names, action.get('id'))

    def test_08_non_draft_dossier_report_requires_trusted_rules(self):
        source = Path(__file__).parents[1] / 'controllers' / 'report.py'
        route = next(
            node for node in ast.walk(ast.parse(source.read_text()))
            if isinstance(node, ast.FunctionDef) and node.name == 'report_routes'
        )
        rendered = ast.unparse(route)
        self.assertIn("dossier.state != 'draft'", rendered)
        self.assertIn('._check_regulatory_review()', rendered)
        self.assertIn('report_chemical_dossier_application_doc', rendered)
        self.assertIn('report_chemical_nsw_declaration_doc', rendered)
        self.assertIn('governed evidence and publication controls', rendered)

    def test_09_only_governed_dossier_pdf_action_remains(self):
        report_app = self.env.ref('insilos_chemical_trade_compliance.action_report_chemical_dossier_application')
        self.assertTrue(report_app)
        self.assertEqual(report_app.report_type, 'qweb-pdf')
        actions = (Path(__file__).parents[1] / 'reports' / 'is_chemical_dossier_reports.xml').read_text()
        for unavailable_action in (
            'action_report_chemical_usage_tracking',
            'action_report_chemical_nsw_declaration',
            'action_report_chemical_permit_quota',
        ):
            self.assertNotIn(unavailable_action, actions)
        templates = Path(__file__).parents[1] / 'reports' / 'is_chemical_dossier_templates.xml'
        template_text = templates.read_text()
        application_template = ElementTree.parse(templates).find(
            ".//template[@id='report_chemical_dossier_application_doc']"
        )
        application_text = ElementTree.tostring(application_template, encoding='unicode')
        self.assertIn('DỰ THẢO NỘI BỘ PHỤC VỤ RÀ SOÁT VÀ CHUẨN BỊ DỮ LIỆU', application_text)
        for obsolete_text in (
            'CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM',
            'ĐƠN ĐỀ NGHỊ CẤP GIẤY PHÉP',
            'Kính gửi: Cục Hóa chất',
            'Cam kết của doanh nghiệp',
            'ĐẠI DIỆN THEO PHÁP LUẬT CỦA DOANH NGHIỆP',
        ):
            self.assertNotIn(obsolete_text, application_text)
        self.assertIn('KHÔNG XÁC NHẬN GIẤY PHÉP HOẶC THẨM QUYỀN CƠ QUAN NHÀ NƯỚC', template_text)
        usage_template = ElementTree.parse(templates).find(
            ".//template[@id='report_chemical_usage_tracking_doc']"
        )
        usage_text = ElementTree.tostring(usage_template, encoding='unicode')
        self.assertIn('SỔ THEO DÕI NỘI BỘ SỬ DỤNG HÓA CHẤT', usage_text)
        self.assertIn('BẢN GHI NỘI BỘ/DỰ THẢO; KHÔNG PHẢI HỒ SƠ CẤP PHÉP, BÁO CÁO CHÍNH THỨC, XÁC NHẬN HOẶC CĂN CỨ PHÁP LÝ', usage_text)
        self.assertIn('NGƯỜI LẬP NỘI BỘ', usage_text)
        self.assertIn('NGƯỜI RÀ SOÁT NỘI BỘ', usage_text)
        self.assertNotIn('PHỤC VỤ CẤP PHÉP/BÁO CÁO', usage_text)
        self.assertNotIn('ĐẠI DIỆN DOANH NGHIỆP', usage_text)
        self.assertNotIn('Ký, đóng dấu', usage_text)
        self.assertIn('NHẬT KÝ GHI NHẬN NỘI BỘ BIẾN ĐỘNG HẠN NGẠCH', template_text.upper())
        self.assertNotIn('Ngày Thông quan', template_text)

        hub_action = self.env.ref('insilos_chemical_trade_compliance.action_is_chemical_onboarding_hub')
        self.assertTrue(hub_action)
        self.assertEqual(hub_action.res_model, 'res.config.settings')
