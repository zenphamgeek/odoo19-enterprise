import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
MODULE = ROOT / "insilos/apps/whatsapp_pos"


class WhatsappPosReceiptParityTest(unittest.TestCase):
    def test_receipt_flow_contract(self):
        js = (MODULE / "static/src/app/screens/receipt_screen/receipt_screen.js").read_text(encoding="utf-8")
        xml = (MODULE / "static/src/app/screens/receipt_screen/receipt_screen.xml").read_text(encoding="utf-8")
        model = ast.parse((MODULE / "models/pos_order.py").read_text(encoding="utf-8"))
        method = next(
            node
            for node in ast.walk(model)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name == "action_sent_receipt_on_whatsapp"
        )
        calls = {
            node.func.attr
            for node in ast.walk(method)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
        }

        self.assertIn("super.showPhoneInput() || this.pos.config.whatsapp_enabled", js)
        self.assertIn('action: "action_sent_receipt_on_whatsapp"', js)
        self.assertIn("destination: this.state.phone", js)
        self.assertIn('name: "WhatsApp"', js)
        self.assertIn('x-if="pos.config.whatsapp_enabled"', xml)
        self.assertIn('x-att-disabled="!isValidPhone"', xml)
        self.assertIn("actionSendReceiptOnWhatsapp()", xml)
        self.assertTrue({"create", "_send_whatsapp_template"} <= calls)
        self.assertIn("self.mobile = phone", ast.unparse(method))


if __name__ == "__main__":
    unittest.main()
