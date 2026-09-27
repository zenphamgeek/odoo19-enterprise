# -*- coding: utf-8 -*-
# Part of Insilos. See LICENSE file for full copyright and licensing details.
"""`_hold_iap()` giữ đúng số credit mà DỮ LIỆU quy định (plan 6.3).

Test nằm ở `ai_vision_iap` chứ không ở `iap`, dù thứ nó kiểm là giá IAP: bộ
test của `iap` chạy lúc `iap` vừa nạp xong, khi đó `ai_vision_iap` **chưa** vào
registry. Cột `account_move.ai_status` là NOT NULL trong DB nhưng trường tương
ứng chưa tồn tại trong registry ở thời điểm đó, nên `create()` sinh câu INSERT
bỏ hẳn cột và Postgres từ chối. Test phải sống trong module sở hữu trường mà nó
chạm tới.
"""

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase


class TestAiVisionHoldUsesServicePrice(TransactionCase):

    def setUp(self):
        super().setUp()
        self.service = self.env['iap.service'].search(
            [('technical_name', '=', 'ai_vision')], limit=1)
        self.assertTrue(
            self.service,
            "thiếu bản ghi `ai_vision` — `data/iap_service_data.xml` không nạp")
        self.move = self.env['account.move'].create({'move_type': 'in_invoice'})
        self.wallet = self.env['iap.wallet'].get_wallet(self.move.company_id)
        # Không giả định ví bắt đầu từ 0 (R45): nạp thêm rồi đo trên số dư thật.
        self.env['iap.ledger'].create_entry(
            self.wallet, 'topup', 50.0, 'ai_vision_pricing_test_topup',
            reference='test')
        self.wallet.invalidate_recordset()

    def test_hold_amount_follows_service_credit_cost(self):
        """Đổi giá trong dữ liệu thì số credit giữ đổi theo.

        Chiều này là chiều duy nhất chứng minh `_hold_iap()` thật sự đọc dữ
        liệu: một hàm còn hardcode 1 vẫn xanh nếu giá dữ liệu tình cờ bằng 1.
        """
        self.service.credit_cost = 5.0
        charge = self.move._hold_iap()
        self.assertEqual(charge.amount, 5.0)

    def test_explicit_amount_still_wins(self):
        """Người gọi truyền số cụ thể thì số đó thắng dữ liệu."""
        self.service.credit_cost = 5.0
        charge = self.move._hold_iap(amount=2.0)
        self.assertEqual(charge.amount, 2.0)

    def test_hold_fails_when_price_exceeds_balance(self):
        """Giá cao hơn số dư thì dừng có lời, không giữ âm."""
        self.service.credit_cost = self.wallet.available_balance + 1000.0
        with self.assertRaises(UserError):
            self.move._hold_iap()
