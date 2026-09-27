# -*- coding: utf-8 -*-
# Part of Insilos. See LICENSE file for full copyright and licensing details.
{
    'name': 'Vietnam - Manufacturing & Industrial Transport Demo Data (Sản Xuất & Vận Tải Công Nghiệp)',
    'version': '20.0.2.0.0',
    'category': 'Localization/Vietnam',
    'summary': 'Dữ liệu demo chuyên sâu ngành Sản Xuất Chế Tạo Cơ Khí & Vận Tải Tiếp Vận Đa Phương Thức tại Việt Nam',
    'description': """
Bộ dữ liệu Demo Chuẩn Mực Doanh Nghiệp (Enterprise Demo Data Suite) cho Odoo 20:
================================================================================
Cung cấp toàn diện hệ sinh thái vận hành thực tế cho các Tập đoàn Công nghiệp và Vận tải tại Việt Nam:

1. Cơ cấu Tổ chức & Nhân sự:
   - Sơ đồ Khối Kỹ thuật & Chế tạo R&D, Khối Vận tải & Logistics, Khối Quản lý chất lượng QA/QC.
   - Đội trưởng đội xe container, kỹ sư trưởng xưởng cơ khí, tài xế chuyên nghiệp bằng FC/C.

2. Danh mục Đối tác B2B Đầu ngành:
   - Khách hàng: VinFast Cát Hải, Samsung Electronics Thái Nguyên, THACO Chu Lai, Tân Cảng Sài Gòn, Gemadept Logistics, ITL Corp.
   - Nhà cung cấp công nghiệp: Tập đoàn Thép Hòa Phát, Dây cáp điện CADIVI, Schneider Electric, Xăng dầu Petrolimex/PVOIL, Sơn Jotun, Lốp Bridgestone.

3. Sản xuất & Chế tạo Cơ khí (MRP):
   - 6 Trung tâm làm việc hiện đại: Phân xưởng Cắt Fiber Laser 12kW CNC, Chấn dập CNC 250T, Robot hàn Yaskawa, Dây chuyền sơn tĩnh điện tự động, Xưởng lắp ráp, Trạm thử tải PDI.
   - Định mức vật tư đa cấp (Multi-level BOMs) chi tiết cho Xe kéo điện nhà xưởng V-LIFT 2500E và Sơ mi rơ moóc 40ft container chassis VT-SEMITRAIL 40 kèm công đoạn Routing chuẩn xác.

4. Quản lý Đội xe Vận tải & Logistics (Fleet & Transport):
   - Đội xe đầu kéo container Hyundai Xcient GT 440PS, Sơ mi rơ moóc CIMC 40ft 3 trục, Xe tải nặng 15T Hino 500, Xe tải đông lạnh Isuzu Forward FVR 8T (-20°C).
   - Nhật ký Odometer, Định mức nhiên liệu Dầu DO 0.05S, Nhật ký bảo dưỡng định kỳ và kiểm định đăng kiểm.

5. Bán hàng, Mua hàng, CRM & Kế toán Việt Nam:
   - CRM Pipeline dự án thầu quy mô hàng chục tỷ đồng.
   - Đơn bán hàng và Mua hàng với đơn giá tiền đồng (VND) thực tế, hạch toán đồng bộ theo Thông tư 200/2014/TT-BTC.
    """,
    'author': 'Insilos',
    'depends': [
        'l10n_vn',
        'sale_management',
        'crm',
        'purchase',
        'mrp',
        'mrp_workorder',
        'stock',
        'fleet',
        'delivery',
        'hr',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
    'data': [
        'demo/res_partner_demo.xml',
        'demo/hr_employee_demo.xml',
        'demo/product_category_demo.xml',
        'demo/product_demo.xml',
        'demo/mrp_workcenter_demo.xml',
        'demo/mrp_bom_demo.xml',
        'demo/stock_quant_demo.xml',
        'demo/mrp_production_demo.xml',
        'demo/fleet_demo.xml',
        'demo/crm_demo.xml',
        'demo/account_move_demo.xml',
        'demo/sale_demo.xml',
        'demo/purchase_demo.xml',
    ],
    'assets': {
        'web.assets_unit_tests': [
            'l10n_vn_demo/static/tests/mock_server/**/*',
        ],
    },
}
