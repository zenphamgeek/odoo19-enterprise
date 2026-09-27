import ast
import json
import subprocess
import unittest
from pathlib import Path


MODULE = Path(__file__).parents[1]
REGISTRY = MODULE.parents[0] / "pos_react/static/src/plugin_registry.js"
TRANSLATION_RUNTIME = MODULE.parents[0] / "pos_react/static/src/translation_runtime.js"
TAX_ENGINE = MODULE.parents[0] / "pos_react/static/src/tax_engine.js"
PLUGIN = MODULE / "static/src/pos_react_plugin.js"


class PosDiscountReactPluginTest(unittest.TestCase):
    def test_localizes_literals_with_standard_runtime_and_fallback(self):
        registry = json.dumps(REGISTRY.read_text(encoding="utf-8"))
        runtime = json.dumps(TRANSLATION_RUNTIME.read_text(encoding="utf-8"))
        plugin = json.dumps(PLUGIN.read_text(encoding="utf-8"))
        script = """
            global.window = global;
            global.document = { getElementById: () => ({ textContent: JSON.stringify({ translations: {
                pos_discount_react: {
                    "Global discount": "Giảm giá toàn đơn",
                    "Discount percentage must be between 0 and 100.": "Phần trăm giảm giá phải từ 0 đến 100.",
                },
            } }) }) };
            eval(%s); eval(%s); eval(%s);
            const action = posReactPlugins.resolve("action")[0].value;
            let error;
            action.run({ pluginData: { role: "cashier", discount: { enabled: true, product: { id: 9 } } }, reportError: value => { error = value; } }, " ").then(() =>
                console.log(JSON.stringify({ label: action.label, error, fallback: posReactTranslate("pos_discount_react", "Apply") }))
            );
        """ % (runtime, registry, plugin)
        result = subprocess.run(["node", "-e", script], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), {
            "label": "Giảm giá toàn đơn",
            "error": "Phần trăm giảm giá phải từ 0 đến 100.",
            "fallback": "Apply",
        })

    def test_manifest_and_tax_detail_discount_allocation(self):
        manifest = ast.literal_eval((MODULE / "__manifest__.py").read_text(encoding="utf-8"))
        self.assertEqual(manifest["depends"], ["pos_react", "pos_discount"])
        self.assertEqual(manifest["pos_react_plugin_scripts"], ["/pos_discount_react/static/src/pos_react_plugin.js"])
        registry = json.dumps(REGISTRY.read_text(encoding="utf-8"))
        plugin = json.dumps(PLUGIN.read_text(encoding="utf-8"))
        tax_engine = json.dumps(str(TAX_ENGINE))
        script = """
            (async () => {
            global.window = global;
            global.crypto = require("crypto").webcrypto;
            window.PosReactTaxEngine = require(%s);
            eval(%s); eval(%s);
            const tax = (id, values = {}) => ({ id, sequence: id, amount_type: "percent", amount: 10, price_include: false, include_base_amount: false, is_base_affected: true, has_negative_factor: false, children_tax_ids: [], ...values });
            const action = posReactPlugins.resolve("action")[0].value;
            let result;
            await action.run({
                cart: [
                    { uuid: "one", productId: 1, price: 1, quantity: 1, taxIds: [4], discount: 0 },
                    { uuid: "two", productId: 2, price: 120, quantity: 1, taxIds: [5], discount: 0 },
                    { uuid: "three", productId: 3, price: 0.05, quantity: 3, taxIds: [1], discount: 0 },
                    { uuid: "discount", productId: 9, price: -1, quantity: 1, taxIds: [4], discount: 0 },
                ],
                lines: [
                    { uuid: "one", productId: 1, price: 100, quantity: 1, taxIds: [2, 1], discount: 0 },
                    { uuid: "two", productId: 2, price: 120, quantity: 1, taxIds: [5], discount: 0 },
                    { uuid: "three", productId: 3, price: 0.05, quantity: 3, taxIds: [1], discount: 0 },
                    { uuid: "tip", productId: 8, price: 20, quantity: 1, taxIds: [], discount: 0 },
                    { uuid: "discount", productId: 9, price: -1, quantity: 1, taxIds: [4], discount: 0 },
                ],
                pluginData: { discount: { enabled: true, percentage: 5, tipProductId: 8, product: { id: 9 } } },
                taxContext: { taxes: [tax(1), tax(2, { amount: 20 }), tax(3, { amount: 20, price_include: true }), tax(4), tax(5, { fiscal_position_ids: [8] })], fiscalPosition: { tax_ids: [5], tax_map: { 5: [3] } }, precision: 0.01, roundingMethod: "round_globally" },
                replaceCart: value => { result = value; return true; },
            }, "10");
            console.log(JSON.stringify(result.map(line => ({ productId: line.productId, price: line.price, taxIds: line.taxIds, extraTaxData: line.extraTaxData }))));
            })();
        """ % (tax_engine, registry, plugin)
        result = subprocess.run(["node", "-e", script], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        lines = json.loads(result.stdout)
        self.assertEqual(lines, [
            {"productId": 1, "price": 1, "taxIds": [4]},
            {"productId": 2, "price": 120, "taxIds": [5]},
            {"productId": 3, "price": 0.05, "taxIds": [1]},
            {"productId": 8, "price": 20, "taxIds": []},
            {"productId": 9, "price": -10, "taxIds": [2, 1], "extraTaxData": {"discount_percentage": 10}},
            {"productId": 9, "price": -12, "taxIds": [5], "extraTaxData": {"discount_percentage": 10}},
            {"productId": 9, "price": -0.015, "taxIds": [1], "extraTaxData": {"discount_percentage": 10}},
        ])
        self.assertEqual([line["productId"] for line in lines[:4]], [1, 2, 3, 8])

    def test_discount_gate_fails_closed_for_missing_config_and_minimal_role(self):
        registry = json.dumps(REGISTRY.read_text(encoding="utf-8"))
        plugin = json.dumps(PLUGIN.read_text(encoding="utf-8"))
        script = """
            global.window = global;
            eval(%s); eval(%s);
            const action = posReactPlugins.resolve("action")[0].value;
            const cart = [{ uuid: "line", productId: 1 }];
            const base = { cart, lines: cart, taxContext: {}, pluginData: {} };
            const missing = action.transformCart(base, 10);
            const minimal = action.transformCart({ ...base, pluginData: { role: "minimal", discount: { enabled: true, product: { id: 9 } } } }, 10);
            console.log(JSON.stringify({
                sameMissing: missing === cart,
                sameMinimal: minimal === cart,
                canMutate: action.canMutateLine(cart[0], { pluginData: { role: "minimal" } }),
                visibleMinimal: action.isVisible({ pluginData: { role: "minimal", discount: { enabled: true, product: { id: 9 } } } }),
                visibleCashier: action.isVisible({ pluginData: { role: "cashier", discount: { enabled: true, product: { id: 9 } } } }),
            }));
        """ % (registry, plugin)
        result = subprocess.run(["node", "-e", script], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), {
            "sameMissing": True,
            "sameMinimal": True,
            "canMutate": True,
            "visibleMinimal": False,
            "visibleCashier": True,
        })

    def test_invalid_percentage_reports_error_without_mutation(self):
        registry = json.dumps(REGISTRY.read_text(encoding="utf-8"))
        plugin = json.dumps(PLUGIN.read_text(encoding="utf-8"))
        script = """
            (async () => {
                global.window = global;
                eval(%s); eval(%s);
                const action = posReactPlugins.resolve("action")[0].value;
                let error = null;
                let mutations = 0;
                const result = await action.run({
                    pluginData: { role: "cashier", discount: { enabled: true, percentage: 10, product: { id: 9 } } },
                    reportError: value => { error = value; },
                    replaceCart: () => { mutations += 1; },
                }, " ");
                console.log(JSON.stringify({ result, error, mutations }));
            })();
        """ % (registry, plugin)
        result = subprocess.run(["node", "-e", script], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), {
            "result": False,
            "error": "Discount percentage must be between 0 and 100.",
            "mutations": 0,
        })

    def test_recomputes_existing_discount_and_prorates_refund(self):
        registry = json.dumps(REGISTRY.read_text(encoding="utf-8"))
        plugin = json.dumps(PLUGIN.read_text(encoding="utf-8"))
        tax_engine = json.dumps(str(TAX_ENGINE))
        script = """
            global.window = global;
            global.crypto = require("crypto").webcrypto;
            window.PosReactTaxEngine = require(%s);
            eval(%s); eval(%s);
            const action = posReactPlugins.resolve("action")[0].value;
            const context = {
                cart: [
                    { uuid: "sale-one", productId: 1, price: 100, quantity: 1, taxIds: [], discount: 0 },
                    { uuid: "discount", productId: 9, price: -10, quantity: 1, taxIds: [], discount: 0, extraTaxData: { discount_percentage: 10 } },
                ],
                pluginData: { discount: { enabled: true, percentage: 5, product: { id: 9 } } },
                taxContext: { taxes: [], precision: 0.01, roundingMethod: "round_per_line" },
            };
            context.lines = context.cart;
            context.cart = [...context.cart.slice(0, 1), { uuid: "sale-two", productId: 2, price: 50, quantity: 1, taxIds: [], discount: 0 }, context.cart[1]];
            context.lines = context.cart;
            const recomputed = action.transformCart(context);
            const refund = action.transformCart({
                ...context,
                cart: [{ uuid: "refund", productId: 1, price: 100, quantity: -0.5, taxIds: [], discount: 0 }],
                lines: [{ uuid: "refund", productId: 1, price: 100, quantity: -0.5, taxIds: [], discount: 0 }],
            }, 10);
            console.log(JSON.stringify({ recomputed, refund }));
        """ % (tax_engine, registry, plugin)
        result = subprocess.run(["node", "-e", script], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        values = json.loads(result.stdout)
        discount = values["recomputed"][-1]
        self.assertEqual(discount["uuid"], "discount")
        self.assertEqual(discount["price"], -15)
        self.assertEqual(discount["extraTaxData"]["discount_percentage"], 10)
        self.assertEqual(values["refund"][0]["quantity"], -0.5)
        self.assertEqual(values["refund"][1]["productId"], 9)
        self.assertEqual(values["refund"][1]["price"], 5)
        self.assertEqual(values["refund"][1]["extraTaxData"]["discount_percentage"], 10)
