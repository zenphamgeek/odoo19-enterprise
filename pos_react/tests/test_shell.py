import importlib.util
import unittest
from pathlib import Path

MODULE = Path(__file__).parents[1]
SPEC = importlib.util.spec_from_file_location("pos_react_controller", MODULE / "controllers/main.py")
CONTROLLER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CONTROLLER)


class ShellTest(unittest.TestCase):
    def test_pos_role_requires_configured_user_group(self):
        class Record:
            def __init__(self, record_id):
                self.id = record_id

        class User:
            all_group_ids = type("Groups", (), {"ids": [10, 20]})()

        config = type("Config", (), {
            "group_pos_user_id": Record(10),
            "group_pos_manager_id": Record(20),
        })()
        self.assertEqual(CONTROLLER._pos_role(User(), config), "manager")
        config.group_pos_manager_id = Record(30)
        self.assertEqual(CONTROLLER._pos_role(User(), config), "cashier")
        config.group_pos_user_id = Record(30)
        self.assertFalse(CONTROLLER._pos_role(User(), config))
        config.group_pos_user_id = False
        self.assertFalse(CONTROLLER._pos_role(User(), config))

    def test_installable_isolated_react_shell(self):
        manifest = (MODULE / "__manifest__.py").read_text(encoding="utf-8")
        controller = (MODULE / "controllers/main.py").read_text(encoding="utf-8")
        template = (MODULE / "views/shell.xml").read_text(encoding="utf-8")
        app = (MODULE / "static/src/app.js").read_text(encoding="utf-8")
        offline = (MODULE / "static/src/offline_store.js").read_text(encoding="utf-8")
        realtime = (MODULE / "static/src/realtime.js").read_text(encoding="utf-8")

        self.assertIn('"installable": True', manifest)
        self.assertIn('/pos/react/<int:config_id>', controller)
        self.assertIn('auth="user"', controller)
        self.assertIn("react.production.min.js", template)
        self.assertIn("ReactDOM.createRoot", app)
        self.assertIn("updateCart", app)
        self.assertIn('const [cart, setCart] = useState([]);', app)
        self.assertIn('function updateCart(cart, product, delta, uuid = null)', app)
        self.assertIn('Object.entries(cart).map(([productId, quantity]) => ({ uuid: crypto.randomUUID(), productId: Number(productId), quantity }))', app)
        self.assertIn('const line = uuid ? cart.find((item) => item.uuid === uuid)', app)
        self.assertIn('uuid: crypto.randomUUID(), productId: product.id, quantity, price: product.price, taxIds: product.taxIds, discount: 0, extraTaxData: {}', app)
        self.assertIn('const { uuid, productId, quantity, product, price, taxIds, discount, extraTaxData, ...attributes } = selected[index];', app)
        self.assertIn('extra_tax_data: line.extraTaxData,', app)
        self.assertIn('const replaceCart = async (next) => {', app)
        self.assertIn('replaceCart, taxContext, restaurant:', app)
        self.assertIn('slot === "cartControls"', app)
        self.assertIn('...attributes,', app)
        self.assertIn('const lineSnapshot = (line) => {', app)
        self.assertIn('remoteLines.sort((a, b) => a.uuid.localeCompare(b.uuid))', app)
        self.assertIn('onClick: () => mutateCart(product, -1, uuid)', app)
        self.assertIn('key: uuid', app)
        self.assertNotIn("lineUuids", app)
        self.assertNotIn("cart[product.id]", app)
        self.assertIn("category", app)
        self.assertNotIn("const PRODUCTS", app)
        self.assertIn('load_data([', controller)
        self.assertIn('"pos.category", "product.template", "product.product"', controller)
        self.assertIn('type="application/json"', template)
        self.assertIn('"accessToken": session.config_id.access_token', controller)
        self.assertIn('"websocketWorkerVersion": request.env["is.http"].session_info()["websocket_worker_version"]', controller)
        self.assertIn('type: "search"', app)
        self.assertIn("product.categoryIds.includes(categoryId)", app)
        self.assertIn('async function rpc(model, method, args = [], kwargs = {})', app)
        self.assertIn('fetch("/api/model/call"', app)
        self.assertNotIn('/web/dataset/call_kw/${model}/${method}', app)
        self.assertLess(app.index('response.ok'), app.index('response.json()'))
        self.assertLess(app.index('content-type'), app.index('response.json()'))
        self.assertIn('function doAction(action, { additionalContext = {} } = {})', app)
        self.assertIn('allowProductCreation: async () => allowProductCreation', app)
        self.assertIn('request.env["product.template"].has_access("create")', controller)
        for field in ('"tenantId"', '"userId"', '"sessionId"', '"configId"', '"companyId"', '"cashMethodId"', '"lastDataChange"', '"taxIds"'):
            self.assertIn(field, controller)
        self.assertIn('await store.commitDraft(draftId);', app)
        checkout = app[app.index('const checkoutDraft'):app.index('const checkoutCash')]
        self.assertLess(checkout.index('await store.commitDraft(draftId);'), checkout.index('store.drain().catch'))
        recovery = app[app.index('const recover'):app.index('const lockFinalized')]
        self.assertLess(recovery.index('await store.drain().catch(() => {});'), recovery.index('await refreshPending();'))
        reconnect = app[app.index('const reconnect = () => {'):app.index('globalThis.addEventListener("online", reconnect);')]
        self.assertLess(reconnect.index('recover();'), reconnect.index('reconcileDraft().catch(() => {});'))
        self.assertEqual(app.count('addEventListener("online", reconnect)'), 1)
        self.assertEqual(app.count("posReactOfflineStore.create({"), 1)
        self.assertIn("const store = useMemo(() => posReactOfflineStore.create({", app)
        self.assertIn("}), [tenantId, configId, userId, sessionId, companyId, currency.decimalPlaces]);", app)
        cleanup = app[app.index('return () => {', app.index('const recover')):app.index('}, [store]);')]
        self.assertLess(cleanup.index('removeEventListener("online", reconnect)'), cleanup.index("store.close();"))
        self.assertNotIn('addEventListener?.("online"', (MODULE / "static/src/offline_store.js").read_text(encoding="utf-8"))
        self.assertIn('rpc("pos.order", "pos_react_sync_from_ui", [[order]])', app)
        self.assertIn('...(tableId ? { table_id: tableId, customer_count: customerCount || false } : {}),', app)
        self.assertIn('...restaurantContext, sessionId, companyId', app)
        self.assertIn('restaurantContext: { ...restaurantContext, locked:', app)
        self.assertIn('tableId: draft.table_id?.[0] || draft.table_id || false,', app)
        self.assertIn('customerCount: draft.customer_count || false,', app)
        self.assertIn('payment_date: new Date().toISOString().slice(0, 19).replace("T", " "),', app)
        self.assertIn('"electronicPaymentMethods": [{', controller)
        self.assertIn('const PAYMENT_STATES = new Set(["pending", "waiting", "done", "retry", "cancelled"]);', app)
        self.assertIn('if (state === "done") {', app)
        self.assertLess(app.index('if (state === "done") {'), app.index('await checkoutDraft()', app.index('if (state === "done") {')))
        self.assertIn('onClick: cancelElectronicPayment', app)
        self.assertIn('onClick: () => runElectronicPayment(electronicPayment.adapter, electronicPayment.method, true)', app)
        self.assertIn('role: "status"', app)
        self.assertIn('token: accessToken,', app)
        self.assertIn('version: websocketWorkerVersion,', app)
        self.assertIn('onSynchronisation: recover,', app)
        synchronisation = app[app.index('onSynchronisation: recover,'):app.index('onStatus: (status) => {')]
        self.assertNotIn('reconcileDraft', synchronisation)
        self.assertNotIn('mutationLocked', synchronisation)
        self.assertIn('draftIdentity.current.serverId = ack["pos.order"][0].id;', app)
        self.assertNotIn('synchronisationSuppressedUntil', app)
        self.assertIn('posReactMetadataGraph.constructOpenOrderQuery(metadataGraph.all("pos.order")', app)
        self.assertIn('serverId ? [serverId] : []', app)
        self.assertIn('await metadataGraph.completeRelations(records,', app)
        self.assertIn('rpc(model, "read", [ids, fields], { load: false })', app)
        self.assertIn('metadataGraph.mergeDelta({ records, deleted: deletedRecords });', app)
        self.assertIn('const deleted = Boolean(order?._deleted);', app)
        self.assertIn('const changed = order?.state === "draft"', app)
        self.assertIn('draftPayload.current = paidDraft;', app)
        connected = app[app.index('if (status === "connected") {'):app.index('const reconnect = () => {')]
        self.assertIn('reconcileDraft().catch(() => {});', connected)
        self.assertNotIn('synchronisationSuppressedUntil', connected)
        self.assertIn('globalThis.addEventListener("online", reconnect);', app)
        self.assertNotIn('synchronisationSuppressedUntil', reconnect)
        self.assertIn('globalThis.removeEventListener("online", reconnect);', app)
        self.assertIn('realtime.close();', app)
        self.assertIn('setRealtimeStatus(status);', app)
        self.assertIn('url ||= `${location.origin.replace(/^http/, "ws")}/websocket?version=${encodeURIComponent(version)}`;', realtime)
        self.assertIn('new WebSocket(url)', realtime)
        self.assertIn('event_name: "subscribe", data: { channels: [token], last: lastId }', realtime)
        self.assertIn('onStatus("connecting")', realtime)
        self.assertIn('onStatus("connected")', realtime)
        self.assertIn('onStatus("disconnected")', realtime)
        self.assertIn('removeEventListener("online", reconnectOnline)', realtime)
        self.assertIn('"aria-live": "polite"', app)
        self.assertIn('"aria-labelledby": "recovery-title"', app)
        self.assertIn('"Delete exported copy"', app)
        self.assertIn("deleteConfirmations[item.id] !== item.id", app)
        self.assertIn('role: "alert"', app)
        self.assertIn('"aria-label": "Recovery error"', app)
        self.assertIn('"aria-label": "Recovery operation"', app)
        self.assertIn("disabled: Boolean(recoveryBusy)", app)
        self.assertIn('proof: await valueHash(record)', offline)
        self.assertIn("if (checkoutLocked.current || mutationLocked.current || !draftReady || mutating || !total) return false;", app)
        self.assertIn("const checkoutCash = () => cashMethodId ? checkoutDraft() : false;", app)
        self.assertLess(app.index("checkoutLocked.current = true;"), app.index("await store.commitDraft(draftId);"))
        self.assertIn("disabled: !draftReady || mutating || checkingOut || Boolean(finalizedAlert) || !cashMethodId || !total", app)
        self.assertIn("const SCHEMA_VERSION = 4;", offline)
        self.assertIn('db.transaction([DRAFTS_STORE, STORE], "readwrite")', offline)
        self.assertIn("const scope = scopeFor({ tenantId, configId, userId, sessionId, companyId });", offline)
        self.assertIn('errorCode: "SCOPE_MISMATCH"', offline)
        self.assertLess(offline.index('errorCode: "SCOPE_MISMATCH"'), offline.index("ack = await send"))
        self.assertNotIn("canary", controller.lower() + app.lower())
        self.assertNotIn("point_of_sale.assets", template)
        service_worker = (MODULE / "static/src/service_worker.js").read_text(encoding="utf-8")
        self.assertIn('/pos/react/service-worker.js', controller)
        self.assertIn('("Service-Worker-Allowed", "/pos/react/")', controller)
        self.assertIn('navigator.serviceWorker.register("/pos/react/service-worker.js", { scope: "/pos/react/" })', app)
        self.assertLess(app.index("ReactDOM.createRoot"), app.index("navigator.serviceWorker.register"))
        self.assertIn('type: "CACHE_NAVIGATION", url: location.href, assets, owner: `${INITIAL_DATA.tenantId}:${INITIAL_DATA.userId}`', app)
        for asset in ("app.css", "react.production.min.js", "react-dom.production.min.js", "plugin_registry.js", "offline_store.js", "metadata_graph.js", "tax_engine.js", "pricelist_engine.js", "app.js"):
            self.assertIn(asset, service_worker)
        self.assertIn('request.mode === "navigate"', service_worker)
        self.assertIn('const OWNER_KEY = new URL("__navigation_owner__", self.registration.scope).href;', service_worker)
        self.assertIn('"/pos_react/static/src/realtime.js"', service_worker)
        self.assertIn('caches.open(CACHE).then((cache) => cache.addAll(STATIC))', service_worker)
        self.assertIn('keys.filter((key) => key.startsWith("pos-react-cold-start-") && key !== CACHE).map((key) => caches.delete(key))', service_worker)
        self.assertIn("cache.put(OWNER_KEY, new Response(owner))", service_worker)
        self.assertIn("await current.text() !== owner", service_worker)
        self.assertIn("Promise.all(keys.map((key) => cache.delete(key)))", service_worker)
        self.assertIn("if (!current) return Response.error();", service_worker)
        self.assertIn("|| Response.error()", service_worker)
        self.assertIn("event.source.url", service_worker)

    def test_plugin_scripts_load_between_registry_and_app(self):
        controller = (MODULE / "controllers/main.py").read_text(encoding="utf-8")
        template = (MODULE / "views/shell.xml").read_text(encoding="utf-8")
        self.assertIn('get("pos_react_plugin_scripts", [])', controller)
        self.assertIn('if module.name == "pos_restaurant":', controller)
        self.assertIn('"restaurant": restaurant', controller)
        self.assertIn('"restaurant.table"]._load_pos_data_read', controller)
        self.assertLess(template.index("plugin_registry.js"), template.index("restaurant_adapter.js"))
        self.assertLess(template.index("restaurant_adapter.js"), template.index('t-foreach="plugin_scripts"'))
        self.assertLess(template.index('t-foreach="plugin_scripts"'), template.index("app.js"))
        self.assertLess(template.index("offline_store.js"), template.index("metadata_graph.js"))
        self.assertLess(template.index("metadata_graph.js"), template.index("tax_engine.js"))
        self.assertLess(template.index("tax_engine.js"), template.index("pricelist_engine.js"))
        self.assertLess(template.index("pricelist_engine.js"), template.index("realtime.js"))
        self.assertLess(template.index("realtime.js"), template.index("app.js"))
        self.assertNotIn("canary", controller.lower() + template.lower())

    def test_plugin_script_paths_are_same_origin_static_javascript(self):
        accepted = ["/addon/static/src/plugin.js", "/addon_name/static/plugin.min.js"]
        rejected = [
            "https://example.com/plugin.js", "//example.com/plugin.js",
            "/addon/plugin.js", "/addon/static/../plugin.js", "/addon/static/plugin.css",
        ]
        self.assertTrue(all(CONTROLLER._PLUGIN_SCRIPT_PATH.fullmatch(path) for path in accepted))
        self.assertTrue(all(not CONTROLLER._PLUGIN_SCRIPT_PATH.fullmatch(path) for path in rejected))

    def test_vendored_runtime_present(self):
        for name in ("react.production.min.js", "react-dom.production.min.js"):
            path = MODULE / "static/lib/react" / name
            self.assertGreater(path.stat().st_size, 10_000)


if __name__ == "__main__":
    unittest.main()
