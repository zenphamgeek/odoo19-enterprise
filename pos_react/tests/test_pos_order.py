from unittest.mock import MagicMock, patch
from uuid import uuid4

from odoo.addons.point_of_sale.models.pos_order import PosOrder as CorePosOrder
from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon
from odoo.exceptions import ValidationError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


class TestPosReactOrderSync(TransactionCase):
    def test_rejects_invalid_payload(self):
        order_model = self.env["pos.order"]

        for payload in (None, {}, [None], [], [{"state": "paid"}], [{"uuid": "uuid", "state": "done"}], [{"uuid": "a", "state": "paid"}, {"uuid": "b", "state": "paid"}]):
            with self.assertRaises(ValidationError):
                order_model.pos_react_sync_from_ui(payload)

    def test_rejects_finalized_order_before_delegating(self):
        order_model = self.env["pos.order"]
        finalized = MagicMock(id=42, state="paid")
        finalized.currency_id.rounding = 0.01
        finalized.__getitem__.return_value = 1
        with (
            patch.object(type(order_model), "_pos_react_validate_order_payments"),
            patch.object(type(order_model), "search", return_value=finalized) as search,
            patch.object(type(self.env.cr), "execute") as execute,
            patch.object(CorePosOrder, "sync_from_ui") as sync,
        ):
            with self.assertRaisesRegex(ValidationError, "finalized"):
                order_model.pos_react_sync_from_ui([{"uuid": "uuid", "state": "paid"}])
            search.assert_called_once_with([("uuid", "=", "uuid")], limit=1)
            self.assertTrue(any("FOR UPDATE" in str(call.args[0]) for call in execute.call_args_list))
            sync.assert_not_called()

    def test_cancels_only_matching_draft(self):
        order_model = self.env["pos.order"]
        draft = MagicMock(id=42, state="draft")
        with (
            patch.object(type(order_model), "search", return_value=draft) as search,
            patch.object(type(self.env.cr), "execute") as execute,
        ):
            self.assertTrue(order_model.pos_react_cancel_draft("uuid", 7))
            search.assert_called_once_with([("uuid", "=", "uuid"), ("session_id", "=", 7)], limit=1)
            self.assertTrue(any("FOR UPDATE" in str(call.args[0]) for call in execute.call_args_list))
            draft.action_pos_order_cancel.assert_called_once_with()

    def test_cancel_rejects_invalid_or_finalized_draft(self):
        order_model = self.env["pos.order"]
        for args in ((None, 7), ("uuid", None), ("uuid", 0)):
            with self.assertRaises(ValidationError):
                order_model.pos_react_cancel_draft(*args)

        finalized = MagicMock(id=42, state="paid")
        with patch.object(type(order_model), "search", return_value=finalized):
            with self.assertRaisesRegex(ValidationError, "finalized"):
                order_model.pos_react_cancel_draft("uuid", 7)
            finalized.action_pos_order_cancel.assert_not_called()

    def test_delegates_new_draft_and_paid_orders(self):
        order_model = self.env["pos.order"]
        expected = {"pos.order": []}
        with (
            patch.object(type(order_model), "_pos_react_validate_order_payments"),
            patch.object(type(order_model), "search", return_value=order_model.browse()) as search,
            patch.object(type(self.env.cr), "execute") as execute,
            patch.object(CorePosOrder, "sync_from_ui", return_value=expected) as sync,
        ):
            for state in ("draft", "paid"):
                payload = [{"uuid": f"uuid-{state}", "state": state}]
                self.assertEqual(order_model.pos_react_sync_from_ui(payload), expected)
                sync.assert_called_with(payload)
            self.assertEqual(search.call_count, 2)
            execute.assert_not_called()
            self.assertEqual(sync.call_count, 2)


@tagged("post_install", "-at_install")
class TestPosReactOrderSyncIntegration(TestPointOfSaleHttpCommon):
    @classmethod
    def collect_company_accounting_data(cls, company):
        data = super().collect_company_accounting_data(company)
        if not data["default_journal_bank"]:
            data["default_journal_bank"] = cls.env["account.journal"].create({
                "name": "POS React integration bank",
                "type": "bank",
                "code": "PRB",
                "company_id": company.id,
            })
        return data

    def setUp(self):
        super().setUp()
        self.config = self.main_pos_config
        self.product = self.env["product.product"].create({
            "name": "POS React integration product",
            "list_price": 10.0,
            "available_in_pos": True,
            "taxes_id": False,
            "property_account_income_id": self.env["account.account"].create({
                "name": "POS React integration income",
                "code": "PRI",
                "account_type": "income",
            }).id,
        })
        self.pos_session = self.env["pos.session"].create({
            "name": "POS React integration session",
            "config_id": self.config.id,
            "user_id": self.env.uid,
        })

    def _payload(self, uuid, quantity, state):
        amount = self.product.list_price * quantity
        payments = [] if state == "draft" else [[0, 0, {
            "uuid": str(uuid4()),
            "payment_method_id": self.config.payment_method_ids[0].id,
            "amount": amount,
        }]]
        return {
            "uuid": uuid,
            "access_token": str(uuid),
            "name": "/",
            "pos_reference": uuid,
            "session_id": self.pos_session.id,
            "company_id": self.env.company.id,
            "state": state,
            "amount_paid": 0 if state == "draft" else amount,
            "amount_total": amount,
            "amount_tax": 0,
            "amount_return": 0,
            "lines": [[0, 0, {
                "uuid": f"{uuid}-line",
                "product_id": self.product.id,
                "qty": quantity,
                "price_unit": self.product.list_price,
                "price_subtotal": amount,
                "price_subtotal_incl": amount,
                "discount": 0,
                "tax_ids": [[6, 0, []]],
            }]],
            "payment_ids": payments,
        }

    def test_rejects_invalid_payment_payloads(self):
        valid = self._payload(str(uuid4()), 1, "paid")
        payment = valid["payment_ids"][0][2]
        cases = [
            {"session_id": 2_147_483_647},
            {"company_id": 2_147_483_647},
            {"config_id": 2_147_483_647},
            {"payment_ids": []},
            {"amount_paid": float("nan")},
            {"amount_paid": 9},
            {"payment_ids": [[0, 0, {**payment, "uuid": "invalid"}]]},
            {"payment_ids": [[0, 0, {**payment, "amount": float("inf")}]]},
            {"payment_ids": [[0, 0, {**payment, "payment_method_id": 2_147_483_647}]]},
            {"payment_ids": [valid["payment_ids"][0], valid["payment_ids"][0]]},
            {"state": "draft"},
            {"state": "draft", "payment_ids": [], "amount_paid": 1},
        ]
        for changes in cases:
            payload = {**valid, **changes}
            with self.subTest(changes=changes), self.assertRaises(ValidationError):
                self.env["pos.order"].pos_react_sync_from_ui([payload])

    def test_finalized_replay_returns_existing_graph_only(self):
        payload = self._payload(str(uuid4()), 1, "paid")
        order_model = self.env["pos.order"]
        first = order_model.pos_react_sync_from_ui([payload])
        order = order_model.search([("uuid", "=", payload["uuid"])])
        identity = (order.id, order.lines.ids, order.payment_ids.ids)
        replay = order_model.pos_react_sync_from_ui([payload])
        order.invalidate_recordset()
        self.assertEqual(replay["pos.order"][0]["id"], first["pos.order"][0]["id"])
        self.assertEqual((order.id, order.lines.ids, order.payment_ids.ids), identity)

    def test_finalized_replay_rejects_changed_graph(self):
        payload = self._payload(str(uuid4()), 1, "paid")
        order_model = self.env["pos.order"]
        order_model.pos_react_sync_from_ui([payload])
        for field, value in (("amount", 11), ("uuid", str(uuid4()))):
            changed = {**payload, "payment_ids": [[0, 0, {**payload["payment_ids"][0][2], field: value}]]}
            with self.subTest(field=field), self.assertRaises(ValidationError):
                order_model.pos_react_sync_from_ui([changed])
        self.assertEqual(order_model.search_count([("uuid", "=", payload["uuid"])]), 1)

    def test_accepts_cash_first_then_one_electronic_remaining_slice(self):
        electronic = self.config.payment_method_ids.filtered(
            lambda method: not method.is_cash_count
        )[:1]
        self.assertTrue(electronic)
        payload = self._payload(str(uuid4()), 1, "paid")
        cash_uuid = payload["payment_ids"][0][2]["uuid"]
        payload["payment_ids"][0][2]["amount"] = 4
        payload["payment_ids"].append([0, 0, {
            "uuid": str(uuid4()),
            "payment_method_id": electronic.id,
            "amount": 6,
        }])
        self.env["pos.order"].pos_react_sync_from_ui([payload])
        order = self.env["pos.order"].search([("uuid", "=", payload["uuid"])])
        self.assertEqual(order.payment_ids.mapped("amount"), [4, 6])
        self.assertEqual(str(order.payment_ids[0].uuid), cash_uuid)
        self.assertEqual(order.payment_ids[1].payment_method_id, electronic)

    def test_accepts_cash_rounding_payment_delta(self):
        account = self.env["account.account"].create({
            "name": "POS React payment rounding",
            "code": "PRP",
            "account_type": "expense",
        })
        rounding = self.env["account.cash.rounding"].create({
            "name": "POS React payment 0.01 nearest",
            "rounding": 0.01,
            "rounding_method": "HALF-UP",
            "strategy": "add_invoice_line",
            "profit_account_id": account.id,
            "loss_account_id": account.id,
        })
        self.config.write({"cash_rounding": True, "rounding_method": rounding.id})
        payload = self._payload(str(uuid4()), 1, "paid")
        payload["payment_ids"][0][2]["amount"] = 10.004
        self.env["pos.order"].pos_react_sync_from_ui([payload])
        self.assertEqual(self.env["pos.order"].search([("uuid", "=", payload["uuid"])]).amount_paid, 10)

    def test_refund_locks_and_rejects_quantity_above_remaining(self):
        order_model = self.env["pos.order"]
        sale_uuid = str(uuid4())
        order_model.pos_react_sync_from_ui([self._payload(sale_uuid, 1, "paid")])
        sale_line = order_model.search([("uuid", "=", sale_uuid)]).lines

        refund_uuid = str(uuid4())
        refund = self._payload(refund_uuid, -1, "paid")
        refund["is_refund"] = True
        refund["lines"][0][2]["refunded_orderline_id"] = sale_line.id
        with patch.object(type(self.env.cr), "execute", wraps=self.env.cr.execute) as execute:
            order_model.pos_react_sync_from_ui([refund])
            self.assertTrue(any("pos_order_line" in str(call.args[0]) and "FOR UPDATE" in str(call.args[0]) for call in execute.call_args_list))
        self.assertEqual(sale_line.refunded_qty, 1)

        second_refund = self._payload(str(uuid4()), -1, "paid")
        second_refund["is_refund"] = True
        second_refund["lines"][0][2]["refunded_orderline_id"] = sale_line.id
        with self.assertRaisesRegex(ValidationError, "exceeds"):
            order_model.pos_react_sync_from_ui([second_refund])

    def test_refund_rejects_missing_original_line(self):
        refund = self._payload(str(uuid4()), -1, "paid")
        refund["is_refund"] = True
        refund["lines"][0][2]["refunded_orderline_id"] = 2_147_483_647
        with self.assertRaisesRegex(ValidationError, "no longer exists"):
            self.env["pos.order"].pos_react_sync_from_ui([refund])

    def test_refund_rejects_zero_positive_and_duplicate_source_quantities(self):
        order_model = self.env["pos.order"]
        sale_uuid = str(uuid4())
        order_model.pos_react_sync_from_ui([self._payload(sale_uuid, 2, "paid")])
        sale_line = order_model.search([("uuid", "=", sale_uuid)]).lines

        for quantity in (0, 1):
            refund = self._payload(str(uuid4()), quantity, "paid")
            refund["is_refund"] = True
            refund["lines"][0][2]["refunded_orderline_id"] = sale_line.id
            with self.assertRaisesRegex(ValidationError, "negative quantity"):
                order_model.pos_react_sync_from_ui([refund])

        refund = self._payload(str(uuid4()), -1, "paid")
        refund["is_refund"] = True
        refund["lines"][0][2]["refunded_orderline_id"] = sale_line.id
        refund["lines"].append([0, 0, dict(refund["lines"][0][2], uuid=str(uuid4()))])
        with self.assertRaisesRegex(ValidationError, "negative quantity"):
            order_model.pos_react_sync_from_ui([refund])

    def test_refund_rejects_product_mismatch_and_unfinalized_source(self):
        order_model = self.env["pos.order"]
        draft_uuid = str(uuid4())
        order_model.pos_react_sync_from_ui([self._payload(draft_uuid, 1, "draft")])
        draft = order_model.search([("uuid", "=", draft_uuid)])

        refund = self._payload(str(uuid4()), -1, "paid")
        refund["is_refund"] = True
        refund["lines"][0][2]["refunded_orderline_id"] = draft.lines.id
        with self.assertRaisesRegex(ValidationError, "finalized original"):
            order_model.pos_react_sync_from_ui([refund])

        draft.action_pos_order_cancel()
        refund = self._payload(str(uuid4()), -1, "paid")
        refund["is_refund"] = True
        refund["lines"][0][2]["refunded_orderline_id"] = draft.lines.id
        with self.assertRaisesRegex(ValidationError, "finalized original"):
            order_model.pos_react_sync_from_ui([refund])

        sale_uuid = str(uuid4())
        order_model.pos_react_sync_from_ui([self._payload(sale_uuid, 1, "paid")])
        sale_line = order_model.search([("uuid", "=", sale_uuid)]).lines
        refund = self._payload(str(uuid4()), -1, "paid")
        refund["is_refund"] = True
        refund["lines"][0][2].update({
            "refunded_orderline_id": sale_line.id,
            "product_id": self.env["product.product"].create({"name": "Refund mismatch"}).id,
        })
        with self.assertRaisesRegex(ValidationError, "finalized original"):
            order_model.pos_react_sync_from_ui([refund])

    def test_cancelled_refund_restores_refundable_quantity(self):
        order_model = self.env["pos.order"]
        sale_uuid = str(uuid4())
        order_model.pos_react_sync_from_ui([self._payload(sale_uuid, 1, "paid")])
        sale_line = order_model.search([("uuid", "=", sale_uuid)]).lines

        refund = self._payload(str(uuid4()), -1, "draft")
        refund["is_refund"] = True
        refund["lines"][0][2]["refunded_orderline_id"] = sale_line.id
        order_model.pos_react_sync_from_ui([refund])
        order_model.pos_react_cancel_draft(refund["uuid"], self.pos_session.id)

        replacement = self._payload(str(uuid4()), -1, "paid")
        replacement["is_refund"] = True
        replacement["lines"][0][2]["refunded_orderline_id"] = sale_line.id
        order_model.pos_react_sync_from_ui([replacement])
        self.assertEqual(sale_line.refunded_qty, 1)

    def test_draft_update_and_paid_reuse_one_graph(self):
        uuid = str(uuid4())
        order_model = self.env["pos.order"]

        order_model.pos_react_sync_from_ui([self._payload(uuid, 1, "draft")])
        order = order_model.search([("uuid", "=", uuid)])
        self.assertEqual(len(order), 1)
        self.assertEqual(order.state, "draft")
        self.assertEqual(len(order.lines), 1)
        self.assertEqual(order.lines.qty, 1)
        order_id = order.id
        line_id = order.lines.id

        order_model.pos_react_sync_from_ui([self._payload(uuid, 2, "draft")])
        order.invalidate_recordset()
        self.assertEqual(order.id, order_id)
        self.assertEqual(len(order.lines), 1)
        self.assertEqual(order.lines.id, line_id)
        self.assertEqual(order.lines.qty, 2)

        acknowledgement = order_model.pos_react_sync_from_ui([self._payload(uuid, 2, "paid")])
        order.invalidate_recordset()
        self.assertEqual(order.id, order_id)
        self.assertEqual(order.state, "paid")
        self.assertEqual(len(order.lines), 1)
        self.assertEqual(order.lines.id, line_id)
        self.assertEqual(len(order.payment_ids), 1)
        self.assertEqual(acknowledgement["pos.order"][0]["id"], order_id)
        self.assertEqual(order_model.search_count([("uuid", "=", uuid)]), 1)
