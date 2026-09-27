import ast
import unittest
from pathlib import Path
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parents[4]
MODULE = ROOT / "insilos/apps/pos_avatax"


class PosAvataxParityOracleTest(unittest.TestCase):
    """Static oracle for the POS contracts owned by pos_avatax."""

    def test_manifest_loads_all_pos_assets(self):
        data = ast.literal_eval((MODULE / "__manifest__.py").read_text(encoding="utf-8"))

        self.assertIn("point_of_sale", data["depends"])
        self.assertIn("account_avatax", data["depends"])
        self.assertIn("pos_avatax/static/src/**/*", data["assets"]["point_of_sale._assets_pos"])

    def test_server_tax_refresh_contract(self):
        source = (MODULE / "models/pos_order.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        methods = {
            node.name: node
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }

        self.assertIn("get_order_tax_details", methods)
        self.assertIn("sync_from_ui(orders)", source)
        self.assertIn("order.button_external_tax_calculation()", source)
        for model in ("pos.order", "pos.order.line", "account.tax", "account.tax.group"):
            self.assertIn(repr(model), source)

    def test_client_refresh_contract(self):
        store = (MODULE / "static/src/app/services/pos_store.js").read_text(encoding="utf-8")
        payment = (MODULE / "static/src/app/screens/payment_screen/payment_screen.js").read_text(encoding="utf-8")

        self.assertIn("async getAvataxTaxesRpc()", store)
        self.assertIn('this.data.call("pos.order", "get_order_tax_details"', store)
        self.assertIn("this.models.replaceDataByKey", store)
        self.assertIn("this.models.connectNewData", store)
        self.assertIn("await this.getAvataxTaxesRpc();", store)
        self.assertIn("await this.pos.getAvataxTaxesRpc();", payment)

    def test_refresh_ui_contract(self):
        order_display = MODULE / "static/src/app/components/order_display/order_display.xml"
        order_summary = MODULE / "static/src/app/screens/product_screen/order_summary/order_summary.xml"
        for path in (order_display, order_summary):
            ElementTree.parse(path)

        display = order_display.read_text(encoding="utf-8")
        summary = order_summary.read_text(encoding="utf-8")
        self.assertIn('x-if="this.props.isAvataxConfig"', display)
        self.assertIn('t-on-click="() =&gt; this.refreshAvatax()"', display.replace("=>", "=&gt;"))
        self.assertIn('name="refreshAvatax"', summary)
        self.assertIn('name="isAvataxConfig"', summary)


if __name__ == "__main__":
    unittest.main()
