import json
import re
from pathlib import Path

from markupsafe import Markup

from odoo import http
from odoo.fields import Domain
from odoo.http import request
from odoo.tools.translate import code_translations
from odoo.modules.module import get_manifest


_PLUGIN_SCRIPT_PATH = re.compile(r"^(?!.*(?:^|/)\.\.(?:/|$))/[A-Za-z0-9_.-]+/static/[A-Za-z0-9_./-]+\.js$")


def _pos_role(user, config):
    group_ids = user.all_group_ids.ids
    if not config.group_pos_user_id or config.group_pos_user_id.id not in group_ids:
        return False
    return "manager" if config.group_pos_manager_id and config.group_pos_manager_id.id in group_ids else "cashier"


def _employee_role(employee, config):
    if config.group_pos_manager_id and config.group_pos_manager_id.id in employee.user_id.all_group_ids.ids:
        return "manager"
    if employee.id in config.advanced_employee_ids.ids:
        return "manager"
    if employee.id in config.minimal_employee_ids.ids:
        return "minimal"
    return "cashier"


class PosReactController(http.Controller):
    @http.route("/pos/react/service-worker.js", type="http", auth="user", methods=["GET"], readonly=True)
    def service_worker(self):
        with open(Path(__file__).parents[1] / "static/src/service_worker.js", encoding="utf-8") as service_worker:
            return request.make_response(service_worker.read(), [
                ("Content-Type", "text/javascript"),
                ("Cache-Control", "no-cache"),
                ("Service-Worker-Allowed", "/pos/react/"),
            ])

    def _plugin_assets(self):
        scripts = []
        translation_sources = {}
        modules = request.env["ir.module.module"].sudo().search(
            [("state", "=", "installed")], order="name"
        )
        for module in modules:
            if module.name == "pos_restaurant":
                continue
            manifest = get_manifest(module.name)
            for path in manifest.get("pos_react_plugin_scripts", []):
                if isinstance(path, str) and _PLUGIN_SCRIPT_PATH.fullmatch(path) and path not in scripts:
                    scripts.append(path)
            sources = manifest.get("pos_react_translations", [])
            if sources:
                translation_sources[module.name] = {
                    source for source in sources if isinstance(source, str)
                }
        lang = request.env.lang
        translations = {}
        for module, sources in translation_sources.items():
            catalog = code_translations.get_web_translations(module, lang)
            translated = {item["id"]: item["string"] for item in catalog["messages"]}
            translations[module] = {
                source: translated.get(source, source) for source in sources
            }
        return scripts, translations

    def _employee_bootstrap(self, config):
        if "module_pos_hr" not in config._fields or not config.module_pos_hr:
            return None
        employee = request.env["hr.employee"].sudo().search(
            config._employee_domain(request.session.uid) & Domain("user_id", "=", request.session.uid),
            limit=1,
        )
        if not employee:
            return False
        return {
            "id": employee.id,
            "name": employee.name,
            "role": _employee_role(employee, config),
            "hasPin": bool(employee.pin),
        }

    def _bootstrap_session(self, config_id):
        if not request.env.user._is_internal():
            return request.env["pos.session"]

        config = request.env["pos.config"].sudo().browse(config_id).exists()
        if (
            not config
            or not config.active
            or not _pos_role(request.env.user, config)
            or self._employee_bootstrap(config) is False
        ):
            return request.env["pos.session"]

        domain = Domain([
            ("state", "in", ["opening_control", "opened"]),
            ("rescue", "=", False),
            ("config_id", "=", config.id),
        ])
        session = request.env["pos.session"].sudo().search(
            domain & Domain("user_id", "=", request.session.uid), limit=1
        ) or request.env["pos.session"].sudo().search(domain, limit=1)
        if config.has_active_session and not session:
            return request.env["pos.session"]
        if not session:
            request.env.cr.execute("SELECT id FROM pos_config WHERE id = %s FOR UPDATE NOWAIT", (config.id,))
            config.open_ui()
            session = request.env["pos.session"].sudo().search(domain, limit=1)
        return session

    @http.route("/pos/react/<int:config_id>", type="http", auth="user")
    def pos_react(self, config_id):
        session = self._bootstrap_session(config_id)
        if not session:
            return request.not_found()

        data = session.with_company(session.company_id).load_data([
            "pos.category", "product.template", "product.product",
        ])
        templates = {record["id"]: record for record in data["product.template"]}
        products = []
        for product in data["product.product"]:
            template_id = product["product_tmpl_id"]
            template_id = template_id[0] if isinstance(template_id, (list, tuple)) else template_id
            template = templates[template_id]
            products.append({
                "id": product["id"],
                "name": product["display_name"],
                "price": product["lst_price"],
                "categoryIds": template["pos_categ_ids"],
                "taxIds": product.get("taxes_id", template.get("taxes_id", [])),
            })
        currencies = data.get("res.currency", [])
        currency_id = session.config_id.currency_id.id
        currency = next((item for item in currencies if item["id"] == currency_id), {})
        cash_method = session.config_id.payment_method_ids.filtered("is_cash_count")[:1]
        electronic_methods = session.config_id.payment_method_ids.filtered(
            lambda method: not method.is_cash_count and method.type != "pay_later"
        )
        restaurant = {"enabled": False, "tables": []}
        if "module_pos_restaurant" in session.config_id._fields and session.config_id.module_pos_restaurant:
            restaurant["enabled"] = True
            restaurant["tables"] = request.env["restaurant.table"]._load_pos_data_read(
                request.env["restaurant.table"].search([
                    ("active", "=", True), ("floor_id", "in", session.config_id.floor_ids.ids),
                ]), session.config_id,
            )
        has_discount = "module_pos_discount" in session.config_id._fields and session.config_id.module_pos_discount
        discount_product = session.config_id.discount_product_id if has_discount else False
        employee = self._employee_bootstrap(session.config_id)
        role = employee["role"] if employee else _pos_role(request.env.user, session.config_id)
        employees = []
        if employee:
            employee_records = request.env["hr.employee"].sudo().search(
                session.config_id._employee_domain(request.session.uid)
            )
            employees = [{
                "id": item.id,
                "name": item.name,
                "role": _employee_role(item, session.config_id),
                "hasPin": bool(item.pin),
            } for item in employee_records]
        tip_product = session.config_id.tip_product_id if "tip_product_id" in session.config_id._fields else False
        plugin_scripts, translations = self._plugin_assets()
        initial_data = {
            "translations": translations,
            "tenantId": request.env.cr.dbname,
            "userId": request.session.uid,
            "sessionId": session.id,
            "configId": session.config_id.id,
            "accessToken": session.config_id.access_token,
            "websocketWorkerVersion": request.env["is.http"].session_info()["websocket_worker_version"],
            "companyId": session.company_id.id,
            "role": role,
            "employee": employee,
            "employees": employees,
            "cashMethodId": cash_method.id,
            "electronicPaymentMethods": [{
                "id": method.id,
                "name": method.name,
                "terminal": method.use_payment_terminal or False,
            } for method in electronic_methods],
            "cashRounding": {
                "enabled": session.config_id.cash_rounding,
                "onlyCash": session.config_id.only_round_cash_method,
                "precision": session.config_id.rounding_method.rounding,
                "method": session.config_id.rounding_method.rounding_method,
            } if session.config_id.cash_rounding else {"enabled": False},
            "lastDataChange": session.config_id.last_data_change.strftime("%Y-%m-%d %H:%M:%S"),
            "restaurant": restaurant,
            "discount": {
                "enabled": bool(has_discount and discount_product),
                "percentage": session.config_id.discount_pc if has_discount else 0,
                "tipProductId": tip_product.id if tip_product else False,
                "product": {
                    "id": discount_product.id,
                    "name": discount_product.display_name,
                } if discount_product else False,
            },
            "products": products,
            "categories": [{"id": category["id"], "name": category["name"]} for category in data["pos.category"]],
            "allowProductCreation": request.env["product.template"].has_access("create"),
            "currency": {
                "symbol": currency.get("symbol", session.config_id.currency_id.symbol),
                "position": currency.get("position", session.config_id.currency_id.position),
                "decimalPlaces": session.config_id.currency_id.decimal_places,
                "rounding": session.config_id.currency_id.rounding,
            },
        }
        return request.render("pos_react.shell", {
            "config": session.config_id,
            "initial_data": Markup(json.dumps(initial_data).replace("<", "\\u003c")),
            "plugin_scripts": plugin_scripts,
        })
