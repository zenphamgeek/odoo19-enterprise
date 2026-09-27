import ast
import hashlib
import json
import subprocess
import unittest
from pathlib import Path

MODULE = Path(__file__).parents[1]
REGISTRY = MODULE / "static/src/plugin_registry.js"
STRIPE_ADAPTER = MODULE / "static/src/stripe_adapter.js"
ROOT = MODULE.parents[1] / "addons"
PLUGIN_CONTRACTS = {
    "pos_sale": {
        "action": "pos_sale.summary",
        "receiptFragment": "pos_sale.summary",
    },
    "pos_stripe": {"paymentAdapter": "stripe"},
}


def run_registry(script, sources=()):
    source = json.dumps(REGISTRY.read_text(encoding="utf-8"))
    plugins = ";".join(f"eval({json.dumps(path.read_text(encoding='utf-8'))})" for path in sources)
    result = subprocess.run(
        ["node", "-e", f"global.window = global; global.document = {{ getElementById() {{ return {{ textContent: '{{\"restaurant\":{{\"enabled\":true}}}}' }}; }} }}; global.React = {{ createElement(type, props, ...children) {{ return {{ type, props, children }}; }} }}; eval({source}); {plugins}; (async () => {{ {script} }})().catch(error => {{ console.error(error); process.exit(1); }});"],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)


class PluginRegistryTest(unittest.TestCase):
    def test_seven_points_and_deterministic_priority(self):
        result = run_registry("""
            for (const point of posReactPlugins.points) {
                posReactPlugins.register(point, "z", {}, { priority: 10 });
                posReactPlugins.register(point, "a", {}, { priority: 10 });
                posReactPlugins.register(point, "low", {}, { priority: -1 });
            }
            console.log(JSON.stringify(Object.fromEntries(posReactPlugins.points.map(
                point => [point, posReactPlugins.resolve(point).map(item => item.id)]
            ))));
        """)
        self.assertEqual(set(result), {
            "screen", "slot", "action", "dataRequirement", "paymentAdapter", "receiptFragment",
        })
        self.assertTrue(all(order == ["a", "z", "low"] for order in result.values()))

    def test_anchors_override_priority_and_fail_closed(self):
        result = run_registry("""
            posReactPlugins.register("slot", "middle", {}, { priority: -100 });
            posReactPlugins.register("slot", "first", {}, { after: "middle", priority: 100 });
            posReactPlugins.register("slot", "last", {}, { after: "first" });
            const order = posReactPlugins.resolve("slot").map(item => item.id);
            let duplicate, missing;
            try { posReactPlugins.register("slot", "middle", {}); } catch (error) { duplicate = error.message; }
            posReactPlugins.register("action", "orphan", {}, { before: "absent" });
            try { posReactPlugins.resolve("action"); } catch (error) { missing = error.message; }
            console.log(JSON.stringify({ order, duplicate, missing }));
        """)
        self.assertEqual(result["order"], ["middle", "first", "last"])
        self.assertIn("Duplicate", result["duplicate"])
        self.assertIn("Missing", result["missing"])

    def test_unregister_is_idempotent_and_cleans_up(self):
        result = run_registry("""
            let cleanups = 0;
            const unregister = posReactPlugins.register("paymentAdapter", "terminal", { cleanup() { cleanups++; } });
            unregister();
            unregister();
            console.log(JSON.stringify({ cleanups, remaining: posReactPlugins.resolve("paymentAdapter").length }));
        """)
        self.assertEqual(result, {"cleanups": 1, "remaining": 0})

    def test_plugin_contracts_are_owned_manifested_and_executable(self):
        sources = []
        artifacts = [REGISTRY, MODULE / "static/src/app.js"]
        for module, points in PLUGIN_CONTRACTS.items():
            manifest_path = ROOT / module / "__manifest__.py"
            manifest = ast.literal_eval(manifest_path.read_text(encoding="utf-8"))
            scripts = manifest.get("pos_react_plugin_scripts", [])
            self.assertEqual(len(scripts), 1, module)
            self.assertEqual(scripts[0].lstrip("/").split("/", 1)[0], module)
            script = ROOT / scripts[0].lstrip("/")
            self.assertTrue(script.is_file(), script)
            self.assertTrue(script.resolve().is_relative_to((ROOT / module).resolve()), script)
            sources.append(script)
            artifacts.extend((manifest_path, script))

        artifact_sha256 = {
            str(path.relative_to(MODULE.parents[2])): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in artifacts
        }
        generic_core = "\n".join(path.read_text(encoding="utf-8") for path in artifacts[:2])
        for registrations in PLUGIN_CONTRACTS.values():
            for registration in registrations.values():
                self.assertNotIn(registration, generic_core)

        result = {
            "artifact_sha256": artifact_sha256,
            "registrations": run_registry("""
                const registrations = Object.fromEntries(posReactPlugins.points.map(
                    point => [point, posReactPlugins.resolve(point).map(item => item.id)]
                ));
                console.log(JSON.stringify(registrations));
            """, sources),
        }
        for module, registrations in PLUGIN_CONTRACTS.items():
            for point, registration in registrations.items():
                self.assertIn(registration, result["registrations"][point], (module, point))

    def test_plugin_behavior(self):
        sources = [
            ROOT / "pos_sale/static/src/pos_react_plugin.js",
            MODULE / "static/src/restaurant_adapter.js",
            ROOT / "pos_stripe/static/src/pos_react_plugin.js",
        ]
        result = run_registry("""
            const saleContext = {
                lines: [{ uuid: "a", quantity: 2 }, { uuid: "b", quantity: 1 }], total: 42,
                formatMoney: value => `$${value}`,
            };
            let alert;
            window.alert = value => { alert = value; };
            posReactPlugins.resolve("action")[0].value.run(saleContext);
            const receipt = posReactPlugins.resolve("receiptFragment")[0].value.component(saleContext);

            const restaurantScreen = posReactPlugins.resolve("screen")[0].value.component;
            let screen = "floor", restaurantContext = {};
            const restaurant = restaurantScreen({
                restaurant: { tables: [{ id: 7, table_number: 12 }] },
                restaurantContext: {},
                setRestaurantContext: value => { Object.assign(restaurantContext, value); },
                setScreen: value => { screen = value; },
            });
            restaurant.children[1].children[1].props.onChange({ target: { value: "7" } });
            restaurant.children[2].children[1].props.onChange({ target: { value: "3" } });
            restaurant.children[3].props.onClick();
            const transform = posReactPlugins.resolve("dataRequirement")[0].value.transform;
            const existing = { tables: [1] };

            const stripe = posReactPlugins.resolve("paymentAdapter")[0].value;
            const payment = { amount: 42 };
            const stripeSuccess = await stripe.start({ pluginData: {
                payment,
                terminal: { collectPaymentMethod: candidate => candidate === payment ? "paid" : false },
            }});
            const stripeUnavailable = await stripe.start({ pluginData: {} });
            console.log(JSON.stringify({
                alert, receipt: receipt.children[0],
                restaurantTitle: restaurant.children[0].children[0], screen, restaurantContext,
                restaurantDefault: transform({}).restaurant,
                restaurantExisting: transform({ restaurant: existing }).restaurant.tables === existing.tables,
                stripeSuccess, stripeUnavailable,
            }));
        """, sources)
        self.assertEqual(result, {
            "alert": "3 items · $42",
            "receipt": "3 items · $42",
            "restaurantTitle": "Restaurant",
            "screen": None,
            "restaurantContext": {"tableId": 7, "customerCount": 3},
            "restaurantDefault": {"tables": []},
            "restaurantExisting": True,
            "stripeSuccess": "paid",
            "stripeUnavailable": False,
        })

    def test_stripe_terminal_lifecycle(self):
        stripe_plugin = ROOT / "pos_stripe/static/src/pos_react_plugin.js"
        result = run_registry("""
            global.document = {
                head: { append() { throw new Error("SDK should already be loaded"); } },
                createElement() { return {}; },
            };
            const calls = [];
            const terminal = {
                getConnectionStatus: () => "not_connected",
                discoverReaders: async options => {
                    calls.push(["discover", options]);
                    return { discoveredReaders: [{ serial_number: "SIMULATOR" }] };
                },
                connectReader: async (reader, options) => {
                    calls.push(["connect", reader.serial_number, options]);
                    return { reader };
                },
                collectPaymentMethod: async (secret, options) => {
                    calls.push(["collect", secret, options]);
                    return { paymentIntent: { id: "pi_collect" } };
                },
                processPayment: async intent => {
                    calls.push(["process", intent.id]);
                    return { paymentIntent: { id: "pi_done" } };
                },
                cancelCollectPaymentMethod: async () => calls.push(["cancel"]),
            };
            global.StripeTerminal = { create: options => {
                calls.push(["create"]);
                options.onFetchConnectionToken().then(token => calls.push(["token", token]));
                return terminal;
            }};
            eval("" + %s);
            const payment = { amount: 42, method: { id: 9 } };
            const rpc = async (model, method, args) => {
                calls.push(["rpc", method, args]);
                if (method === "read") return [{ stripe_serial_number: "SIMULATOR" }];
                if (method === "stripe_connection_token") return { secret: "pst_test" };
                if (method === "stripe_payment_intent") return { client_secret: "secret" };
                if (method === "stripe_capture_payment") return {
                    id: "pi_done",
                    charges: { data: [{ payment_method_details: { card_present: { brand: "visa" } } }] },
                };
                if (method === "stripe_refund") return { id: "re_done" };
            };
            const stripe = posReactPlugins.resolve("paymentAdapter")[0].value;
            const outcome = await stripe.start({ payment, rpc });
            const refund = await stripe.refund({
                payment: { amount: -12, method: { id: 9 }, transaction_id: "pi_done" },
                rpc,
            });
            await stripe.cancel();
            console.log(JSON.stringify({ outcome, refund, calls }));
        """ % json.dumps(STRIPE_ADAPTER.read_text(encoding="utf-8")), [stripe_plugin])
        self.assertEqual(result["outcome"], {
            "state": "done", "transaction_id": "pi_done", "card_type": "visa",
        })
        self.assertEqual(result["refund"], {"state": "done", "transaction_id": "re_done"})
        self.assertIn(["collect", "secret", {"enable_customer_cancellation": True}], result["calls"])
        self.assertIn(["process", "pi_collect"], result["calls"])
        self.assertIn(["rpc", "stripe_capture_payment", ["pi_done"]], result["calls"])
        self.assertIn(["rpc", "stripe_refund", [[9], "pi_done", -12]], result["calls"])

    def test_point_of_sale_worktree_is_untouched(self):
        result = subprocess.run(
            ["git", "status", "--porcelain", "--", "odoo/addons/point_of_sale"],
            cwd=MODULE.parents[2],
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.stdout, "")


if __name__ == "__main__":
    unittest.main()
