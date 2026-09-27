import math

from odoo import _, api, models
from odoo.exceptions import AccessError, ValidationError


class PosSession(models.Model):
    _inherit = "pos.session"

    def _pos_react_employee_session(self, session_id):
        session = self.browse(session_id).exists()
        if not session or session.state not in ("opening_control", "opened"):
            raise AccessError("Invalid POS session")
        if not session.config_id.module_pos_hr or not self.env.user.has_group("point_of_sale.group_pos_user"):
            raise AccessError("Employee login is not available")
        return session

    def _pos_react_employee_data(self, employee, config):
        return {
            "id": employee.id,
            "name": employee.name,
            "role": "manager" if (
                config.group_pos_manager_id.id in employee.user_id.all_group_ids.ids
                or employee in config.advanced_employee_ids
            ) else "minimal" if employee in config.minimal_employee_ids else "cashier",
            "hasPin": bool(employee.pin),
        }

    @api.model
    def pos_react_try_cash_in_out(self, session_id, _type, amount, reason=""):
        session = self._pos_react_employee_session(session_id)
        if _type not in ("in", "out"):
            raise ValidationError(_("Invalid cash move type"))
        if isinstance(amount, bool) or not isinstance(amount, (int, float)) or not math.isfinite(amount) or amount <= 0:
            raise ValidationError(_("Cash move amount must be a positive finite number"))
        if not isinstance(reason, str) or not reason.strip() or len(reason) > 500:
            raise ValidationError(_("Invalid cash move reason"))

        employee = self.env["hr.employee"].sudo().search(
            session.config_id._employee_domain(self.env.uid)
        ).filtered(
            lambda item: item == session.employee_id or (
                not session.employee_id and item.user_id == self.env.user
            )
        ).filtered(lambda item: item.company_id == session.company_id)[:1]
        if not employee:
            raise AccessError(_("No active employee for this POS session"))
        partner = employee._get_related_partners()[:1] or session.user_id.partner_id
        extras = {
            "employee_id": employee.id,
            "formattedAmount": session.currency_id.format(amount),
            "translatedType": _("in") if _type == "in" else _("out"),
        }
        session.try_cash_in_out(_type, amount, reason.strip(), partner.id, extras)
        return True

    @api.model
    def pos_react_restore_employee(self, session_id, employee_id):
        session = self._pos_react_employee_session(session_id)
        employee = self.env["hr.employee"].search(session.config_id._employee_domain(self.env.uid)).filtered(
            lambda item: item.id == employee_id and item == session.employee_id
        )[:1].sudo()
        return self._pos_react_employee_data(employee, session.config_id) if employee else False

    @api.model
    def pos_react_select_employee(self, session_id, employee_id=False, credential="", credential_type="pin"):
        session = self._pos_react_employee_session(session_id)
        config = session.config_id
        visible_employees = self.env["hr.employee"].search(config._employee_domain(self.env.uid))
        employees = visible_employees.sudo()
        if credential_type == "barcode":
            employee = employees.filtered(lambda item: item.barcode == credential)[:1]
        elif credential_type == "pin":
            employee = employees.filtered(lambda item: item.id == employee_id)[:1]
            if not employee or employee.pin and employee.pin != credential:
                employee = self.env["hr.employee"]
        else:
            employee = self.env["hr.employee"]
        if not employee:
            raise AccessError("Invalid employee credential")

        session.employee_id = employee
        return self._pos_react_employee_data(employee, config)
