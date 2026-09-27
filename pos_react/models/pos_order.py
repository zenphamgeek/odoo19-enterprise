import math
from uuid import UUID

from odoo import _, api, models
from odoo.exceptions import ValidationError
from odoo.fields import Domain
from odoo.tools import float_compare


class PosOrder(models.Model):
    _inherit = "pos.order"

    def _pos_react_validate_order_payments(self, order):
        session_id = order.get("session_id")
        session = self.env["pos.session"].browse(session_id).exists() if isinstance(session_id, int) and session_id > 0 else self.env["pos.session"]
        if not session:
            raise ValidationError(_("The POS session is invalid."))
        session.check_access("read")
        session.check_access_rule("read")
        session.config_id.check_access("read")
        session.config_id.check_access_rule("read")
        company_id = order.get("company_id")
        if not isinstance(company_id, int) or company_id != session.company_id.id:
            raise ValidationError(_("The POS company does not match the session."))
        config_id = order.get("config_id")
        if config_id and config_id != session.config_id.id:
            raise ValidationError(_("The POS configuration does not match the session."))

        payments = []
        payment_uuids = set()
        for command in order.get("payment_ids", []):
            values = command[2] if isinstance(command, (list, tuple)) and len(command) > 2 and command[0] in (0, 1) and isinstance(command[2], dict) else None
            if values is None:
                raise ValidationError(_("A POS payment is invalid."))
            payment_uuid = values.get("uuid")
            try:
                payment_uuid = UUID(payment_uuid)
            except (AttributeError, TypeError, ValueError):
                raise ValidationError(_("A POS payment requires a valid UUID."))
            if payment_uuid in payment_uuids:
                raise ValidationError(_("POS payment UUIDs must be unique."))
            payment_uuids.add(payment_uuid)
            amount = values.get("amount")
            if isinstance(amount, bool) or not isinstance(amount, (int, float)) or not math.isfinite(amount):
                raise ValidationError(_("A POS payment amount must be finite."))
            method_id = values.get("payment_method_id")
            method_id = method_id[0] if isinstance(method_id, (list, tuple)) and method_id else method_id
            if method_id not in session.config_id.payment_method_ids.ids:
                raise ValidationError(_("The POS payment method is not configured for this session."))
            payments.append(amount)

        amount_paid = order.get("amount_paid")
        if isinstance(amount_paid, bool) or not isinstance(amount_paid, (int, float)) or not math.isfinite(amount_paid):
            raise ValidationError(_("The POS paid amount must be finite."))
        if order["state"] == "draft" and (payments or amount_paid):
            raise ValidationError(_("A draft POS order cannot have payments."))
        if order["state"] == "paid" and not payments:
            raise ValidationError(_("A paid POS order requires a payment."))
        if float_compare(sum(payments), amount_paid, precision_rounding=session.currency_id.rounding):
            raise ValidationError(_("The POS payment total must equal the paid amount."))
        return session

    def _pos_react_validate_employee(self, payload, session, existing):
        has_pos_hr = "module_pos_hr" in session.config_id._fields and session.config_id.module_pos_hr
        employee_id = payload.get("employee_id")
        if not has_pos_hr:
            if employee_id:
                raise ValidationError(_("Employee ownership requires POS Employees."))
            return
        if not isinstance(employee_id, int) or isinstance(employee_id, bool) or employee_id <= 0:
            raise ValidationError(_("A POS employee is required."))
        employee = self.env["hr.employee"].search(
            session.config_id._employee_domain(self.env.uid) & Domain("id", "=", employee_id),
            limit=1,
        )
        if not employee or employee.company_id != session.company_id:
            raise ValidationError(_("The POS employee is not allowed for this session."))
        if existing and existing.employee_id and existing.employee_id != employee:
            raise ValidationError(_("The POS order employee cannot be changed."))

    def _pos_react_is_finalized_replay(self, order, payload):
        if payload.get("state") != "paid" or order.state not in {"paid", "done"}:
            return False

        rounding = order.currency_id.rounding
        scalar_fields = ("amount_total", "amount_paid", "amount_return")
        if any(float_compare(payload.get(field, 0), order[field], precision_rounding=rounding) for field in scalar_fields):
            return False
        for field in ("session_id", "company_id", "employee_id", "partner_id", "pricelist_id", "fiscal_position_id"):
            if field not in payload:
                continue
            value = payload.get(field, False)
            value = value[0] if isinstance(value, (list, tuple)) and value else value
            if (value or False) != (order[field].id or False):
                return False

        def command_values(commands):
            values = {}
            for command in commands:
                value = command[2] if isinstance(command, (list, tuple)) and len(command) > 2 and isinstance(command[2], dict) else None
                if not value or not value.get("uuid") or value["uuid"] in values:
                    return False
                values[value["uuid"]] = value
            return values

        lines = command_values(payload.get("lines", []))
        payments = command_values(payload.get("payment_ids", []))
        if lines is False or payments is False or set(lines) != {str(uuid) for uuid in order.lines.mapped("uuid")} or set(payments) != {str(uuid) for uuid in order.payment_ids.mapped("uuid")}:
            return False
        for line in order.lines:
            value = lines[str(line.uuid)]
            product_id = value.get("product_id")
            product_id = product_id[0] if isinstance(product_id, (list, tuple)) and product_id else product_id
            source_id = value.get("refunded_orderline_id", False)
            source_id = source_id[0] if isinstance(source_id, (list, tuple)) and source_id else source_id
            tax_ids = value.get("tax_ids", [])
            tax_ids = tax_ids[0][2] if len(tax_ids) == 1 and isinstance(tax_ids[0], (list, tuple)) and len(tax_ids[0]) > 2 and tax_ids[0][0] == 6 else tax_ids
            if product_id != line.product_id.id or source_id != (line.refunded_orderline_id.id or False) or set(tax_ids) != set(line.tax_ids.ids):
                return False
            if any(float_compare(value.get(field, 0), line[field], precision_rounding=rounding) for field in ("qty", "price_unit", "discount")):
                return False
        for payment in order.payment_ids:
            value = payments[str(payment.uuid)]
            method_id = value.get("payment_method_id")
            method_id = method_id[0] if isinstance(method_id, (list, tuple)) and method_id else method_id
            if method_id != payment.payment_method_id.id or value.get("transaction_id", False) != (payment.transaction_id or False):
                return False
            if float_compare(value.get("amount", 0), payment.amount, precision_rounding=rounding):
                return False
        return True

    @api.model
    def pos_react_sync_from_ui(self, orders):
        if not isinstance(orders, list) or len(orders) != 1 or not isinstance(orders[0], dict) or not orders[0].get("uuid") or orders[0].get("state") not in {"draft", "paid"}:
            raise ValidationError(_("POS React accepts one draft or paid order with a UUID per synchronization."))

        session = self._pos_react_validate_order_payments(orders[0])
        existing = self.search([("uuid", "=", orders[0]["uuid"])], limit=1)
        if existing:
            self.env.cr.execute("SELECT id FROM pos_order WHERE id = %s FOR UPDATE", [existing.id])
            existing.invalidate_recordset(["state", "employee_id"])
        self._pos_react_validate_employee(orders[0], session, existing)
        if existing:
            if existing.state != "draft":
                if self._pos_react_is_finalized_replay(existing, orders[0]):
                    return existing.read_pos_data(orders, existing.config_id)
                raise ValidationError(_("A finalized POS order cannot be modified."))

        refund_lines = {}
        for command in orders[0].get("lines", []):
            values = command[2] if isinstance(command, (list, tuple)) and len(command) > 2 and command[0] in (0, 1) and isinstance(command[2], dict) else {}
            line_id = values.get("refunded_orderline_id")
            if not line_id:
                continue
            if not isinstance(line_id, int) or line_id <= 0 or line_id in refund_lines or values.get("qty", 0) >= 0:
                raise ValidationError(_("A refund requires one negative quantity per original order line."))
            refund_lines[line_id] = values
        if refund_lines:
            self.env["pos.order"].flush_model(["state"])
            self.env.cr.execute("SELECT id FROM pos_order_line WHERE id IN %s ORDER BY id FOR UPDATE", [tuple(refund_lines)])
            original_lines = self.env["pos.order.line"].browse(refund_lines).exists()
            if len(original_lines) != len(refund_lines):
                raise ValidationError(_("The refunded order line no longer exists."))
            for line in original_lines:
                values = refund_lines[line.id]
                product_id = values.get("product_id")
                product_id = product_id[0] if isinstance(product_id, (list, tuple)) else product_id
                if line.order_id.state in {"draft", "cancel"} or product_id != line.product_id.id or line.order_id.company_id.id != orders[0].get("company_id"):
                    raise ValidationError(_("The refund does not match a finalized original order line."))
                existing_id = existing.id or None
                self.env.cr.execute(
                    """SELECT COALESCE(-SUM(refund.qty), 0)
                         FROM pos_order_line refund
                         JOIN pos_order refund_order ON refund_order.id = refund.order_id
                        WHERE refund.refunded_orderline_id = %s
                          AND refund_order.state != 'cancel'
                          AND (%s IS NULL OR refund_order.id != %s)""",
                    [line.id, existing_id, existing_id],
                )
                other_refunded_qty = self.env.cr.fetchone()[0]
                if -values["qty"] > line.qty - other_refunded_qty:
                    raise ValidationError(_("The refund quantity exceeds the refundable quantity."))

        return super().sync_from_ui(orders)

    @api.model
    def pos_react_cancel_draft(self, uuid, session_id):
        if not isinstance(uuid, str) or not uuid or not isinstance(session_id, int) or session_id <= 0:
            raise ValidationError(_("POS React draft cancellation requires a UUID and session."))

        order = self.search([("uuid", "=", uuid), ("session_id", "=", session_id)], limit=1)
        if not order:
            return False

        self.env.cr.execute("SELECT id FROM pos_order WHERE id = %s FOR UPDATE", [order.id])
        order.invalidate_recordset(["state"])
        if order.state != "draft":
            raise ValidationError(_("A finalized POS order cannot be cancelled."))

        order.action_pos_order_cancel()
        return True
