# -*- coding: utf-8 -*-
# Part of Insilos. See LICENSE file for full copyright and licensing details.
"""Cổng bảo mật của `/api/iap/webhook-ai` (Phase 7).

Endpoint này là `auth='public'`, `csrf=False`, và nó ghi `account.move` rồi
tiêu credit của khách hàng. Toàn bộ thứ ngăn người lạ gọi nó là một câu so
sánh chuỗi — nên câu so sánh đó phải được chứng minh **hai chiều**: chặn khi
sai, và cho qua khi đúng. Một test chỉ kiểm "403 khi sai" sẽ xanh y hệt như
vậy trên một endpoint hỏng đến mức 403 với mọi thứ.

`type='jsonrpc'` nên thân đáp ứng là phong bì JSON-RPC: nội dung thật nằm ở
`result`. Đọc thẳng body sẽ so nhầm với phong bì.
"""

from odoo.tests.common import HttpCase, tagged

SECRET = 'wh_secret_for_tests_0123456789'
URL = '/api/iap/webhook-ai'


@tagged('post_install', '-at_install')
class TestAiVisionWebhookAuth(HttpCase):

    def setUp(self):
        super().setUp()
        # Phiên ẩn danh nhưng **gắn vào DB của test**. Không có nó, request
        # không mang db nào và server tự chọn DB đầu danh sách: các test dưới
        # đây đọc `is.config_parameter` họ vừa ghi ở DB này nhưng controller
        # lại tra ở DB khác, và mọi thứ trả 403 "chưa cấu hình" — xanh hay đỏ
        # đều không nói gì về endpoint. Nó cũng là thứ nối request vào con trỏ
        # test, nên `set_param` chưa commit vẫn nhìn thấy được.
        self.authenticate(None, None)

    def _post(self, secret=None, header='X-Insilos-Webhook-Secret', **payload):
        headers = {'Content-Type': 'application/json'}
        if secret is not None:
            headers[header] = secret
        res = self.url_open(
            URL, headers=headers,
            json={'jsonrpc': '2.0', 'method': 'call', 'params': payload or {'record_id': 1}},
        )
        res.raise_for_status()
        return res.json().get('result') or {}

    def _set_secret(self, value):
        self.env['ir.config_parameter'].sudo().set_param('ai_vision.webhook_secret', value)
        self.env.flush_all()

    # --- chiều "chặn" -----------------------------------------------------

    def test_rejects_when_secret_not_configured(self):
        """Chưa cấu hình thì phải từ chối, không phải đoán một mặc định.

        Bản trước có literal làm giá trị mặc định, nghĩa là mọi DB production
        chưa cấu hình đều dùng đúng một secret nằm sẵn trong source code.
        """
        self._set_secret(False)
        self.assertEqual(self._post(secret='anything').get('code'), 403)

    def test_rejects_missing_header(self):
        self._set_secret(SECRET)
        self.assertEqual(self._post().get('code'), 403)

    def test_rejects_wrong_secret(self):
        self._set_secret(SECRET)
        self.assertEqual(self._post(secret='wrong').get('code'), 403)

    def test_rejects_correct_prefix(self):
        """Tiền tố đúng vẫn phải trượt.

        `compare_digest` so toàn bộ chuỗi; một phép so thoát sớm sẽ nhận
        tiền tố dài dần và biến secret thành thứ dò được từng byte.
        """
        self._set_secret(SECRET)
        self.assertEqual(self._post(secret=SECRET[:-1]).get('code'), 403)

    # --- chiều "cho qua" --------------------------------------------------

    def test_accepts_correct_secret(self):
        """Secret đúng phải đi qua được cổng.

        Không có test này thì bốn test ở trên vẫn xanh trên một endpoint
        từ chối tất cả. Bằng chứng "đã qua cổng" là mã lỗi đổi từ 403 sang
        404 — 404 chỉ được sinh ra ở nhánh sau phần kiểm secret.
        """
        self._set_secret(SECRET)
        res = self._post(
            secret=SECRET, record_id=999999999, status='succeeded',
            schema_version='1.0', operation_id='missing', event_id='event-1',
            trigger_run_id='run-1')
        self.assertEqual(res.get('code'), 404, res)

    def test_accepts_legacy_header_name(self):
        """Tên header cũ `X-Insilos-*` vẫn được chấp nhận.

        Worker Trigger.dev đang chạy ngoài kia gửi tên cũ; bỏ nó là làm câm
        webhook production mà không một dòng log nào nói tại sao.
        """
        self._set_secret(SECRET)
        res = self._post(
            secret=SECRET, header='X-Insilos-Webhook-Secret',
            record_id=999999999, status='succeeded', schema_version='1.0',
            operation_id='missing', event_id='event-legacy', trigger_run_id='run-legacy')
        self.assertEqual(res.get('code'), 404, res)

    def test_rejects_missing_record_id(self):
        """Qua cổng nhưng thiếu `record_id` là 400, không phải traceback."""
        self._set_secret(SECRET)
        self.assertEqual(self._post(secret=SECRET, status='success').get('code'), 400)

    def test_rejects_invalid_status(self):
        self._set_secret(SECRET)
        result = self._post(
            secret=SECRET, record_id=999999999, status='pending', schema_version='1.0',
            operation_id='missing', event_id='event-pending', trigger_run_id='run-pending')
        self.assertEqual(result.get('error'), 'Invalid status')

    def test_rejects_mismatched_operation(self):
        self._set_secret(SECRET)
        move = self.env['account.move'].create({'move_type': 'in_invoice'})
        result = self._post(
            secret=SECRET, record_id=move.id, status='succeeded',
            schema_version='1.0', operation_id='ai_vision_account.move_wrong',
            event_id='event-wrong', trigger_run_id='run-wrong')
        self.assertEqual(result.get('error'), 'Operation mismatch')
        self.assertEqual(move.ai_status, 'draft')
