# Part of Insilos. See LICENSE file for full copyright and licensing details.
"""E02 gate G2 — lớp agent không sở hữu bảng, và exception baseline bị khoá.

Hai bất biến, hai vòng đời:

1. `insilos_finance_agent_os` không được khai model nào — kể cả transient.
   Static gate `tools/check_combo_zero_schema.py` quét source; test này quét
   registry sau install, nên kể cả model tạo bằng đường vòng cũng lộ.
2. Baseline `insilos_capital_markets_decision_governance` có 13 model persistent
   ra đời trước build spec. Đó là exception được chấp nhận — nhưng chấp nhận
   **đúng 13 cái này**. Danh sách khoá cứng ở đây: thêm model thứ 14 là quyết
   định kiến trúc phải sửa test + exception doc, không phải thao tác.
"""

from odoo.tests.common import TransactionCase, tagged

MODULE = 'insilos_finance_agent_os'
BASELINE_MODULE = 'insilos_capital_markets_decision_governance'

# Ghi ở docs/industries/Insilos_Combo_Upgrade_Implementation_Package_v1.0/zero_schema_exception.md
BASELINE_MODELS = [
    'capital.alert.rule',
    'capital.benchmark',
    'capital.corporate.action',
    'capital.data.quarantine',
    'capital.fx.rate',
    'capital.instrument',
    'capital.market.data',
    'capital.order',
    'capital.order.fill',
    'capital.portfolio',
    'capital.position',
    'capital.reconciliation.import',
    'capital.reconciliation.line',
]


@tagged('post_install', '-at_install', 'finance_agent_os')
class TestComboZeroSchema(TransactionCase):
    def _owned_models(self, module):
        """Model mà một mình module này định nghĩa (không tính _inherit)."""
        owned = self.env['ir.model.data'].search([('module', '=', module), ('model', '=', 'ir.model')])
        result = []
        for data in owned:
            shared = self.env['ir.model.data'].search_count([
                ('model', '=', 'ir.model'), ('res_id', '=', data.res_id), ('module', '!=', module)])
            if shared:
                continue
            result.append(self.env['ir.model'].browse(data.res_id).model)
        return sorted(result)

    def test_agent_layer_owns_no_model_at_all(self):
        module = self.env['ir.module.module'].search([('name', '=', MODULE)], limit=1)
        self.assertEqual(module.state, 'installed')
        self.assertEqual(self._owned_models(MODULE), [],
                         'Lớp agent phải zero-schema: mọi state nằm trên model có sẵn')

    def test_agent_layer_owns_no_table(self):
        self.env.cr.execute(
            "SELECT tablename FROM pg_tables WHERE schemaname = 'public' "
            "AND (tablename LIKE 'finance_agent%%' OR tablename LIKE 'fao_%%')")
        self.assertEqual(self.env.cr.fetchall(), [])

    def test_baseline_exception_list_is_locked(self):
        """13 model có trước spec — được phép tồn tại, không được phép lớn thêm.

        Test fail theo cả hai chiều: thêm model mới (danh sách phình) và gỡ
        model (exception doc thành nói dối) đều phải sửa chỗ này một cách
        có chủ đích.
        """
        self.assertEqual(self._owned_models(BASELINE_MODULE), BASELINE_MODELS)
