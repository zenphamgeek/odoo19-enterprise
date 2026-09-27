# -*- coding: utf-8 -*-
from pathlib import Path

from odoo.tests.common import TransactionCase, tagged

@tagged('post_install', '-at_install', 'insilos_hse_compliance')
class TestHSEReportsAndOnboarding(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))

        cls.facility = cls.env['is.hse.facility'].create({
            'name': 'Nhà máy Sản xuất Hóa chất Hải Phòng Test',
            'code': 'FAC-HP-TEST-99',
            'address': 'KCN Đình Vũ, Hải Phòng',
        })

        cls.substance = cls.env['is.hse.chemical.substance'].create({
            'name': 'Toluene Solvent Industrial Test 99',
            'cas_number': 'TEST-108-88-3-REP',
            'formula': 'C7H8',
            'un_number': 'UN 1294',
            'hazard_classification': 'conditional',
            'ghs_signal_word': 'danger',
            'ghs_flammable': True,
            'ghs_toxic': True,
        })

        cls.permit = cls.env['is.hse.product.permit'].create({
            'name': 'Giấy phép Nhập khẩu & Sử dụng Hóa chất Hạn chế 2026 Test',
            'permit_number': 'TEST-GP-BCT-2026-99',
            'permit_type': 'restricted_license',
            'issuing_authority': 'Cục Hóa chất - Bộ Công Thương',
            'chemical_substance_id': cls.substance.id,
            'conditions_summary': 'Chỉ sử dụng đúng mục đích tại cơ sở KCN Đình Vũ, tuân thủ QCVN 05A:2020/BCT.',
        })

        cls.register = cls.env['is.hse.legal.register'].create({
            'name': 'Sổ Đăng ký Tuân thủ HSE 2026 — Nhà máy Hải Phòng Test',
            'facility_id': cls.facility.id,
            'year': 2026,
        })

    def test_01_hse_reports_exist_and_types(self):
        """Verify all 3 HSE QWeb PDF reports are properly registered."""
        rep_permit = self.env.ref('insilos_hse_compliance.action_report_hse_product_permit')
        self.assertTrue(rep_permit)
        self.assertEqual(rep_permit.report_type, 'qweb-pdf')

        rep_sop = self.env.ref('insilos_hse_compliance.action_report_hse_chemical_safety_sop')
        self.assertTrue(rep_sop)
        self.assertEqual(rep_sop.report_type, 'qweb-pdf')

        rep_audit = self.env.ref('insilos_hse_compliance.action_report_hse_legal_compliance_audit')
        self.assertTrue(rep_audit)
        self.assertEqual(rep_audit.report_type, 'qweb-pdf')

    def test_03_reports_do_not_fabricate_compliance_or_legal_provenance(self):
        permit_template = self.env.ref('insilos_hse_compliance.report_hse_product_permit_doc').arch
        audit_template = self.env.ref('insilos_hse_compliance.report_hse_legal_compliance_audit_doc').arch
        sds_template = self.env.ref('insilos_hse_compliance.report_hse_safety_data_sheet_doc').arch
        self.assertIn('HỒ SƠ THEO DÕI NỘI BỘ', permit_template)
        self.assertIn('Cơ quan ban hành (theo khai báo):', permit_template)
        self.assertIn('Đơn vị liên quan:', permit_template)
        self.assertIn('Danh mục Vật tư / Hóa chất liên quan theo hồ sơ:', permit_template)
        self.assertIn('NGƯỜI RÀ SOÁT NỘI BỘ', permit_template)
        self.assertNotIn('CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM', permit_template)
        self.assertNotIn('Độc lập - Tự do - Hạnh phúc', permit_template)
        self.assertNotIn('CƠ QUAN CẤP PHÉP:', permit_template)
        self.assertNotIn('Đơn vị được cấp phép:', permit_template)
        self.assertNotIn('phạm vi cấp phép', permit_template)
        self.assertNotIn("o.state != 'valid'", permit_template)
        self.assertIn('BẢN DỰ THẢO NỘI BỘ', permit_template)
        self.assertIn('KHÔNG XÁC NHẬN GIẤY PHÉP, CHỨNG NHẬN HOẶC CHẤP THUẬN CỦA CƠ QUAN CÓ THẨM QUYỀN', permit_template)
        self.assertNotIn('CỤC HÓA CHẤT - BỘ CÔNG THƯƠNG', permit_template)
        sop_template = (Path(__file__).resolve().parents[1] / 'reports' / 'is_hse_report_templates.xml').read_text(encoding='utf-8')
        self.assertIn('BẢN DỰ THẢO NỘI BỘ — KHÔNG DÙNG THAY THẾ SDS HOẶC QUY TRÌNH KHẨN CẤP ĐƯỢC PHÊ DUYỆT.', sop_template)
        self.assertIn('theo SDS và quy trình khẩn cấp đã được phê duyệt cho đúng hóa chất này.', sop_template)
        self.assertNotIn('Găng tay chuyên dụng chống hóa chất (Nitrile/Butyl).', sop_template)
        self.assertNotIn('Sử dụng bình bọt Foam, bột khô ABC hoặc CO2.', sop_template)
        self.assertIn('Chỉ phản ánh đánh giá nội bộ trên các nghĩa vụ đã ghi nhận; không phải kết luận tuân thủ pháp lý.', audit_template)
        self.assertIn('CHƯA ĐÁNH GIÁ — không có kết luận tuân thủ', audit_template)
        self.assertIn('CHƯA ĐÁNH GIÁ', audit_template)
        self.assertIn('Chưa đánh giá hoặc xác minh nguồn pháp lý.', sds_template)
        self.assertIn('SDS NỘI BỘ — CHƯA XÁC MINH', sds_template)
        self.assertNotIn('VERIFIED SDS', sds_template)

    def test_03_onboarding_hub_action_and_view(self):
        """Verify HSE Onboarding Hub action and internal-only wording."""
        action = self.env.ref('insilos_hse_compliance.action_is_hse_onboarding_hub')
        self.assertTrue(action)
        self.assertEqual(action.res_model, 'res.config.settings')
        self.assertEqual(action.view_mode, 'form')
        onboarding_template = self.env.ref('insilos_hse_compliance.view_is_hse_onboarding_form').arch
        self.assertIn('Không gian theo dõi nội bộ', onboarding_template)
        self.assertIn('đối chiếu SDS nguồn trước khi sử dụng', onboarding_template)
        self.assertIn('không thay thế kết luận tuân thủ hoặc hồ sơ nộp cơ quan', onboarding_template)
        self.assertNotIn('Enterprise Ready', onboarding_template)
        self.assertNotIn('lập biên bản kiểm toán phục vụ thanh tra', onboarding_template)
        legal_register_template = self.env.ref('insilos_hse_compliance.view_is_hse_legal_register_form').arch
        self.assertIn('Internal HSE Review', legal_register_template)
        self.assertIn('Print Internal HSE Review', legal_register_template)
        self.assertNotIn('Print HSE Evaluation Report', legal_register_template)
