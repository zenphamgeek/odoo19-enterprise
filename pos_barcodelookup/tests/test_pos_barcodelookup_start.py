import ast
import json
import os
import shutil
import subprocess
import unittest
from pathlib import Path

try:
    from odoo.tests import tagged
    from ...product_barcodelookup.tests.test_barcodelookup_flow import TestBarcodelookup
    from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon
except (ImportError, AttributeError):
    tagged = lambda *args, **kwargs: (lambda c: c)
    class TestBarcodelookup: pass
    class TestPointOfSaleHttpCommon: pass


MODULE = Path(__file__).parents[1]


def _resolve_plugin_script(manifest: dict, index: int = 0) -> Path:
    scripts = manifest.get("pos_react_plugin_scripts") or []
    if not scripts or index >= len(scripts):
        raise IndexError("No plugin scripts configured in manifest")
    raw_path = scripts[index]
    if not isinstance(raw_path, str) or not raw_path.startswith("/pos_barcodelookup/static/src/"):
        raise ValueError(f"Invalid plugin script path: {raw_path}")
    if ".." in raw_path:
        raise ValueError(f"Path traversal sequence detected: {raw_path}")

    rel_path = raw_path.removeprefix("/pos_barcodelookup/")
    resolved = (MODULE / rel_path).resolve()
    if not resolved.is_relative_to(MODULE.resolve()):
        raise ValueError(f"Path traversal violation: {resolved}")
    if not resolved.is_file():
        raise FileNotFoundError(f"Plugin script file not found: {resolved}")
    return resolved


def _run_node_isolated(script_content: str, args: list = None, timeout: float = 5.0) -> subprocess.CompletedProcess:
    """Executes Node script under strict environment containment, timeout bounds, and CLI checks (CWE-78, CWE-400)."""
    node_bin = shutil.which("node")
    if not node_bin:
        raise unittest.SkipTest("Node.js runtime not available in environment")
    cmd = [node_bin, "-e", script_content]
    if args:
        cmd.extend(args)
    clean_env = {
        "NODE_ENV": "test",
        "PATH": os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin"),
    }
    return subprocess.run(
        cmd,
        check=True,
        capture_output=True,
        text=True,
        timeout=timeout,
        env=clean_env,
    )


class TestPOSReactPlugin(unittest.TestCase):
    def test_action_matches_legacy_permissions_authentication_and_services(self):
        manifest = ast.literal_eval((MODULE / "__manifest__.py").read_text(encoding="utf-8"))
        script_path = _resolve_plugin_script(manifest, 0)
        node_script = """
            const fs = require('fs');
            const targetPath = process.argv[1];
            if (!targetPath || !fs.existsSync(targetPath)) {
                console.error("Missing or invalid script path:", targetPath);
                process.exit(1);
            }
            global.window = global;
            let action, fetches = 0, navigations = 0;
            global.posReactPlugins = { register(point, id, value) { action = { point, id, value }; } };
            global.prompt = () => "710535977349";
            global.fetch = async () => { fetches++; throw new Error("fetch must not run when rpc exists"); };
            global.location = { assign() { navigations++; } };

            const code = fs.readFileSync(targetPath, 'utf-8');
            new Function(code)();

            (async () => {
                const calls = [], actions = [];
                const base = {
                    pluginData: { barcode: "710535977349" },
                    rpc: async (...args) => { calls.push(args); return { authenticated: true }; },
                    doAction: async (...args) => actions.push(args),
                    allowProductCreation: async () => true,
                };
                const success = await action.value.run(base);
                const denied = await action.value.run({ ...base, allowProductCreation: async () => false });
                const unauthenticated = await action.value.run({ ...base, rpc: async () => ({ authenticated: false }) });
                console.log(JSON.stringify({ point: action.point, id: action.id, success, denied, unauthenticated, calls, actions, fetches, navigations }));
            })();
        """
        result = subprocess.run(
            ["node", "-e", node_script, str(script_path)],
            check=True,
            capture_output=True,
            text=True,
        )
        behavior = json.loads(result.stdout)
        self.assertEqual((behavior["point"], behavior["id"], behavior["success"]), ("action", "pos_barcodelookup.create", True))
        self.assertFalse(behavior["denied"])
        self.assertFalse(behavior["unauthenticated"])
        self.assertEqual(behavior["calls"][0], ["product.template", "barcode_lookup", []])
        self.assertEqual(behavior["actions"][0], ["point_of_sale.product_template_action_add_pos", {"additionalContext": {"default_barcode": "710535977349"}}])
        self.assertEqual((behavior["fetches"], behavior["navigations"]), (0, 0))

    def test_fallback_uses_generic_api_and_rejects_bad_http_before_json(self):
        script_path = (MODULE / "static/src/pos_react_plugin.js").resolve()
        if not script_path.is_relative_to(MODULE.resolve()):
            raise ValueError(f"Path traversal violation: {script_path}")
        if not script_path.is_file():
            raise FileNotFoundError(f"Plugin script file not found: {script_path}")

        node_script = """
            const fs = require('fs');
            const targetPath = process.argv[1];
            if (!targetPath || !fs.existsSync(targetPath)) {
                console.error("Missing or invalid script path:", targetPath);
                process.exit(1);
            }
            global.window = global;
            let action, requested, navigated = [];
            global.posReactPlugins = { register(point, id, value) { action = value; } };
            global.location = { assign(url) { navigated.push(url); } };

            const code = fs.readFileSync(targetPath, 'utf-8');
            new Function(code)();

            (async () => {
                const run = (response) => {
                    global.fetch = async (url, options) => { requested = { url, options }; return response; };
                    return action.run({ pluginData: { barcode: "123" }, allowProductCreation: async () => true });
                };
                const badStatus = await run({ ok: false, status: 500, headers: { get: () => "application/json" }, json: () => { throw new Error("json called"); } });
                const badType = await run({ ok: true, status: 200, headers: { get: () => "text/html" }, json: () => { throw new Error("json called"); } });
                const success = await run({ ok: true, status: 200, headers: { get: () => "application/json; charset=utf-8" }, json: async () => ({ result: { authenticated: true } }) });
                console.log(JSON.stringify({ badStatus, badType, success, requested, navigated }));
            })();
        """
        result = subprocess.run(
            ["node", "-e", node_script, str(script_path)],
            check=True,
            capture_output=True,
            text=True,
        )
        behavior = json.loads(result.stdout)
        self.assertEqual((behavior["badStatus"], behavior["badType"], behavior["success"]), (False, False, True))
        self.assertEqual(behavior["requested"]["url"], "/api/model/call")
        self.assertEqual(json.loads(behavior["requested"]["options"]["body"])["params"]["method"], "barcode_lookup")
        self.assertEqual(len(behavior["navigated"]), 1)


@tagged('post_install', '-at_install')
class TestPOSBarcodelookup(TestPointOfSaleHttpCommon, TestBarcodelookup):
    def test_01_pos_barcodelookup_flow(self):
        with self.mockBarcodelookupAutofill():
            self.main_pos_config.open_ui()
            self.start_pos_tour('PosBarcodelookupFlow', login="accountman")
        product = self.env['product.template'].sudo().search([('name', '=', 'Odoo Scale up')], limit=1)
        self.assertEqual(product.name, "Odoo Scale up")
        self.assertEqual(product.list_price, 100)
        #  Product created from pos should be available_in_pos by default
        self.assertTrue(product.available_in_pos)
