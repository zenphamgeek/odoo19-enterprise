import json
from unittest.mock import patch

from odoo.addons.pos_restaurant.tests.test_frontend import TestFrontendCommon
from odoo.tests import tagged
from odoo.tests.common import ChromeBrowser


class ColdReloadBrowser(ChromeBrowser):
    reload_count = 0
    blocked_requests = 0
    target_before = None
    target_after = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        type(self).target_before = self._websocket_request("Target.getTargetInfo")["targetInfo"]["targetId"]
        self._websocket_request("Network.enable")
        self._websocket_request("Fetch.enable", params={"patterns": [{"urlPattern": "*", "requestStage": "Request"}]})

    def _handle_request_paused(self, **params):
        if self.reload_count:
            type(self).blocked_requests += 1
            self._websocket_send("Fetch.failRequest", params={"requestId": params["requestId"], "errorReason": "InternetDisconnected"})
            return
        super()._handle_request_paused(**params)

    def _handle_console(self, type, args=None, **kwargs):
        message = args and self._from_remoteobject(args[0])
        if message == "POS cache ready" and not self.reload_count:
            self.__class__.reload_count = 1
            self._websocket_send("Network.setCacheDisabled", params={"cacheDisabled": True})
            self._websocket_send("Network.emulateNetworkConditions", params={
                "offline": True,
                "latency": 0,
                "downloadThroughput": 0,
                "uploadThroughput": 0,
            })
            self._websocket_send("Page.reload")
        super()._handle_console(type, args=args, **kwargs)

    def _handle_frame_stopped_loading(self, frameId):
        super()._handle_frame_stopped_loading(frameId)
        if self.reload_count != 1 or self.target_after:
            return
        future = self._websocket_send("Target.getTargetInfo", with_future=True)
        future.add_done_callback(lambda result: setattr(type(self), "target_after", result.result()["targetInfo"]["targetId"]))
        self._websocket_send("Runtime.evaluate", params={"expression": """
            (async () => {
                for (let attempt = 0; attempt < 100; attempt++) {
                    const products = document.querySelectorAll('#pos-react-root .product');
                    const categories = document.querySelectorAll('#pos-react-root nav button');
                    if (products.length && categories.length > 1 && globalThis.posReact?.catalog?.offline === true) {
                        console.log('POS cold reload succeeded');
                        return;
                    }
                    await new Promise(resolve => setTimeout(resolve, 100));
                }
                throw new Error('cached POS shell/catalog missing after cold reload');
            })();
        """})


class SameTabDraftReloadBrowser(ChromeBrowser):
    reload_count = 0
    target_before = None
    target_after = None
    sync_graphs = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        type(self).target_before = self._websocket_request("Target.getTargetInfo")["targetInfo"]["targetId"]
        self._websocket_request("Fetch.enable", params={"patterns": [{"urlPattern": "*", "requestStage": "Request"}]})

    def _handle_request_paused(self, **params):
        post_data = params["request"].get("postData", "")
        if "sync_from_ui" in post_data:
            graph = json.loads(post_data)["params"]["args"][0][0]
            if graph.get("state") == "paid":
                type(self).sync_graphs.append(graph)
        super()._handle_request_paused(**params)

    def _handle_console(self, type, args=None, **kwargs):
        message = args and self._from_remoteobject(args[0])
        if message == "same-tab draft reload pending" and not self.reload_count:
            self.__class__.reload_count = 1
            self._websocket_send("Page.reload", params={"ignoreCache": True})
        super()._handle_console(type, args=args, **kwargs)

    def _handle_frame_stopped_loading(self, frameId):
        super()._handle_frame_stopped_loading(frameId)
        if self.reload_count != 1 or self.target_after:
            return
        future = self._websocket_send("Target.getTargetInfo", with_future=True)
        future.add_done_callback(lambda result: setattr(type(self), "target_after", result.result()["targetInfo"]["targetId"]))
        self._websocket_send("Runtime.evaluate", params={"expression": """
            (async () => {
                const consoleErrors = [];
                const originalConsoleError = console.error;
                console.error = (...args) => { consoleErrors.push(args.map(String).join(' ')); originalConsoleError(...args); };
                addEventListener('error', event => consoleErrors.push(String(event.error || event.message)));
                addEventListener('unhandledrejection', event => consoleErrors.push(String(event.reason)));
                const expected = JSON.parse(sessionStorage.getItem('pos-react-reload-draft'));
                for (let attempt = 0; attempt < 300 && !document.querySelector('.line'); attempt++) {
                    await new Promise(resolve => setTimeout(resolve, 100));
                }
                const dataNode = document.getElementById('pos-react-data');
                const data = dataNode && JSON.parse(dataNode.textContent);
                const scopeKey = data && `${data.tenantId}:${data.configId}:${data.userId}:${data.sessionId}:${data.companyId}`;
                let draft;
                if (data) {
                    const name = `pos-react:${encodeURIComponent(data.tenantId)}:${encodeURIComponent(data.configId)}:${encodeURIComponent(data.userId)}`;
                    draft = await new Promise((resolve, reject) => {
                        const request = indexedDB.open(name);
                        request.onerror = () => reject(request.error);
                        request.onsuccess = () => {
                            const database = request.result;
                            const result = database.transaction('drafts').objectStore('drafts').get(scopeKey);
                            result.onerror = () => reject(result.error);
                            result.onsuccess = () => { database.close(); resolve(result.result?.active); };
                        };
                    });
                }
                const line = document.querySelector('.line');
                const total = document.querySelector('aside footer strong:last-child')?.textContent;
                const failed = !line?.textContent.includes('× 2') || total !== expected.total ||
                    draft?.uuid !== expected.orderUuid || draft?.lines?.[0]?.[2]?.uuid !== expected.lineUuid ||
                    (expected.tableId && (draft?.table_id !== expected.tableId || draft?.customer_count !== expected.customerCount));
                if (failed) {
                    console.error('same-tab draft reload diagnostics', JSON.stringify({
                        scopeKey,
                        draft,
                        cart: document.querySelector('aside')?.innerText,
                        disabled: [...document.querySelectorAll('button:disabled')].map(button => button.textContent.trim()),
                        alerts: [...document.querySelectorAll('[role="alert"], .alert')].map(alert => alert.textContent.trim()),
                        consoleErrors,
                    }));
                    throw new Error('reloaded draft state mismatch');
                }
                if (expected.tableId) {
                    [...document.querySelectorAll('button')].find(button => button.textContent === 'Restaurant').click();
                    let table;
                    let guests;
                    for (let attempt = 0; attempt < 100 && (!table || !guests); attempt++) {
                        table = document.querySelector('[aria-label="Restaurant table"]');
                        guests = document.querySelector('[aria-label="Guest count"]');
                        await new Promise(resolve => setTimeout(resolve, 20));
                    }
                    if (Number(table?.value) !== expected.tableId || Number(guests?.value) !== expected.customerCount) throw new Error('reloaded restaurant context mismatch');
                    [...document.querySelectorAll('button')].find(button => button.textContent === 'Back').click();
                }
                const before = await posReact.rpc('pos.order', 'search_count', [[['uuid', '=', expected.orderUuid]]]);
                if (before !== 1) throw new Error('reloaded server draft missing');
                const payCash = [...document.querySelectorAll('button')].find(button => button.textContent === 'Pay cash');
                payCash.click();
                payCash.click();
                for (let attempt = 0; attempt < 100; attempt++) {
                    const orders = await posReact.rpc('pos.order', 'search_read', [[['uuid', '=', expected.orderUuid]], ['state', 'table_id', 'customer_count']]);
                    if (orders.length === 1 && orders[0].state === 'paid' &&
                        (!expected.tableId || (orders[0].table_id?.[0] === expected.tableId && orders[0].customer_count === expected.customerCount))) {
                        console.log('same-tab draft reload succeeded');
                        return;
                    }
                    await new Promise(resolve => setTimeout(resolve, 100));
                }
                throw new Error('reloaded checkout did not finalize server draft');
            })();
        """})


class ElectronicPaymentOracleBrowser(ChromeBrowser):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._websocket_request("Page.addScriptToEvaluateOnNewDocument", params={"source": """
            Object.defineProperty(window, 'posReactPlugins', { configurable: true, set(registry) {
                Object.defineProperty(window, 'posReactPlugins', { value: registry, configurable: true });
                let attempt = 0;
                registry.register('paymentAdapter', 'browser-oracle', {
                    label: 'Browser oracle',
                    start(context) {
                        attempt += 1;
                        window.electronicPaymentStartCount = attempt;
                        window.electronicPaymentAmounts = [...(window.electronicPaymentAmounts || []), context.payment.amount];
                        if (attempt === 1) return new Promise(resolve => { window.releaseElectronicPayment = () => resolve('done'); });
                        return attempt === 2 ? 'retry' : 'done';
                    },
                    cancel() {
                        window.electronicPaymentCancelCount = (window.electronicPaymentCancelCount || 0) + 1;
                    },
                });
            }});
        """})


class AbortFirstSyncResponseBrowser(ChromeBrowser):
    aborted_uuid = None
    abort_count = 0
    paid_sync_uuids = []
    reload_count = 0
    target_before = None
    target_after = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        type(self).target_before = self._websocket_request("Target.getTargetInfo")["targetInfo"]["targetId"]
        self._websocket_request("Fetch.enable", params={"patterns": [{"urlPattern": "*", "requestStage": "Response"}]})

    def _handle_request_paused(self, **params):
        request = params["request"]
        if "sync_from_ui" in request.get("postData", ""):
            payload = json.loads(request["postData"])["params"]["args"][0][0]
            uuid = payload["uuid"]
            if payload["state"] == "paid":
                type(self).paid_sync_uuids.append(uuid)
                if not self.aborted_uuid:
                    type(self).aborted_uuid = uuid
                    type(self).abort_count += 1
                    self._websocket_send("Fetch.failRequest", params={"requestId": params["requestId"], "errorReason": "Aborted"})
                    return
        super()._handle_request_paused(**params)

    def _handle_console(self, type, args=None, **kwargs):
        message = args and self._from_remoteobject(args[0])
        if message == "hard reload pending" and not self.reload_count:
            self.__class__.reload_count += 1
            self._websocket_send("Page.reload", params={"ignoreCache": True})
        super()._handle_console(type, args=args, **kwargs)

    def _handle_frame_stopped_loading(self, frameId):
        super()._handle_frame_stopped_loading(frameId)
        if self.reload_count != 1 or self.target_after:
            return
        future = self._websocket_send("Target.getTargetInfo", with_future=True)
        future.add_done_callback(lambda result: setattr(type(self), "target_after", result.result()["targetInfo"]["targetId"]))
        self._websocket_send("Runtime.evaluate", params={"expression": """
            (async () => {
                for (let attempt = 0; attempt < 100 && !document.getElementById('pos-react-data'); attempt++) {
                    await new Promise(resolve => setTimeout(resolve, 100));
                }
                const dataNode = document.getElementById('pos-react-data');
                if (!dataNode) throw new Error('POS bootstrap missing after hard reload');
                const data = JSON.parse(dataNode.textContent);
                const name = `pos-react:${encodeURIComponent(data.tenantId)}:${encodeURIComponent(data.configId)}:${encodeURIComponent(data.userId)}`;
                for (let attempt = 0; attempt < 100; attempt++) {
                    const records = await new Promise((resolve, reject) => {
                        const request = indexedDB.open(name);
                        request.onerror = () => reject(request.error);
                        request.onsuccess = () => {
                            const database = request.result;
                            const result = database.transaction('outbox').objectStore('outbox').getAll();
                            result.onerror = () => reject(result.error);
                            result.onsuccess = () => { database.close(); resolve(result.result); };
                        };
                    });
                    if (!records.length) {
                        console.log('committed sync reload retry succeeded');
                        return;
                    }
                    await new Promise(resolve => setTimeout(resolve, 100));
                }
                throw new Error('startup did not clear outbox');
            })();
        """})


@tagged("post_install", "-at_install")
class TestPosReactBrowser(TestFrontendCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.customer_fiscal_position = cls.env["account.fiscal.position"].create({"name": "POS React customer fiscal position"})
        cls.customer_source_tax = cls.env["account.tax"].create({
            "name": "POS React customer source 10%",
            "type_tax_use": "sale",
            "amount_type": "percent",
            "amount": 10,
        })
        cls.customer_destination_tax = cls.env["account.tax"].create({
            "name": "POS React customer destination 5%",
            "type_tax_use": "sale",
            "amount_type": "percent",
            "amount": 5,
            "fiscal_position_ids": [(6, 0, cls.customer_fiscal_position.ids)],
            "original_tax_ids": [(6, 0, cls.customer_source_tax.ids)],
        })
        cls.customer_product = cls.env["product.product"].create({
            "name": "POS React customer priced product",
            "list_price": 100,
            "available_in_pos": True,
            "taxes_id": cls.customer_source_tax.ids,
        })
        cls.customer_pricelist = cls.env["product.pricelist"].create({
            "name": "POS React customer fixed pricelist",
            "item_ids": [(0, 0, {
                "compute_price": "fixed",
                "fixed_price": 80.02,
                "applied_on": "0_product_variant",
                "product_id": cls.customer_product.id,
            })],
        })
        cls.priced_customer = cls.env["res.partner"].with_company(
            cls.main_pos_config.company_id
        ).create({
            "name": "POS React priced customer",
            "property_account_position_id": cls.customer_fiscal_position.id,
            "property_product_pricelist": cls.customer_pricelist.id,
        })
        cls.main_pos_config.available_pricelist_ids = [(4, cls.customer_pricelist.id)]
        cls.main_pos_config.use_pricelist = True

    def test_realtime_websocket_protocol_and_lifecycle(self):
        self.browser_js(
            f"/pos/react/{self.main_pos_config.id}",
            """
            (() => {
                const check = (condition, message) => { if (!condition) throw new Error(message); };
                const NativeWebSocket = globalThis.WebSocket;
                const nativeSetTimeout = globalThis.setTimeout;
                const nativeClearTimeout = globalThis.clearTimeout;
                const nativeAddEventListener = globalThis.addEventListener;
                const nativeRemoveEventListener = globalThis.removeEventListener;
                const onlineDescriptor = Object.getOwnPropertyDescriptor(navigator, 'onLine');
                const sockets = [];
                const timers = new Map();
                const listeners = new Map();
                let timerId = 0;
                class MockWebSocket {
                    static OPEN = 1;
                    static CLOSING = 2;
                    constructor(url) { this.url = url; this.readyState = 0; this.sent = []; this.closes = []; sockets.push(this); }
                    send(payload) { this.sent.push(JSON.parse(payload)); }
                    close(code) { this.closes.push(code); this.readyState = MockWebSocket.CLOSING; }
                }
                try {
                    Object.defineProperty(navigator, 'onLine', { configurable: true, value: true });
                    globalThis.WebSocket = MockWebSocket;
                    globalThis.setTimeout = (callback, delay) => { const id = ++timerId; timers.set(id, { callback, delay }); return id; };
                    globalThis.clearTimeout = id => timers.delete(id);
                    globalThis.addEventListener = (type, callback) => listeners.set(type, callback);
                    globalThis.removeEventListener = (type, callback) => { if (listeners.get(type) === callback) listeners.delete(type); };

                    const notifications = [];
                    const statuses = [];
                    const client = posReactRealtime.connect({
                        token: 'token-1', version: '19.7 beta', lastId: 4,
                        onSynchronisation: payload => notifications.push(payload),
                        onStatus: status => statuses.push(status),
                    });
                    check(sockets[0].url === `${location.origin.replace(/^http/, 'ws')}/websocket?version=19.7%20beta`, 'versioned websocket URL');
                    sockets[0].readyState = MockWebSocket.OPEN;
                    sockets[0].onopen();
                    check(JSON.stringify(sockets[0].sent[0]) === JSON.stringify({ event_name: 'subscribe', data: { channels: ['token-1'], last: 4 } }), 'subscribe token/last');
                    sockets[0].onmessage({ data: JSON.stringify([
                        { id: 7, message: { type: 'other', payload: 'ignored' } },
                        { id: 9, message: { type: 'token-1-SYNCHRONISATION', payload: { order: 42 } } },
                    ]) });
                    check(client.lastId === 9 && notifications.length === 1 && notifications[0].order === 42, 'notification callback/lastId');
                    try { sockets[0].onmessage({ data: '{malformed' }); } catch {}
                    check(client.lastId === 9 && notifications.length === 1, 'malformed payload must fail closed');

                    sockets[0].readyState = MockWebSocket.CLOSING;
                    sockets[0].onclose();
                    check([...timers.values()][0]?.delay === 1000, 'first reconnect backoff');
                    [...timers.values()][0].callback();
                    check(sockets.length === 2, 'timer reconnect');
                    sockets[1].readyState = MockWebSocket.CLOSING;
                    sockets[1].onclose();
                    check([...timers.values()][0]?.delay === 2000, 'exponential reconnect backoff');
                    timers.clear();
                    listeners.get('online')();
                    check(sockets.length === 3, 'online reconnect');

                    client.close();
                    check(!timers.size && !listeners.has('online') && sockets[2].closes[0] === 1000 && statuses.at(-1) === 'closed', 'close cleanup');
                    console.log('realtime websocket protocol succeeded');
                } finally {
                    globalThis.WebSocket = NativeWebSocket;
                    globalThis.setTimeout = nativeSetTimeout;
                    globalThis.clearTimeout = nativeClearTimeout;
                    globalThis.addEventListener = nativeAddEventListener;
                    globalThis.removeEventListener = nativeRemoveEventListener;
                    if (onlineDescriptor) Object.defineProperty(navigator, 'onLine', onlineDescriptor);
                    else delete navigator.onLine;
                }
            })();
            """,
            "Boolean(globalThis.posReactRealtime)",
            login="pos_user",
            success_signal="realtime websocket protocol succeeded",
        )

    def test_remote_finalization_locks_local_draft(self):
        self.browser_js(
            f"/pos/react/{self.main_pos_config.id}",
            """
            (async () => {
                const check = (condition, message) => { if (!condition) throw new Error(message); };
                const waitFor = async (probe, message) => {
                    for (let attempt = 0; attempt < 150; attempt++) {
                        const value = await probe();
                        if (value) return value;
                        await new Promise(resolve => setTimeout(resolve, 100));
                    }
                    throw new Error(message);
                };
                const product = await waitFor(
                    () => [...document.querySelectorAll('button.product')].find(button => !button.disabled),
                    'product not ready'
                );
                product.click();

                const data = JSON.parse(document.getElementById('pos-react-data').textContent);
                const databaseName = `pos-react:${encodeURIComponent(data.tenantId)}:${encodeURIComponent(data.configId)}:${encodeURIComponent(data.userId)}`;
                const draft = await waitFor(async () => new Promise((resolve, reject) => {
                    const request = indexedDB.open(databaseName);
                    request.onerror = () => reject(request.error);
                    request.onsuccess = () => {
                        const database = request.result;
                        const transaction = database.transaction('drafts');
                        const stored = transaction.objectStore('drafts').get(`${data.tenantId}:${data.configId}:${data.userId}:${data.sessionId}:${data.companyId}`);
                        stored.onerror = () => reject(stored.error);
                        stored.onsuccess = () => { database.close(); resolve(stored.result?.active); };
                    };
                }), 'local draft missing');

                await waitFor(async () => {
                    const response = await posReact.rpc('pos.config', 'read_config_open_orders', [
                        data.configId,
                        { 'pos.order': [['uuid', '=', draft.uuid]] },
                        { 'pos.order': [] },
                    ]);
                    return response.dynamic_records?.['pos.order']?.some(order => order.uuid === draft.uuid && order.state === 'draft');
                }, 'server draft missing');

                await posReact.rpc('pos.order', 'pos_react_sync_from_ui', [[draft]]);
                await new Promise(resolve => setTimeout(resolve, 500));
                check(!document.querySelector('[aria-label="Finalized order"]')?.textContent, 'websocket notification unexpectedly locked draft');
                globalThis.dispatchEvent(new Event('online'));
                const alert = await waitFor(
                    () => document.querySelector('[aria-label="Finalized order"]')?.textContent,
                    'remote finalization alert missing after reconciliation'
                );
                check(alert.includes('finalized on another device'), 'wrong finalization alert');
                check(product.disabled, 'product mutation remained enabled');
                check([...document.querySelectorAll('button')].find(button => button.textContent === 'Pay cash')?.disabled, 'checkout remained enabled');
                console.log('remote finalization lock succeeded');
            })();
            """,
            "Boolean(globalThis.posReact?.rpc)",
            login="pos_user",
            success_signal="remote finalization lock succeeded",
            timeout=90,
        )

    def test_missed_notification_reconciles_when_online(self):
        self.browser_js(
            f"/pos/react/{self.main_pos_config.id}",
            """
            (async () => {
                const check = (condition, message) => { if (!condition) throw new Error(message); };
                const waitFor = async (probe, message) => {
                    for (let attempt = 0; attempt < 150; attempt++) {
                        const value = await probe();
                        if (value) return value;
                        await new Promise(resolve => setTimeout(resolve, 100));
                    }
                    throw new Error(message);
                };
                const product = await waitFor(
                    () => [...document.querySelectorAll('button.product')].find(button => !button.disabled),
                    'product not ready'
                );
                product.click();

                const data = JSON.parse(document.getElementById('pos-react-data').textContent);
                const databaseName = `pos-react:${encodeURIComponent(data.tenantId)}:${encodeURIComponent(data.configId)}:${encodeURIComponent(data.userId)}`;
                const draft = await waitFor(async () => new Promise((resolve, reject) => {
                    const request = indexedDB.open(databaseName);
                    request.onerror = () => reject(request.error);
                    request.onsuccess = () => {
                        const database = request.result;
                        const stored = database.transaction('drafts').objectStore('drafts').get(`${data.tenantId}:${data.configId}:${data.userId}:${data.sessionId}:${data.companyId}`);
                        stored.onerror = () => reject(stored.error);
                        stored.onsuccess = () => { database.close(); resolve(stored.result?.active); };
                    };
                }), 'local draft missing');

                await waitFor(async () => {
                    const response = await posReact.rpc('pos.config', 'read_config_open_orders', [
                        data.configId,
                        { 'pos.order': [['uuid', '=', draft.uuid]] },
                        { 'pos.order': [] },
                    ]);
                    return response.dynamic_records?.['pos.order']?.some(order => order.uuid === draft.uuid && order.state === 'draft');
                }, 'server draft missing');

                const orderIds = await posReact.rpc('pos.order', 'search', [[['uuid', '=', draft.uuid]]]);
                check(orderIds.length === 1, 'server order identity missing');
                await posReact.rpc('pos.order', 'write', [orderIds, { state: 'paid' }]);
                await new Promise(resolve => setTimeout(resolve, 500));
                check(!document.querySelector('[aria-label="Finalized order"]')?.textContent, 'suppressed notification unexpectedly locked draft');

                globalThis.dispatchEvent(new Event('online'));
                const alert = await waitFor(
                    () => document.querySelector('[aria-label="Finalized order"]')?.textContent,
                    'online reconciliation did not detect finalization'
                );
                check(alert.includes('finalized on another device'), 'wrong reconnect alert');
                check(product.disabled, 'product remained enabled after reconnect reconciliation');
                check([...document.querySelectorAll('button')].find(button => button.textContent === 'Pay cash')?.disabled, 'checkout remained enabled after reconnect reconciliation');
                console.log('missed notification reconnect reconciliation succeeded');
            })();
            """,
            "Boolean(globalThis.posReact?.rpc)",
            login="pos_user",
            success_signal="missed notification reconnect reconciliation succeeded",
            timeout=90,
        )

    def test_remote_draft_graph_change_locks_local_draft(self):
        self.browser_js(
            f"/pos/react/{self.main_pos_config.id}",
            """
            (async () => {
                const waitFor = async (probe, message) => {
                    for (let attempt = 0; attempt < 150; attempt++) {
                        const value = await probe();
                        if (value) return value;
                        await new Promise(resolve => setTimeout(resolve, 100));
                    }
                    throw new Error(message);
                };
                const product = await waitFor(
                    () => [...document.querySelectorAll('button.product')].find(button => !button.disabled),
                    'product not ready'
                );
                product.click();
                const data = JSON.parse(document.getElementById('pos-react-data').textContent);
                const orderId = await waitFor(async () => {
                    const ids = await posReact.rpc('pos.order', 'search', [[['session_id', '=', data.sessionId], ['state', '=', 'draft']]]);
                    return ids[0];
                }, 'server draft missing');
                const lineIds = await posReact.rpc('pos.order.line', 'search', [[['order_id', '=', orderId]]]);
                if (lineIds.length !== 1) throw new Error('server line identity missing');
                await posReact.rpc('pos.order.line', 'write', [lineIds, { qty: 7 }]);
                globalThis.dispatchEvent(new Event('online'));
                await waitFor(
                    () => document.querySelector('[aria-label="Finalized order"]')?.textContent,
                    'remote graph change did not lock local draft'
                );
                if (!product.disabled) throw new Error('product remained enabled after remote graph change');
                const databaseName = `pos-react:${encodeURIComponent(data.tenantId)}:${encodeURIComponent(data.configId)}:${encodeURIComponent(data.userId)}`;
                const database = await new Promise((resolve, reject) => { const request = indexedDB.open(databaseName); request.onerror = () => reject(request.error); request.onsuccess = () => resolve(request.result); });
                await new Promise((resolve, reject) => { const transaction = database.transaction('drafts', 'readwrite'); transaction.objectStore('drafts').delete(`${data.tenantId}:${data.configId}:${data.userId}:${data.sessionId}:${data.companyId}`); transaction.oncomplete = resolve; transaction.onerror = () => reject(transaction.error); });
                database.close();
                console.log('remote draft graph conflict lock succeeded');
            })();
            """,
            "Boolean(globalThis.posReact?.rpc)",
            login="pos_user",
            success_signal="remote draft graph conflict lock succeeded",
            timeout=90,
        )

    def test_deleted_server_draft_locks_local_draft(self):
        self.browser_js(
            f"/pos/react/{self.main_pos_config.id}",
            """
            (async () => {
                const waitFor = async (probe, message) => {
                    for (let attempt = 0; attempt < 150; attempt++) {
                        const value = await probe();
                        if (value) return value;
                        await new Promise(resolve => setTimeout(resolve, 100));
                    }
                    throw new Error(message);
                };
                const product = await waitFor(
                    () => [...document.querySelectorAll('button.product')].find(button => !button.disabled),
                    'product not ready'
                );
                product.click();
                const data = JSON.parse(document.getElementById('pos-react-data').textContent);
                const orderId = await waitFor(async () => {
                    const databaseName = `pos-react:${encodeURIComponent(data.tenantId)}:${encodeURIComponent(data.configId)}:${encodeURIComponent(data.userId)}`;
                    const draft = await new Promise((resolve, reject) => {
                        const request = indexedDB.open(databaseName);
                        request.onerror = () => reject(request.error);
                        request.onsuccess = () => {
                            const database = request.result;
                            const stored = database.transaction('drafts').objectStore('drafts').get(`${data.tenantId}:${data.configId}:${data.userId}:${data.sessionId}:${data.companyId}`);
                            stored.onerror = () => reject(stored.error);
                            stored.onsuccess = () => { database.close(); resolve(stored.result?.active); };
                        };
                    });
                    if (!draft) return false;
                    const ids = await posReact.rpc('pos.order', 'search', [[['uuid', '=', draft.uuid]]]);
                    return ids[0];
                }, 'server draft missing');
                await posReact.rpc('pos.order', 'unlink', [[orderId]]);
                globalThis.dispatchEvent(new Event('online'));
                await waitFor(
                    () => document.querySelector('[aria-label="Finalized order"]')?.textContent,
                    'deleted server draft did not lock local draft'
                );
                if (!product.disabled) throw new Error('product remained enabled after server deletion');
                const databaseName = `pos-react:${encodeURIComponent(data.tenantId)}:${encodeURIComponent(data.configId)}:${encodeURIComponent(data.userId)}`;
                const database = await new Promise((resolve, reject) => { const request = indexedDB.open(databaseName); request.onerror = () => reject(request.error); request.onsuccess = () => resolve(request.result); });
                await new Promise((resolve, reject) => { const transaction = database.transaction('drafts', 'readwrite'); transaction.objectStore('drafts').delete(`${data.tenantId}:${data.configId}:${data.userId}:${data.sessionId}:${data.companyId}`); transaction.oncomplete = resolve; transaction.onerror = () => reject(transaction.error); });
                database.close();
                console.log('deleted server draft lock succeeded');
            })();
            """,
            "Boolean(globalThis.posReact?.rpc)",
            login="pos_user",
            success_signal="deleted server draft lock succeeded",
            timeout=90,
        )

    def test_cold_reload_renders_cached_shell_and_catalog(self):
        ColdReloadBrowser.reload_count = 0
        ColdReloadBrowser.blocked_requests = 0
        ColdReloadBrowser.target_before = None
        ColdReloadBrowser.target_after = None
        with patch("odoo.tests.common.ChromeBrowser", ColdReloadBrowser):
            self.browser_js(
                f"/pos/react/{self.main_pos_config.id}",
                """
                (async () => {
                    const registration = await navigator.serviceWorker.ready;
                    if (!registration.active) throw new Error('active POS service worker missing');
                    const navigation = location.href;
                    registration.active.postMessage({ type: 'CACHE_NAVIGATION', url: navigation });
                    for (let attempt = 0; attempt < 100; attempt++) {
                        const cachedNavigation = await caches.match(navigation, { ignoreSearch: false });
                        const cachedApp = await caches.match('/pos_react/static/src/app.js');
                        if (cachedNavigation && cachedApp) {
                            console.log('POS cache ready');
                            return;
                        }
                        await new Promise(resolve => setTimeout(resolve, 100));
                    }
                    throw new Error('POS cache-ready ACK timeout');
                })();
                """,
                "Boolean(document.querySelector('#pos-react-root .product'))",
                login="pos_user",
                success_signal="POS cold reload succeeded",
            )

        self.assertEqual(ColdReloadBrowser.reload_count, 1)
        self.assertGreater(ColdReloadBrowser.blocked_requests, 0)
        self.assertEqual(ColdReloadBrowser.target_after, ColdReloadBrowser.target_before)

    def test_restaurant_table_draft_survives_same_tab_hard_reload(self):
        SameTabDraftReloadBrowser.reload_count = 0
        SameTabDraftReloadBrowser.target_before = None
        SameTabDraftReloadBrowser.target_after = None
        SameTabDraftReloadBrowser.sync_graphs = []
        with patch("odoo.tests.common.ChromeBrowser", SameTabDraftReloadBrowser):
            self.browser_js(
                f"/pos/react/{self.main_pos_config.id}",
                """
                (async () => {
                    const data = JSON.parse(document.getElementById('pos-react-data').textContent);
                    const productIndex = data.products.findIndex(product => !product.taxIds.length);
                    const name = `pos-react:${encodeURIComponent(data.tenantId)}:${encodeURIComponent(data.configId)}:${encodeURIComponent(data.userId)}`;
                    const loadActiveDraft = () => new Promise((resolve, reject) => {
                        const request = indexedDB.open(name);
                        request.onerror = () => reject(request.error);
                        request.onsuccess = () => {
                            const database = request.result;
                            const result = database.transaction('drafts').objectStore('drafts').get(`${data.tenantId}:${data.configId}:${data.userId}:${data.sessionId}:${data.companyId}`);
                            result.onerror = () => reject(result.error);
                            result.onsuccess = () => { database.close(); resolve(result.result?.active); };
                        };
                    });
                    const tableId = data.restaurant?.tables?.[0]?.id;
                    if (!tableId) throw new Error('fresh restaurant table missing');
                    [...document.querySelectorAll('button')].find(button => button.textContent === 'Restaurant').click();
                    let table;
                    let guests;
                    for (let attempt = 0; attempt < 50 && !table; attempt++) {
                        table = document.querySelector('[aria-label="Restaurant table"]');
                        guests = document.querySelector('[aria-label="Guest count"]');
                        await new Promise(resolve => setTimeout(resolve, 20));
                    }
                    if (!table || !guests) throw new Error('restaurant context inputs unavailable');
                    Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype, 'value').set.call(table, String(tableId));
                    table.dispatchEvent(new Event('change', { bubbles: true }));
                    Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set.call(guests, '3');
                    guests.dispatchEvent(new Event('input', { bubbles: true }));
                    await new Promise(resolve => setTimeout(resolve, 0));
                    [...document.querySelectorAll('button')].find(button => button.textContent === 'Back').click();
                    let product;
                    for (let attempt = 0; attempt < 100; attempt++) {
                        product = document.querySelectorAll('.product')[productIndex];
                        if (product && !product.disabled) break;
                        await new Promise(resolve => setTimeout(resolve, 20));
                    }
                    if (!product || product.disabled) throw new Error('product unavailable after restaurant context');
                    product.click();
                    let draft;
                    for (let attempt = 0; attempt < 50; attempt++) {
                        product = document.querySelectorAll('.product')[productIndex];
                        draft = await loadActiveDraft();
                        if (draft?.lines?.[0]?.[2]?.qty === 1 && !product.disabled) break;
                        await new Promise(resolve => setTimeout(resolve, 20));
                    }
                    if (draft?.lines?.[0]?.[2]?.qty !== 1 || product.disabled) throw new Error('first draft quantity not persisted');
                    product.click();
                    for (let attempt = 0; attempt < 50; attempt++) {
                        draft = await loadActiveDraft();
                        if (draft?.lines?.[0]?.[2]?.qty === 2) break;
                        await new Promise(resolve => setTimeout(resolve, 100));
                    }
                    if (draft?.lines?.[0]?.[2]?.qty !== 2) throw new Error('second draft quantity not persisted');
                    sessionStorage.setItem('pos-react-reload-draft', JSON.stringify({
                        orderUuid: draft.uuid,
                        lineUuid: draft.lines[0][2].uuid,
                        tableId,
                        customerCount: 3,
                        total: document.querySelector('aside footer strong:last-child').textContent,
                    }));
                    console.log('same-tab draft reload pending');
                })();
                """,
                "Boolean(document.querySelector('#pos-react-root .product'))",
                login="pos_user",
                success_signal="same-tab draft reload succeeded",
            )

        self.assertEqual(SameTabDraftReloadBrowser.reload_count, 1)
        self.assertEqual(SameTabDraftReloadBrowser.target_after, SameTabDraftReloadBrowser.target_before)
        self.assertEqual(len(SameTabDraftReloadBrowser.sync_graphs), 1)
        graph = SameTabDraftReloadBrowser.sync_graphs[0]
        self.assertEqual(graph["uuid"], graph["pos_reference"])
        self.assertEqual(graph["lines"][0][2]["qty"], 2)
        self.assertTrue(graph["lines"][0][2]["uuid"])
        order = self.env["pos.order"].search([("uuid", "=", graph["uuid"])])
        self.assertEqual(len(order), 1)
        self.assertEqual(len(order.lines), 1)
        self.assertEqual(order.lines.uuid, graph["lines"][0][2]["uuid"])

    def test_sync_retry_after_committed_response_abort(self):
        AbortFirstSyncResponseBrowser.aborted_uuid = None
        AbortFirstSyncResponseBrowser.abort_count = 0
        AbortFirstSyncResponseBrowser.paid_sync_uuids = []
        AbortFirstSyncResponseBrowser.reload_count = 0
        AbortFirstSyncResponseBrowser.target_before = None
        AbortFirstSyncResponseBrowser.target_after = None
        with patch("odoo.tests.common.ChromeBrowser", AbortFirstSyncResponseBrowser):
            self.browser_js(
                f"/pos/react/{self.main_pos_config.id}",
                """
                (async () => {
                const product = [...document.querySelectorAll('.product')].find(
                    item => !JSON.parse(document.getElementById('pos-react-data').textContent).products[
                        [...document.querySelectorAll('.product')].indexOf(item)
                    ].taxIds.length
                );
                for (let attempt = 0; attempt < 100 && product.disabled; attempt++) await new Promise(resolve => setTimeout(resolve, 20));
                product.click();
                let payCash;
                for (let attempt = 0; attempt < 100; attempt++) {
                    payCash = [...document.querySelectorAll('button')].find(button => button.textContent === 'Pay cash');
                    if (payCash && !payCash.disabled) break;
                    await new Promise(resolve => setTimeout(resolve, 20));
                }
                payCash.click();
                payCash.click();
                const initialData = JSON.parse(document.getElementById('pos-react-data').textContent);
                const databaseName = `pos-react:${encodeURIComponent(initialData.tenantId)}:${encodeURIComponent(initialData.configId)}:${encodeURIComponent(initialData.userId)}`;
                const readOutbox = () => new Promise((resolve, reject) => {
                    const request = indexedDB.open(databaseName);
                    request.onerror = () => reject(request.error);
                    request.onsuccess = () => {
                        const database = request.result;
                        const transaction = database.transaction('outbox', 'readonly');
                        const records = transaction.objectStore('outbox').getAll();
                        records.onerror = () => reject(records.error);
                        records.onsuccess = () => { database.close(); resolve(records.result); };
                    };
                });
                const waitForOutbox = async (expected, message) => {
                    for (let attempt = 0; attempt < 50; attempt++) {
                        const records = await readOutbox();
                        if (expected(records)) return records;
                        await new Promise(resolve => setTimeout(resolve, 100));
                    }
                    throw new Error(message);
                };
                const pendingRecords = await waitForOutbox(records => records.length === 1, 'aborted order missing from outbox');
                if (pendingRecords[0].id !== pendingRecords[0].payload.uuid) throw new Error('outbox record does not match aborted UUID');
                if (!document.querySelector('[aria-label="Pending orders"]')) throw new Error('pending orders status missing');
                await new Promise(resolve => setTimeout(resolve, 2100));
                console.log('hard reload pending');
                })();
                """,
                "Boolean(document.querySelector('#pos-react-root .product'))",
                login="pos_user",
                success_signal="committed sync reload retry succeeded",
            )

        self.assertTrue(AbortFirstSyncResponseBrowser.aborted_uuid)
        self.assertEqual(AbortFirstSyncResponseBrowser.abort_count, 1)
        self.assertEqual(AbortFirstSyncResponseBrowser.reload_count, 1)
        self.assertEqual(AbortFirstSyncResponseBrowser.target_after, AbortFirstSyncResponseBrowser.target_before)
        self.assertEqual(AbortFirstSyncResponseBrowser.paid_sync_uuids, [AbortFirstSyncResponseBrowser.aborted_uuid] * 2)
        order = self.env["pos.order"].search([("uuid", "=", AbortFirstSyncResponseBrowser.aborted_uuid)])
        self.assertEqual(len(order), 1)
        self.assertEqual(len(order.lines), 1)
        self.assertEqual(len(order.payment_ids), 1)

    def test_app_retry_lifecycle_respects_deadline(self):
        self.browser_js(
            f"/pos/react/{self.main_pos_config.id}",
            """
            (async () => {
            const nativeFetch = globalThis.fetch;
            let syncCalls = 0;
            globalThis.fetch = (...args) => {
                const body = String(args[1]?.body);
                if (String(args[0]).includes('/api/model/call') && body.includes('pos_react_sync_from_ui')) {
                    const state = JSON.parse(body).params.args[0][0].state;
                    if (state === 'paid' && ++syncCalls === 1) return Promise.reject(new Error('offline once'));
                }
                return nativeFetch(...args);
            };
            const waitFor = async (predicate, timeout, message) => {
                const deadline = Date.now() + timeout;
                while (Date.now() < deadline) {
                    const value = predicate();
                    if (value) return value;
                    await new Promise(resolve => setTimeout(resolve, 20));
                }
                throw new Error(message);
            };
            const product = [...document.querySelectorAll('.product')].find(
                item => !JSON.parse(document.getElementById('pos-react-data').textContent).products[
                    [...document.querySelectorAll('.product')].indexOf(item)
                ].taxIds.length
            );
            await waitFor(() => !product.disabled, 1000, 'draft checkout not ready');
            product.click();
            const payCash = await waitFor(
                () => [...document.querySelectorAll('button')].find(button => button.textContent === 'Pay cash' && !button.disabled),
                1000,
                'draft mutation did not become checkout-ready',
            );
            payCash.click();
            await waitFor(() => document.querySelector('[aria-label="Pending orders"]')?.textContent, 1000, 'pending status missing');
            globalThis.dispatchEvent(new Event('online'));
            await new Promise(resolve => setTimeout(resolve, 100));
            if (syncCalls !== 1) throw new Error('online bypassed retry deadline');
            await waitFor(() => !document.querySelector('.recovery'), 3000, 'retry timer did not drain due order');
            if (syncCalls !== 2) throw new Error(`unexpected sync count: ${syncCalls}`);
            globalThis.fetch = nativeFetch;
            console.log('app retry lifecycle succeeded');
            })();
            """,
            "Boolean(document.querySelector('#pos-react-root .product'))",
            login="pos_user",
            success_signal="app retry lifecycle succeeded",
        )

    def test_offline_store_reconnect_during_failing_drain(self):
        self.browser_js(
            f"/pos/react/{self.main_pos_config.id}",
            """
            (async () => {
            const initialData = JSON.parse(document.getElementById('pos-react-data').textContent);
            const calls = [];
            let resolveFirst;
            const firstSend = new Promise(resolve => { resolveFirst = resolve; });
            const tenantId = `${initialData.tenantId}-drain-test`;
            const databaseName = `pos-react:${encodeURIComponent(tenantId)}:${encodeURIComponent(initialData.configId)}:${encodeURIComponent(initialData.userId)}`;
            const store = posReactOfflineStore.create({
                tenantId,
                configId: initialData.configId,
                userId: initialData.userId,
                sessionId: initialData.sessionId,
                companyId: initialData.companyId,
                send: async (payload) => {
                    calls.push(payload.sequence);
                    if (calls.length === 1) return firstSend;
                    return true;
                },
                isValidAck: Boolean,
            });
            try {
                await store.put({ sequence: 1 }, 'first');
                await store.put({ sequence: 2 }, 'second');
                const activeDrain = store.drain();
                await new Promise(resolve => setTimeout(resolve));
                const reconnectDrain = store.drain();
                if (activeDrain !== reconnectDrain) throw new Error('drain is not single-flight');
                resolveFirst(true);
                await reconnectDrain;
                if (calls.join(',') !== '1,2') throw new Error(`unexpected send order: ${calls}`);
                if ((await store.list()).length) throw new Error('outbox not drained');
            } finally {
                await store.close();
                await new Promise((resolve, reject) => {
                    const request = indexedDB.deleteDatabase(databaseName);
                    request.onsuccess = resolve;
                    request.onerror = () => reject(request.error);
                    request.onblocked = () => reject(new Error(`IndexedDB deletion blocked: ${databaseName}`));
                });
            }
            console.log('offline store queued drain succeeded');
            })();
            """,
            "Boolean(globalThis.posReactOfflineStore)",
            login="pos_user",
            success_signal="offline store queued drain succeeded",
        )

    def test_offline_store_poison_reload_and_payload_tamper(self):
        self.browser_js(
            f"/pos/react/{self.main_pos_config.id}",
            """
            (async () => {
            const initial = JSON.parse(document.getElementById('pos-react-data').textContent);
            const tenantId = `${initial.tenantId}-poison-test`;
            const databaseName = `pos-react:${encodeURIComponent(tenantId)}:${encodeURIComponent(initial.configId)}:${encodeURIComponent(initial.userId)}`;
            const options = {
                tenantId, configId: initial.configId, userId: initial.userId,
                sessionId: initial.sessionId, companyId: initial.companyId,
            };
            const remove = () => new Promise((resolve, reject) => {
                const request = indexedDB.deleteDatabase(databaseName);
                request.onsuccess = resolve;
                request.onerror = () => reject(request.error);
            });
            await remove();
            let store;
            try {
                const sent = [];
                store = posReactOfflineStore.create({
                    ...options,
                    send: async payload => {
                        sent.push(payload.sequence);
                        if (payload.sequence === 1) throw Object.assign(new Error('rejected'), { permanent: true, code: 'ORDER_REJECTED' });
                        return true;
                    },
                });
                await store.put({ sequence: 1 }, 'poison');
                await store.put({ sequence: 2 }, 'valid');
                const initialRecords = await store.list();
                if (initialRecords.some(record => record.status !== 'pending' || record.attempts !== 0 || !record.payloadHash || record.createdAt !== record.updatedAt || record.lastAttemptAt !== null || record.errorCode !== null)) throw new Error('initial record metadata invalid');
                await store.drain();
                if (sent.join(',') !== '1,2') throw new Error(`later record not drained: ${sent}`);
                let records = await store.list();
                if (records.length !== 1 || records[0].id !== 'poison' || records[0].status !== 'blocked' || records[0].attempts !== 1 || records[0].errorCode !== 'ORDER_REJECTED' || !records[0].lastAttemptAt) throw new Error('poison state invalid');
                const immutableHash = records[0].payloadHash;
                await store.close();
                store = posReactOfflineStore.create({ ...options, send: async () => { throw new Error('blocked record sent after reload'); } });
                await store.drain();
                records = await store.list();
                if (records.length !== 1 || records[0].payloadHash !== immutableHash || records[0].attempts !== 1) throw new Error('blocked state not preserved across reload');
                await store.put({ sequence: 3 }, 'tampered');
                const database = await new Promise((resolve, reject) => {
                    const request = indexedDB.open(databaseName);
                    request.onsuccess = () => resolve(request.result);
                    request.onerror = () => reject(request.error);
                });
                const transaction = database.transaction('outbox', 'readwrite');
                const objectStore = transaction.objectStore('outbox');
                const tampered = await new Promise((resolve, reject) => {
                    const request = objectStore.get('tampered');
                    request.onsuccess = () => resolve(request.result);
                    request.onerror = () => reject(request.error);
                });
                tampered.payload.sequence = 999;
                objectStore.put(tampered);
                await new Promise((resolve, reject) => { transaction.oncomplete = resolve; transaction.onerror = reject; });
                database.close();
                await store.drain();
                records = await store.list();
                const blocked = records.find(record => record.id === 'tampered');
                if (!blocked || blocked.status !== 'blocked' || blocked.errorCode !== 'PAYLOAD_TAMPERED' || blocked.payloadHash !== tampered.payloadHash) throw new Error('payload tamper not blocked');
                const exported = await store.exportRecord('tampered');
                if (exported.schemaVersion !== 4 || exported.record.id !== 'tampered' || !exported.proof) throw new Error('recovery export proof missing');
                const expectPreserved = async (attempt, message) => {
                    await attempt().then(() => { throw new Error(`${message} deleted record`); }, () => {});
                    if (!(await store.list()).some(record => record.id === 'tampered')) throw new Error(`${message} did not preserve record`);
                };
                await expectPreserved(() => store.deleteExported('tampered', exported.proof, 'wrong'), 'wrong confirmation');
                await expectPreserved(() => store.deleteExported('other', exported.proof, 'other'), 'other-record deletion');
                await expectPreserved(() => store.deleteExported('tampered', `${exported.proof}bad`, 'tampered'), 'invalid proof');
                const beforeFailedDeletes = JSON.stringify(await store.list());
                await expectPreserved(() => store.deleteExported('tampered', exported.proof, 'wrong'), 'repeated wrong confirmation');
                if (JSON.stringify(await store.list()) !== beforeFailedDeletes) throw new Error('failed deletion mutated outbox');
                await store.put({ sequence: 4 }, 'stale');
                const staleExport = await store.exportRecord('stale');
                const staleDb = await new Promise((resolve, reject) => { const request = indexedDB.open(databaseName); request.onsuccess = () => resolve(request.result); request.onerror = () => reject(request.error); });
                const staleTx = staleDb.transaction('outbox', 'readwrite');
                const staleStore = staleTx.objectStore('outbox');
                const staleRecord = await new Promise((resolve, reject) => { const request = staleStore.get('stale'); request.onsuccess = () => resolve(request.result); request.onerror = () => reject(request.error); });
                staleRecord.status = 'blocked'; staleStore.put(staleRecord);
                await new Promise((resolve, reject) => { staleTx.oncomplete = resolve; staleTx.onerror = reject; }); staleDb.close();
                await store.deleteExported('stale', staleExport.proof, 'stale').then(() => { throw new Error('stale proof deleted record'); }, () => {});
                let releaseSend;
                const sendingStore = posReactOfflineStore.create({ ...options, send: () => new Promise(resolve => { releaseSend = resolve; }) });
                await sendingStore.put({ sequence: 5 }, 'sending');
                const sendingExport = await sendingStore.exportRecord('sending');
                const sendingDrain = sendingStore.drain();
                while (!releaseSend) await new Promise(resolve => setTimeout(resolve, 0));
                await sendingStore.deleteExported('sending', sendingExport.proof, 'sending').then(() => { throw new Error('sending record deleted'); }, () => {});
                releaseSend(true); await sendingDrain; await sendingStore.close();
                await store.deleteExported('tampered', exported.proof, 'tampered');
                if ((await store.list()).some(record => record.id === 'tampered')) throw new Error('proved export was not deletable');
            } finally {
                if (store) await store.close();
                await remove();
            }
            console.log('offline poison isolation succeeded');
            })();
            """,
            "Boolean(globalThis.posReactOfflineStore)",
            login="pos_user",
            success_signal="offline poison isolation succeeded",
        )

    def test_offline_store_v4_draft_kernel(self):
        self.browser_js(
            f"/pos/react/{self.main_pos_config.id}",
            """
            (async () => {
            const initial = JSON.parse(document.getElementById('pos-react-data').textContent);
            const tenantId = `${initial.tenantId}-draft-v4-test`;
            const databaseName = `pos-react:${encodeURIComponent(tenantId)}:${encodeURIComponent(initial.configId)}:${encodeURIComponent(initial.userId)}`;
            const remove = () => new Promise((resolve, reject) => {
                const request = indexedDB.deleteDatabase(databaseName);
                request.onsuccess = resolve;
                request.onerror = () => reject(request.error);
                request.onblocked = () => reject(new Error(`IndexedDB deletion blocked: ${databaseName}`));
            });
            const options = sessionId => ({
                tenantId, configId: initial.configId, userId: initial.userId,
                sessionId, companyId: initial.companyId, send: async () => true, now: () => 1234,
            });
            await remove();
            let store;
            let otherScope;
            try {
                store = posReactOfflineStore.create(options('draft-session'));
                const identity = { uuid: 'payload-uuid', lines: [[0, 0, { uuid: 'line-uuid', qty: 1 }]] };
                await store.saveDraft('active', identity);
                identity.uuid = 'mutated-after-save';
                identity.lines[0][2].uuid = 'mutated-line';
                const loaded = await store.loadDraft('active');
                if (loaded.uuid !== 'payload-uuid' || loaded.lines[0][2].uuid !== 'line-uuid') throw new Error('draft identity mutated after save');
                if (!Object.isFrozen(loaded) || !Object.isFrozen(loaded.lines[0][2])) throw new Error('loaded draft is mutable');
                await store.saveDraft('before-enqueue', { uuid: 'before-enqueue-uuid', lines: [[0, 0, { uuid: 'before-enqueue-line', qty: 1 }]] });
                await store.close();
                store = posReactOfflineStore.create(options('draft-session'));
                if ((await store.loadDraft('active')).uuid !== 'payload-uuid') throw new Error('v4 draft did not survive reload');
                const beforeEnqueue = await store.loadDraft('before-enqueue');
                if (beforeEnqueue?.uuid !== 'before-enqueue-uuid' || beforeEnqueue.lines[0][2].uuid !== 'before-enqueue-line') throw new Error('pre-enqueue crash lost draft graph');
                if ((await store.list()).length) throw new Error('pre-enqueue crash created outbox record');
                const recoveredId = await store.commitDraft('before-enqueue');
                const recovered = (await store.list()).find(({ id }) => id === recoveredId);
                if (recoveredId !== 'before-enqueue-uuid' || recovered?.payload.lines[0][2].uuid !== 'before-enqueue-line') throw new Error('pre-enqueue draft did not recover to stable outbox graph');
                const committedId = await store.commitDraft('active');
                const committed = await store.list();
                const activeRecord = committed.find(({ id }) => id === committedId);
                if (committedId !== 'payload-uuid' || committed.length !== 2 || activeRecord?.id !== activeRecord?.payload.uuid) throw new Error('commit did not use payload UUID');
                if (await store.loadDraft('active')) throw new Error('committed draft retained');

                const duplicate = { uuid: 'payload-uuid', lines: [[0, 0, { uuid: 'duplicate-line', qty: 2 }]] };
                await store.saveDraft('duplicate', duplicate);
                await store.commitDraft('duplicate').then(
                    () => { throw new Error('duplicate commit succeeded'); },
                    error => { if (error.message !== 'Outbox record already exists') throw error; },
                );
                const afterAbort = await store.list();
                const retained = await store.loadDraft('duplicate');
                const original = afterAbort.find(({ id }) => id === 'payload-uuid');
                if (afterAbort.length !== 2 || original?.payload.lines[0][2].uuid !== 'line-uuid' || retained?.lines[0][2].uuid !== 'duplicate-line') throw new Error('duplicate abort was not atomic');

                otherScope = posReactOfflineStore.create(options('other-session'));
                if (await otherScope.loadDraft('duplicate')) throw new Error('draft escaped scope');
                await store.deleteDraft('duplicate');
                if (await store.loadDraft('duplicate')) throw new Error('draft delete failed');
                if ((await store.list()).length !== 2) throw new Error('draft delete changed outbox');
                const database = await new Promise((resolve, reject) => {
                    const request = indexedDB.open(databaseName, 4);
                    request.onsuccess = () => resolve(request.result);
                    request.onerror = () => reject(request.error);
                });
                if (database.version !== 4 || !database.objectStoreNames.contains('drafts')) throw new Error('v4 draft schema missing');
                database.close();
                await store.close();
                store = null;
                await otherScope.close();
                otherScope = null;

                const future = await new Promise((resolve, reject) => {
                    const request = indexedDB.open(databaseName, 5);
                    request.onupgradeneeded = () => request.result.createObjectStore('future').put('preserved', 'marker');
                    request.onsuccess = () => resolve(request.result);
                    request.onerror = () => reject(request.error);
                });
                future.close();
                await posReactOfflineStore.create(options('draft-session')).list().then(
                    () => { throw new Error('downgrade opened incompatible schema'); },
                    error => { if (error.name !== 'VersionError') throw error; },
                );
                const preservedFuture = await new Promise((resolve, reject) => {
                    const request = indexedDB.open(databaseName);
                    request.onsuccess = () => resolve(request.result);
                    request.onerror = () => reject(request.error);
                });
                const marker = await new Promise((resolve, reject) => {
                    const request = preservedFuture.transaction('future').objectStore('future').get('marker');
                    request.onsuccess = () => resolve(request.result);
                    request.onerror = () => reject(request.error);
                });
                preservedFuture.close();
                if (marker !== 'preserved') throw new Error('failed downgrade changed future schema data');
            } finally {
                if (store) await store.close();
                if (otherScope) await otherScope.close();
                await remove();
            }
            console.log('offline store v4 draft kernel succeeded');
            })();
            """,
            "Boolean(globalThis.posReactOfflineStore)",
            login="pos_user",
            success_signal="offline store v4 draft kernel succeeded",
        )

    def test_offline_store_scope_isolation_and_forgery(self):
        self.browser_js(
            f"/pos/react/{self.main_pos_config.id}",
            """
            (async () => {
            const initialData = JSON.parse(document.getElementById('pos-react-data').textContent);
            const tenantId = `${initialData.tenantId}-scope-test`;
            const databaseName = userId => `pos-react:${encodeURIComponent(tenantId)}:${encodeURIComponent(initialData.configId)}:${encodeURIComponent(userId)}`;
            const deleteDatabase = name => new Promise((resolve, reject) => {
                const request = indexedDB.deleteDatabase(name);
                request.onsuccess = resolve;
                request.onerror = () => reject(request.error);
                request.onblocked = () => reject(new Error(`IndexedDB deletion blocked: ${name}`));
            });
            const options = userId => ({
                tenantId, configId: initialData.configId, userId,
                sessionId: initialData.sessionId, companyId: initialData.companyId,
            });
            const firstName = databaseName('first-user');
            const secondName = databaseName('second-user');
            let first;
            let second;
            try {
                await Promise.all([deleteDatabase(firstName), deleteDatabase(secondName)]);
                let sends = 0;
                first = posReactOfflineStore.create({ ...options('first-user'), send: async () => { sends++; return true; } });
                await first.put({ order: 1 }, 'forged');
                const database = await new Promise((resolve, reject) => {
                    const request = indexedDB.open(firstName);
                    request.onsuccess = () => resolve(request.result);
                    request.onerror = () => reject(request.error);
                });
                const transaction = database.transaction('outbox', 'readwrite');
                const store = transaction.objectStore('outbox');
                const record = await new Promise((resolve, reject) => {
                    const request = store.get('forged');
                    request.onsuccess = () => resolve(request.result);
                    request.onerror = () => reject(request.error);
                });
                record.scope.userId = 'second-user';
                store.put(record);
                await new Promise((resolve, reject) => {
                    transaction.oncomplete = resolve;
                    transaction.onerror = () => reject(transaction.error);
                    transaction.onabort = () => reject(transaction.error);
                });
                database.close();
                await first.drain();
                const forged = (await first.list())[0];
                if (sends !== 0 || !forged || forged.status !== 'blocked' || forged.errorCode !== 'SCOPE_MISMATCH') throw new Error('forged record sent or not blocked');
                second = posReactOfflineStore.create({ ...options('second-user'), send: async () => true });
                if ((await second.list()).length !== 0) throw new Error('second user can see first user records');
            } finally {
                if (first) await first.close();
                if (second) await second.close();
                await Promise.all([deleteDatabase(firstName), deleteDatabase(secondName)]);
            }
            console.log('offline store scope isolation succeeded');
            })();
            """,
            "Boolean(globalThis.posReactOfflineStore)",
            login="pos_user",
            success_signal="offline store scope isolation succeeded",
        )

    def test_metadata_cache_upgrade_fallback_and_scope_isolation(self):
        self.browser_js(
            f"/pos/react/{self.main_pos_config.id}",
            """
            (async () => {
            const initial = JSON.parse(document.getElementById('pos-react-data').textContent);
            const name = (tenant, user) => `pos-react:${encodeURIComponent(tenant)}:${encodeURIComponent(initial.configId)}:${encodeURIComponent(user)}`;
            const remove = databaseName => new Promise((resolve, reject) => {
                const request = indexedDB.deleteDatabase(databaseName);
                request.onsuccess = resolve;
                request.onerror = () => reject(request.error);
            });
            const open = (databaseName, version, upgrade) => new Promise((resolve, reject) => {
                const request = indexedDB.open(databaseName, version);
                request.onupgradeneeded = () => upgrade?.(request.result);
                request.onsuccess = () => resolve(request.result);
                request.onerror = () => reject(request.error);
            });
            const tenant = `${initial.tenantId}-metadata-test`;
            const firstName = name(tenant, 'first');
            const secondName = name(tenant, 'second');
            await Promise.all([remove(firstName), remove(secondName)]);
            try {
                const v1 = await open(firstName, 1, database => {
                    const outbox = database.createObjectStore('outbox', { keyPath: 'id' });
                    outbox.createIndex('createdAt', 'createdAt');
                });
                const transaction = v1.transaction('outbox', 'readwrite');
                transaction.objectStore('outbox').put({ id: 'preserved', createdAt: 1 });
                await new Promise((resolve, reject) => { transaction.oncomplete = resolve; transaction.onerror = reject; });
                v1.close();
                const scope = userId => ({ tenantId: tenant, configId: initial.configId, userId, sessionId: initial.sessionId, companyId: initial.companyId });
                const relation = { name: 'id', type: 'integer', compute: false, related: false };
                const data = { 'pos.session': { fields: ['id'], relations: { id: relation } } };
                const fresh = await posReactOfflineStore.loadMetadata(scope('first'), async () => data);
                if (fresh.schemaVersion !== 4 || fresh.models.join() !== 'pos.session' || !fresh.hash) throw new Error('runtime metadata missing');
                const reordered = { 'pos.session': { relations: { id: { related: false, compute: false, type: 'integer', name: 'id' } }, fields: ['id'] } };
                const canonical = await posReactOfflineStore.loadMetadata(scope('first'), async () => reordered);
                if (canonical.hash !== fresh.hash) throw new Error('metadata hash is not canonical');
                const runtimeShapes = [
                    { 'pos.session': { fields: ['id', 'id'], relations: { id: relation } } },
                    { 'pos.session': { fields: [], relations: { id: relation } } },
                    { 'pos.session': { fields: ['id'], relations: { id: { ...relation, model: null, ondelete: false } } } },
                    { 'pos.session': { fields: ['partner_id'], relations: { partner_id: { name: 'partner_id', type: 'many2one', compute: false, related: false, relation: 'res.partner' } } } },
                ];
                for (const value of runtimeShapes) await posReactOfflineStore.loadMetadata(scope('first'), async () => value);
                const malformed = [
                    { 'pos.session': { fields: {}, relations: {} } },
                    { 'pos.session': { fields: ['id'], relations: {} } },
                    { 'pos.session': { fields: ['id'], relations: { other: relation } } },
                    { 'pos.session': { fields: [], relations: { id: { ...relation, compute: 0 } } } },
                    { 'pos.session': { fields: ['partner_id'], relations: { partner_id: { name: 'wrong', type: 'many2one', compute: false, related: false, relation: 'res.partner' } } } },
                    { 'pos.session': { fields: ['partner_id'], relations: { partner_id: { name: 'partner_id', type: 'many2one', compute: 0, related: false, relation: 'res.partner' } } } },
                    { 'pos.session': { fields: ['partner_id'], relations: { partner_id: { name: 'partner_id', type: 'many2one', compute: false, related: false } } } },
                    { 'pos.session': { fields: ['line_ids'], relations: { line_ids: { name: 'line_ids', type: 'one2many', compute: false, related: false, relation: 'pos.line', inverse_name: 1 } } } },
                ];
                for (const [index, value] of malformed.entries()) {
                    await posReactOfflineStore.loadMetadata(scope('first'), async () => value).then(
                        () => { throw new Error(`malformed metadata accepted: ${index}`); },
                        error => { if (error.message !== 'Invalid load_data_params metadata') throw error; },
                    );
                }
                const restored = await posReactOfflineStore.loadMetadata(scope('first'), async () => data);
                const upgraded = await open(firstName);
                const preserved = await new Promise((resolve, reject) => {
                    const request = upgraded.transaction('outbox').objectStore('outbox').get('preserved');
                    request.onsuccess = () => resolve(request.result); request.onerror = reject;
                });
                upgraded.close();
                if (!preserved) throw new Error('v1 outbox lost during v2 upgrade');
                const fallback = await posReactOfflineStore.loadMetadata(scope('first'), async () => { throw new Error('offline'); });
                if (fallback.hash !== restored.hash) throw new Error('metadata fallback mismatch');
                await posReactOfflineStore.loadMetadata(scope('second'), async () => { throw new Error('offline'); }).then(
                    () => { throw new Error('second user read first user metadata'); },
                    error => { if (error.message !== 'Valid cached POS metadata is unavailable') throw error; },
                );
                const otherTenant = { ...scope('first'), tenantId: `${tenant}-other` };
                await posReactOfflineStore.loadMetadata(otherTenant, async () => { throw new Error('offline'); }).then(
                    () => { throw new Error('second tenant read first tenant metadata'); },
                    error => { if (error.message !== 'Valid cached POS metadata is unavailable') throw error; },
                );
            } finally {
                await Promise.all([remove(firstName), remove(secondName), remove(name(`${tenant}-other`, 'first'))]);
            }
            console.log('metadata cache browser tests succeeded');
            })();
            """,
            "Boolean(globalThis.posReactOfflineStore)",
            login="pos_user",
            success_signal="metadata cache browser tests succeeded",
        )

    def test_offline_records_atomic_replace_cleanup_and_fallback(self):
        self.browser_js(
            f"/pos/react/{self.main_pos_config.id}",
            """
            (async () => {
            const initial = JSON.parse(document.getElementById('pos-react-data').textContent);
            const tenantId = `${initial.tenantId}-records-test`;
            const scope = { ...initial, tenantId };
            const databaseName = `pos-react:${encodeURIComponent(tenantId)}:${encodeURIComponent(initial.configId)}:${encodeURIComponent(initial.userId)}`;
            const remove = () => new Promise((resolve, reject) => {
                const request = indexedDB.deleteDatabase(databaseName);
                request.onsuccess = resolve; request.onerror = () => reject(request.error);
            });
            await remove();
            try {
                let calls = [];
                let result = await posReactOfflineStore.loadRecords(scope, async (cursor, idsByModel) => {
                    calls.push([cursor, idsByModel]);
                    return { records: { product: [{ id: 1, name: 'one' }, { id: 2, name: 'two' }], legacy: [{ id: 9 }] }, cursor: 'a', hash: 'catalog' };
                }, { hash: 'catalog' });
                if (result.offline || result.records.product.length !== 2 || result.records.legacy.length !== 1 || calls[0][0] !== null || Object.keys(calls[0][1]).length) throw new Error('initial records invalid');
                result = await posReactOfflineStore.loadRecords(scope, async (cursor, idsByModel) => {
                    calls.push([cursor, idsByModel]);
                    return { records: { product: [{ id: 1, name: 'updated' }] }, deleted: { product: [2] }, cursor: 'b', hash: 'catalog' };
                }, { hash: 'catalog' });
                if (calls[1][0] !== 'a' || calls[1][1].product.slice().sort().join() !== '1,2' || calls[1][1].legacy.join() !== '9' || result.records.product.length !== 1 || result.records.product[0].name !== 'updated') throw new Error('upsert cleanup invalid');
                result = await posReactOfflineStore.loadRecords(scope, async (cursor, idsByModel) => {
                    calls.push([cursor, idsByModel]);
                    return { records: { product: [{ id: 3, name: 'replacement' }] }, replace: ['product'], cursor: 'c', hash: 'catalog-v2' };
                }, { hash: 'catalog-v2' });
                if (calls[2][0] !== null || Object.keys(calls[2][1]).length || result.records.product.length !== 1 || result.records.product[0].id !== 3 || result.records.legacy) throw new Error('hash replacement did not remove old models');
                result = await posReactOfflineStore.loadRecords(scope, async () => { throw new Error('offline'); }, { hash: 'catalog-v2' });
                if (!result.offline || result.cursor !== 'c' || result.records.product[0].id !== 3) throw new Error('offline fallback invalid');
                await posReactOfflineStore.loadRecords(scope, async () => { throw new Error('offline'); }, { hash: 'catalog-v3' }).then(
                    () => { throw new Error('offline hash mismatch accepted cached records'); },
                    error => { if (error.message !== 'POS records hash mismatch') throw error; },
                );
                await posReactOfflineStore.loadRecords(scope, async () => ({ records: { product: [{ id: 4 }, { id: 4 }] }, cursor: 'bad' }), {}).then(
                    () => { throw new Error('duplicate records accepted'); },
                    error => { if (!error.message.startsWith('Invalid POS records delta:')) throw error; },
                );
                const fallback = await posReactOfflineStore.loadRecords(scope, async () => { throw new Error('offline'); }, { hash: 'catalog-v2' });
                if (fallback.cursor !== 'c' || fallback.records.product[0].id !== 3) throw new Error('invalid delta was not atomic');
            } finally {
                await remove();
            }
            console.log('offline records browser tests succeeded');
            })();
            """,
            "Boolean(globalThis.posReactOfflineStore?.loadRecords)",
            login="pos_user",
            success_signal="offline records browser tests succeeded",
        )

    def test_fiscal_position_tax_mapping_persists_source_tax(self):
        fiscal_position = self.env["account.fiscal.position"].create({"name": "POS React mapped tax"})
        source_tax = self.env["account.tax"].create({
            "name": "POS React source 10%",
            "type_tax_use": "sale",
            "amount_type": "percent",
            "amount": 10,
        })
        destination_tax = self.env["account.tax"].create({
            "name": "POS React destination 5%",
            "type_tax_use": "sale",
            "amount_type": "percent",
            "amount": 5,
            "fiscal_position_ids": [(6, 0, fiscal_position.ids)],
            "original_tax_ids": [(6, 0, source_tax.ids)],
        })
        product = self.env["product.product"].create({
            "name": "POS React fiscal-position product",
            "list_price": 100,
            "available_in_pos": True,
            "taxes_id": source_tax.ids,
        })
        self.main_pos_config.default_fiscal_position_id = fiscal_position
        amounts = destination_tax.compute_all(product.list_price, product=product)
        expected = {
            "product_id": product.id,
            "product_name": product.name,
            "source_tax_id": source_tax.id,
            "subtotal": amounts["total_excluded"],
            "tax": amounts["total_included"] - amounts["total_excluded"],
            "total": amounts["total_included"],
        }
        self.browser_js(
            f"/pos/react/{self.main_pos_config.id}",
            f"""
            (async () => {{
                const expected = {json.dumps(expected)};
                const check = (condition, message) => {{ if (!condition) throw new Error(message); }};
                const waitFor = async (probe, message) => {{
                    for (let attempt = 0; attempt < 300; attempt++) {{
                        const value = await probe();
                        if (value) return value;
                        await new Promise(resolve => setTimeout(resolve, 100));
                    }}
                    throw new Error(message);
                }};
                const data = JSON.parse(document.getElementById('pos-react-data').textContent);
                const product = await waitFor(
                    () => [...document.querySelectorAll('button.product')].find(button => !button.disabled && button.querySelector('strong')?.textContent === expected.product_name),
                    'mapped-tax product unavailable',
                );
                product.click();
                const payCash = await waitFor(
                    () => [...document.querySelectorAll('button')].find(button => button.textContent === 'Pay cash' && !button.disabled),
                    'Pay cash unavailable',
                );
                payCash.click();
                const order = await waitFor(async () => {{
                    const orders = await posReact.rpc('pos.order', 'search_read', [[
                        ['session_id', '=', data.sessionId], ['state', '=', 'paid'], ['lines.product_id', '=', expected.product_id],
                    ], ['lines', 'amount_tax', 'amount_total'], 0, 1, 'id desc']);
                    return orders[0];
                }}, 'paid mapped-tax order missing');
                const lines = await posReact.rpc('pos.order.line', 'search_read', [[['id', 'in', order.lines]], ['product_id', 'tax_ids', 'price_subtotal', 'price_subtotal_incl']]);
                const line = lines.find(line => line.product_id[0] === expected.product_id);
                check(line?.tax_ids.length === 1 && line.tax_ids[0] === expected.source_tax_id, `persisted source tax mismatch: ${{JSON.stringify(line)}}`);
                check(line.price_subtotal === expected.subtotal && line.price_subtotal_incl === expected.total, 'persisted mapped line totals mismatch');
                check(order.amount_tax === expected.tax && order.amount_total === expected.total, 'persisted mapped order totals mismatch');
                await waitFor(() => !document.querySelector('aside .line') && [...document.querySelectorAll('button')].some(button => button.textContent === 'Pay cash' && button.disabled), 'mapped-tax checkout did not settle');
                console.log('POS React fiscal-position tax mapping succeeded');
            }})();
            """,
            "Boolean(document.querySelector('#pos-react-root .product') || document.querySelector('#pos-react-root[role=alert]'))",
            login="pos_user",
            success_signal="POS React fiscal-position tax mapping succeeded",
        )

    def test_customer_fixed_pricelist_fiscal_position_browser_oracle(self):
        fiscal_position = self.customer_fiscal_position
        source_tax = self.customer_source_tax
        destination_tax = self.customer_destination_tax
        product = self.customer_product
        pricelist = self.customer_pricelist
        customer = self.priced_customer.with_company(self.main_pos_config.company_id)
        self.pos_admin.group_ids += self.env.ref("base.group_partner_manager")
        self.authenticate("pos_admin", "pos_admin")
        self.make_jsonrpc_request("/api/model/call", {
            "model": "res.partner",
            "method": "write",
            "args": [[customer.id], {"property_product_pricelist": pricelist.id}],
            "kwargs": {},
        })
        self.assertEqual(customer.property_product_pricelist, pricelist)
        self.assertEqual(customer.fiscal_position_id, fiscal_position)
        loaded_partner = self.env["res.partner"].with_company(
            self.main_pos_config.company_id
        )._load_pos_data_read(customer, self.main_pos_config)[0]
        self.assertEqual(loaded_partner["property_product_pricelist"], pricelist.id)
        self.assertEqual(loaded_partner["fiscal_position_id"], fiscal_position.id)
        account = self.env["account.account"].create({
            "name": "POS React composite rounding",
            "code": "PRCR",
            "account_type": "expense",
        })
        rounding = self.env["account.cash.rounding"].create({
            "name": "POS React composite 0.05 nearest",
            "rounding": 0.05,
            "rounding_method": "HALF-UP",
            "strategy": "add_invoice_line",
            "profit_account_id": account.id,
            "loss_account_id": account.id,
        })
        self.main_pos_config.write({
            "cash_rounding": True,
            "only_round_cash_method": True,
            "rounding_method": rounding.id,
        })
        currency = self.env.company.currency_id
        format_money = lambda amount: f"{currency.symbol}{amount:.2f}" if currency.position == "before" else f"{amount:.2f} {currency.symbol}"
        expected = {
            "customer_id": customer.id,
            "product_id": product.id,
            "product_name": product.name,
            "pricelist_id": pricelist.id,
            "fiscal_position_id": fiscal_position.id,
            "source_tax_id": source_tax.id,
            "price": 80.02,
            "tax": 4,
            "total": destination_tax.compute_all(80.02, product=product)["total_included"],
            "paid": 84,
            "formatted_price": format_money(80.02),
            "formatted_total": format_money(84.02),
        }
        self.browser_js(
            f"/pos/react/{self.main_pos_config.id}",
            f"""
            (async () => {{
                const expected = {json.dumps(expected)};
                const check = (condition, message) => {{ if (!condition) throw new Error(message); }};
                const waitFor = async (probe, message) => {{
                    for (let attempt = 0; attempt < 300; attempt++) {{
                        const value = await probe();
                        if (value) return value;
                        await new Promise(resolve => setTimeout(resolve, 100));
                    }}
                    throw new Error(message);
                }};
                const data = JSON.parse(document.getElementById('pos-react-data').textContent);
                const customer = document.querySelector('select[aria-label="Customer"]');
                Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype, 'value').set.call(customer, String(expected.customer_id));
                customer.dispatchEvent(new Event('change', {{ bubbles: true }}));
                const product = await waitFor(
                    () => [...document.querySelectorAll('button.product')].find(button => !button.disabled && button.querySelector('strong')?.textContent === expected.product_name && button.querySelector('span')?.textContent === expected.formatted_price),
                    `customer fixed price missing from UI: ${{JSON.stringify({{ customers: [...document.querySelectorAll('select[aria-label="Customer"] option')].map(option => [option.value, option.textContent]), products: [...document.querySelectorAll('button.product')].map(button => [button.querySelector('strong')?.textContent, button.querySelector('span')?.textContent, button.disabled]), partner: (() => {{ const value = posReact.metadataGraph.get('res.partner', expected.customer_id); const raw = posReact.catalog.records['res.partner']?.find(item => item.id === expected.customer_id); return [value?.id, value?.property_product_pricelist?.id, value?.fiscal_position_id?.id, raw?.property_product_pricelist, raw?.fiscal_position_id]; }})(), pricelist: (() => {{ const value = posReact.metadataGraph.get('product.pricelist', expected.pricelist_id); const product = posReact.metadataGraph.get('product.product', expected.product_id); return [value?.id, value?.item_ids?.map(item => [item.id, item.product_id?.id, item.fixed_price]), [product?.id, product?.lst_price, product?.product_tmpl_id?.id], PosReactPricelistEngine.computePrice({{ id: product?.id, lst_price: product?.lst_price, product_tmpl_id: product?.product_tmpl_id }}, value, 1)]; }})() }})}}`,
                );
                product.click();
                await waitFor(() => document.querySelector('aside footer strong:last-child')?.textContent === expected.formatted_total, 'customer fiscal tax total missing from UI');
                const payCash = await waitFor(() => [...document.querySelectorAll('button')].find(button => button.textContent === 'Pay cash' && !button.disabled), 'Pay cash unavailable');
                payCash.click();
                const order = await waitFor(async () => {{
                    const orders = await posReact.rpc('pos.order', 'search_read', [[
                        ['session_id', '=', data.sessionId], ['state', '=', 'paid'], ['lines.product_id', '=', expected.product_id],
                    ], ['lines', 'partner_id', 'pricelist_id', 'fiscal_position_id', 'amount_tax', 'amount_total', 'amount_paid', 'payment_ids'], 0, 1, 'id desc']);
                    return orders[0];
                }}, 'paid customer order missing');
                const [line] = await posReact.rpc('pos.order.line', 'search_read', [[['id', 'in', order.lines]], ['product_id', 'tax_ids', 'price_unit', 'price_subtotal', 'price_subtotal_incl']]);
                const [payment] = await posReact.rpc('pos.payment', 'search_read', [[['id', 'in', order.payment_ids]], ['amount']]);
                check(order.partner_id[0] === expected.customer_id, `persisted partner mismatch: ${{JSON.stringify(order)}}`);
                check(order.pricelist_id[0] === expected.pricelist_id, `persisted pricelist mismatch: ${{JSON.stringify(order)}}`);
                check(order.fiscal_position_id[0] === expected.fiscal_position_id, `persisted fiscal position mismatch: ${{JSON.stringify(order)}}`);
                check(line.product_id[0] === expected.product_id && line.price_unit === expected.price, `persisted fixed price mismatch: ${{JSON.stringify(line)}}`);
                check(line.tax_ids.length === 1 && line.tax_ids[0] === expected.source_tax_id, `persisted source tax mismatch: ${{JSON.stringify(line)}}`);
                check(line.price_subtotal === expected.price && line.price_subtotal_incl === expected.total, `persisted serialized line totals mismatch: ${{JSON.stringify(line)}}`);
                check(order.amount_tax === expected.tax && order.amount_total === expected.total && order.amount_paid === expected.paid && payment.amount === expected.paid, `persisted composite money mismatch: ${{JSON.stringify({{ order, payment }})}}`);
                console.log('POS React customer pricelist fiscal position succeeded');
            }})();
            """,
            "Boolean(document.querySelector('#pos-react-root').textContent)",
            login="pos_user",
            success_signal="POS React customer pricelist fiscal position succeeded",
        )

    def test_taxed_checkout_persists_server_tax_totals(self):
        excluded_tax, included_tax = self.env["account.tax"].create([{
            "name": "POS React excluded 10%",
            "type_tax_use": "sale",
            "amount_type": "percent",
            "amount": 10,
        }, {
            "name": "POS React included 20%",
            "type_tax_use": "sale",
            "amount_type": "percent",
            "amount": 20,
            "price_include_override": "tax_included",
        }])
        excluded_product, included_product = self.env["product.product"].create([{
            "name": "POS React tax excluded",
            "list_price": 100,
            "available_in_pos": True,
            "taxes_id": excluded_tax.ids,
        }, {
            "name": "POS React tax included",
            "list_price": 120,
            "available_in_pos": True,
            "taxes_id": included_tax.ids,
        }])
        expected_lines = {
            excluded_product.id: excluded_tax.compute_all(100, product=excluded_product),
            included_product.id: included_tax.compute_all(120, product=included_product),
        }
        expected = {
            "products": [{"id": excluded_product.id, "name": excluded_product.name}, {"id": included_product.id, "name": included_product.name}],
            "lines": {
                str(product_id): {
                    "subtotal": amounts["total_excluded"],
                    "total": amounts["total_included"],
                }
                for product_id, amounts in expected_lines.items()
            },
            "tax": sum(amounts["total_included"] - amounts["total_excluded"] for amounts in expected_lines.values()),
            "total": sum(amounts["total_included"] for amounts in expected_lines.values()),
        }
        self.browser_js(
            f"/pos/react/{self.main_pos_config.id}",
            f"""
            (async () => {{
                const expected = {json.dumps(expected)};
                const check = (condition, message) => {{ if (!condition) throw new Error(message); }};
                const waitFor = async (condition, message) => {{
                    for (let attempt = 0; attempt < 300; attempt++) {{
                        const value = await condition();
                        if (value) return value;
                        await new Promise(resolve => setTimeout(resolve, 100));
                    }}
                    throw new Error(message);
                }};
                const data = JSON.parse(document.getElementById('pos-react-data').textContent);
                while (document.querySelector('aside .line')) {{
                    const count = document.querySelectorAll('aside .line').length;
                    document.querySelector('aside .line button').click();
                    await waitFor(() => document.querySelectorAll('aside .line').length < count && [...document.querySelectorAll('button.product')].every((button) => !button.disabled), 'existing cart cleanup did not settle');
                }}
                for (const expectedProduct of expected.products) {{
                    const product = await waitFor(
                        () => [...document.querySelectorAll('.product')].find(node => !node.disabled && node.querySelector('strong')?.textContent === expectedProduct.name),
                        `product ${{expectedProduct.id}} missing or disabled`,
                    );
                    check(product.isConnected, `product ${{expectedProduct.id}} detached before click`);
                    product.click();
                    await waitFor(
                        () => [...document.querySelectorAll('aside .line')].some((line) => line.textContent.includes(`${{expectedProduct.name}} × 1`)),
                        `product ${{expectedProduct.id}} cart mutation did not settle: ${{document.querySelector('[aria-label="Recovery error"]')?.textContent || 'no recovery error'}}; connected=${{product.isConnected}}; disabled=${{product.disabled}}; cart=${{[...document.querySelectorAll('aside .line')].map((line) => line.textContent).join('|')}}`,
                    );
                }}
                const payCash = await waitFor(
                    () => [...document.querySelectorAll('button')].find(button => button.textContent === 'Pay cash' && !button.disabled),
                    `Pay cash unavailable: button=${{[...document.querySelectorAll('button')].find(button => button.textContent === 'Pay cash')?.outerHTML}}; error=${{document.querySelector('[aria-label="Recovery error"]')?.textContent}}; finalized=${{document.querySelector('[aria-label="Finalized order"]')?.textContent}}; cart=${{[...document.querySelectorAll('aside .line')].map(line => line.textContent).join('|')}}; total=${{document.querySelector('aside footer')?.textContent}}`,
                );
                payCash.click();
                const order = await waitFor(async () => {{
                    const orders = await posReact.rpc('pos.order', 'search_read', [[
                        ['session_id', '=', data.sessionId], ['state', '=', 'paid'], ['lines.product_id', 'in', expected.products.map(product => product.id)],
                    ], ['id', 'lines', 'amount_tax', 'amount_total'], 0, 1, 'id desc']);
                    return orders[0];
                }}, 'paid taxed order missing');
                const lines = await posReact.rpc('pos.order.line', 'search_read', [[['id', 'in', order.lines]], ['product_id', 'price_subtotal', 'price_subtotal_incl']]);
                check(lines.length === 2, `persisted line count mismatch: ${{JSON.stringify(lines)}}`);
                for (const line of lines) {{
                    const amounts = expected.lines[line.product_id[0]];
                    check(amounts && line.price_subtotal === amounts.subtotal, 'persisted excluded total mismatch');
                    check(line.price_subtotal_incl === amounts.total, 'persisted included total mismatch');
                }}
                check(order.amount_tax === expected.tax, 'persisted order tax mismatch');
                check(order.amount_total === expected.total, 'persisted order total mismatch');
                await waitFor(() => !document.querySelector('aside .line') && [...document.querySelectorAll('button')].some(button => button.textContent === 'Pay cash' && button.disabled), 'taxed checkout did not settle');
                console.log('POS React taxed checkout succeeded');
            }})();
            """,
            "Boolean(document.querySelector('#pos-react-root .product') || document.querySelector('#pos-react-root[role=alert]'))",
            login="pos_user",
            success_signal="POS React taxed checkout succeeded",
        )

    def test_global_rounding_checkout_persists_tax_totals(self):
        self.env.company.tax_calculation_rounding_method = "round_globally"
        tax = self.env["account.tax"].create({
            "name": "POS React global rounding 10%",
            "type_tax_use": "sale",
            "amount_type": "percent",
            "amount": 10,
        })
        products = self.env["product.product"].create([{
            "name": f"POS React global rounding {index}",
            "list_price": 0.05,
            "available_in_pos": True,
            "taxes_id": tax.ids,
        } for index in range(3)])
        currency = self.env.company.currency_id
        raw_amounts = [tax._get_tax_details(
            product.list_price,
            1,
            precision_rounding=currency.rounding,
            rounding_method="round_globally",
            product=product,
        ) for product in products]
        expected_tax = currency.round(sum(
            amounts["total_included"] - amounts["total_excluded"]
            for amounts in raw_amounts
        ))
        expected_total = currency.round(sum(amounts["total_included"] for amounts in raw_amounts))
        self.assertEqual((expected_tax, expected_total), (0.02, 0.17))
        expected = {
            "products": [{"id": product.id, "name": product.name} for product in products],
            "tax_id": tax.id,
            "subtotal": currency.round(sum(amounts["total_excluded"] for amounts in raw_amounts)),
            "tax": expected_tax,
            "total": expected_total,
        }
        self.browser_js(
            f"/pos/react/{self.main_pos_config.id}",
            f"""
            (async () => {{
                const expected = {json.dumps(expected)};
                const check = (condition, message) => {{ if (!condition) throw new Error(message); }};
                const waitFor = async (condition, message) => {{
                    for (let attempt = 0; attempt < 300; attempt++) {{
                        const value = await condition();
                        if (value) return value;
                        await new Promise(resolve => setTimeout(resolve, 100));
                    }}
                    throw new Error(message);
                }};
                const data = JSON.parse(document.getElementById('pos-react-data').textContent);
                while (document.querySelector('aside .line')) {{
                    const count = document.querySelectorAll('aside .line').length;
                    document.querySelector('aside .line button').click();
                    await waitFor(() => document.querySelectorAll('aside .line').length < count && [...document.querySelectorAll('button.product')].every(button => !button.disabled), 'existing cart cleanup did not settle');
                }}
                for (const expectedProduct of expected.products) {{
                    const product = await waitFor(
                        () => [...document.querySelectorAll('.product')].find(node => !node.disabled && node.querySelector('strong')?.textContent === expectedProduct.name),
                        `product ${{expectedProduct.id}} missing or disabled`,
                    );
                    check(product.isConnected, `product ${{expectedProduct.id}} detached before click`);
                    product.click();
                    await waitFor(
                        () => [...document.querySelectorAll('aside .line')].some(line => line.textContent.includes(`${{expectedProduct.name}} × 1`)),
                        `product ${{expectedProduct.id}} cart mutation did not settle: ${{document.querySelector('[aria-label="Recovery error"]')?.textContent || 'no recovery error'}}; connected=${{product.isConnected}}; disabled=${{product.disabled}}; cart=${{[...document.querySelectorAll('aside .line')].map(line => line.textContent).join('|')}}`,
                    );
                }}
                const payCash = await waitFor(
                    () => [...document.querySelectorAll('button')].find(button => button.textContent === 'Pay cash' && !button.disabled),
                    `Pay cash unavailable: button=${{[...document.querySelectorAll('button')].find(button => button.textContent === 'Pay cash')?.outerHTML}}; error=${{document.querySelector('[aria-label="Recovery error"]')?.textContent}}; finalized=${{document.querySelector('[aria-label="Finalized order"]')?.textContent}}; cart=${{[...document.querySelectorAll('aside .line')].map(line => line.textContent).join('|')}}; total=${{document.querySelector('aside footer')?.textContent}}`,
                );
                payCash.click();
                const order = await waitFor(async () => {{
                    const orders = await posReact.rpc('pos.order', 'search_read', [[
                        ['session_id', '=', data.sessionId], ['state', '=', 'paid'], ['lines.product_id', 'in', expected.products.map(product => product.id)],
                    ], ['id', 'lines', 'amount_tax', 'amount_total'], 0, 1, 'id desc']);
                    return orders[0];
                }}, 'paid global-rounding order missing');
                const lines = await posReact.rpc('pos.order.line', 'search_read', [[['id', 'in', order.lines]], ['product_id', 'tax_ids', 'price_subtotal', 'price_subtotal_incl']]);
                const sourceTaxLines = lines.filter(line => line.tax_ids.length === 1 && line.tax_ids[0] === expected.tax_id);
                check(sourceTaxLines.length === 3, `persisted source-tax line count mismatch: ${{JSON.stringify(lines)}}`);
                const lineSubtotal = sourceTaxLines.reduce((sum, line) => sum + line.price_subtotal, 0);
                const lineTotal = sourceTaxLines.reduce((sum, line) => sum + line.price_subtotal_incl, 0);
                check(Math.abs(lineSubtotal - expected.subtotal) < 1e-9, `summed line subtotal mismatch: ${{lineSubtotal}}`);
                check(Math.abs(lineTotal - expected.total) < 1e-9, `summed line total mismatch: ${{lineTotal}}`);
                check(Math.abs(lineTotal - lineSubtotal - expected.tax) < 1e-9, `summed line tax mismatch: ${{lineTotal - lineSubtotal}}`);
                check(order.amount_tax === expected.tax && order.amount_total === expected.total, `persisted global-rounding order totals mismatch: ${{JSON.stringify(order)}}`);
                await waitFor(() => !document.querySelector('aside .line') && [...document.querySelectorAll('button')].some(button => button.textContent === 'Pay cash' && button.disabled), 'global-rounding checkout did not settle');
                console.log('POS React global rounding checkout succeeded');
            }})();
            """,
            "Boolean(document.querySelector('#pos-react-root .product') || document.querySelector('#pos-react-root[role=alert]'))",
            login="pos_user",
            success_signal="POS React global rounding checkout succeeded",
        )

    def test_concurrent_refund_rpc_browser_oracle(self):
        self.browser_js(
            f"/pos/react/{self.main_pos_config.id}",
            """
            (async () => {
                const waitFor = async (probe, message) => {
                    for (let attempt = 0; attempt < 200; attempt++) {
                        const value = await probe();
                        if (value) return value;
                        await new Promise(resolve => setTimeout(resolve, 100));
                    }
                    throw new Error(message);
                };
                const product = await waitFor(() => [...document.querySelectorAll('button.product')].find(button => !button.disabled), 'product unavailable');
                product.click();
                (await waitFor(() => [...document.querySelectorAll('button')].find(button => button.textContent === 'Pay cash' && !button.disabled), 'cash checkout unavailable')).click();
                const sale = await waitFor(async () => (await posReact.rpc('pos.order', 'search_read', [[['is_refund', '=', false], ['state', '=', 'paid']], ['session_id', 'company_id', 'lines', 'payment_ids'], 0, 1, 'id desc']))[0], 'sale missing');
                const [line] = await posReact.rpc('pos.order.line', 'read', [sale.lines, ['product_id', 'price_unit', 'price_subtotal', 'price_subtotal_incl', 'tax_ids']]);
                const [payment] = await posReact.rpc('pos.payment', 'read', [sale.payment_ids, ['payment_method_id']]);
                const refund = () => {
                    const uuid = crypto.randomUUID();
                    return {
                        uuid, access_token: uuid, name: '/', pos_reference: uuid,
                        session_id: sale.session_id[0], company_id: sale.company_id[0], state: 'paid', is_refund: true,
                        amount_paid: -line.price_subtotal_incl, amount_total: -line.price_subtotal_incl,
                        amount_tax: line.price_subtotal - line.price_subtotal_incl, amount_return: 0,
                        lines: [[0, 0, {
                            uuid: crypto.randomUUID(), product_id: line.product_id[0], qty: -1,
                            price_unit: line.price_unit, price_subtotal: -line.price_subtotal,
                            price_subtotal_incl: -line.price_subtotal_incl, discount: 0,
                            tax_ids: [[6, 0, line.tax_ids]], refunded_orderline_id: sale.lines[0],
                        }]],
                        payment_ids: [[0, 0, {
                            uuid: crypto.randomUUID(), payment_method_id: payment.payment_method_id[0],
                            amount: -line.price_subtotal_incl,
                        }]],
                    };
                };
                const outcomes = await Promise.allSettled([
                    posReact.rpc('pos.order', 'pos_react_sync_from_ui', [[refund()]]),
                    posReact.rpc('pos.order', 'pos_react_sync_from_ui', [[refund()]]),
                ]);
                const [source] = await posReact.rpc('pos.order.line', 'read', [[sale.lines[0]], ['refunded_qty']]);
                if (outcomes.filter(result => result.status === 'fulfilled').length !== 1 || outcomes.filter(result => result.status === 'rejected').length !== 1 || source.refunded_qty !== 1) {
                    throw new Error(`concurrent refund mismatch: ${JSON.stringify({ outcomes: outcomes.map(result => result.status), source })}`);
                }
                console.log('POS React concurrent refund RPC succeeded');
            })();
            """,
            "Boolean(document.querySelector('#pos-react-root .product') || document.querySelector('#pos-react-root[role=alert]'))",
            login="pos_user",
            success_signal="POS React concurrent refund RPC succeeded",
            timeout=90,
        )

    def test_partial_cash_refund_browser_oracle(self):
        self.browser_js(
            f"/pos/react/{self.main_pos_config.id}",
            """
            (async () => {
                const waitFor = async (probe, message) => {
                    for (let attempt = 0; attempt < 200; attempt++) {
                        const value = await probe();
                        if (value) return value;
                        await new Promise(resolve => setTimeout(resolve, 100));
                    }
                    throw new Error(message);
                };
                const product = await waitFor(() => [...document.querySelectorAll('button.product')].find(button => !button.disabled), 'product unavailable');
                product.click();
                await waitFor(() => !product.disabled && document.querySelector('aside .line')?.textContent.includes('× 1'), 'first quantity unavailable');
                product.click();
                await waitFor(() => document.querySelector('aside .line')?.textContent.includes('× 2'), 'second quantity unavailable');
                (await waitFor(() => [...document.querySelectorAll('button')].find(button => button.textContent === 'Pay cash' && !button.disabled), 'cash checkout unavailable')).click();
                const refundButton = await waitFor(() => [...document.querySelectorAll('button')].find(button => button.textContent === 'Refund cash' && !button.disabled), 'refund unavailable');
                refundButton.click();
                await waitFor(() => document.querySelector('[aria-label="Refund quantity"]')?.value === '1', 'refund quantity missing');
                (await waitFor(() => [...document.querySelectorAll('button')].find(button => button.textContent === 'Confirm cash refund' && !button.disabled), 'refund confirmation unavailable')).click();
                const refund = await waitFor(async () => (await posReact.rpc('pos.order', 'search_read', [[['is_refund', '=', true]], ['amount_total', 'amount_paid', 'lines', 'payment_ids'], 0, 1, 'id desc']))[0], 'refund order missing');
                const [line] = await posReact.rpc('pos.order.line', 'read', [refund.lines, ['qty', 'refunded_orderline_id']]);
                const [payment] = await posReact.rpc('pos.payment', 'read', [refund.payment_ids, ['amount']]);
                if (line.qty !== -1 || !line.refunded_orderline_id || refund.amount_total >= 0 || refund.amount_paid !== refund.amount_total || payment.amount !== refund.amount_total) throw new Error(`partial refund persistence mismatch: ${JSON.stringify({ refund, line, payment })}`);
                console.log('POS React partial cash refund succeeded');
            })();
            """,
            "Boolean(document.querySelector('#pos-react-root .product') || document.querySelector('#pos-react-root[role=alert]'))",
            login="pos_user",
            success_signal="POS React partial cash refund succeeded",
            timeout=90,
        )

    def test_cash_only_rounding_persists_payment_delta(self):
        account = self.env["account.account"].create({
            "name": "POS React cash rounding",
            "code": "PCR",
            "account_type": "expense",
        })
        rounding = self.env["account.cash.rounding"].create({
            "name": "POS React 0.05 nearest",
            "rounding": 0.05,
            "rounding_method": "HALF-UP",
            "strategy": "add_invoice_line",
            "profit_account_id": account.id,
            "loss_account_id": account.id,
        })
        self.main_pos_config.write({
            "cash_rounding": True,
            "only_round_cash_method": True,
            "rounding_method": rounding.id,
        })
        product = self.env["product.product"].create({
            "name": "POS React cash rounding product",
            "list_price": 10.02,
            "available_in_pos": True,
            "taxes_id": False,
        })
        expected = {"id": product.id, "name": product.name, "total": 10.02, "paid": 10.0}
        self.browser_js(
            f"/pos/react/{self.main_pos_config.id}",
            f"""
            (async () => {{
                const expected = {json.dumps(expected)};
                const waitFor = async (condition, message) => {{
                    for (let attempt = 0; attempt < 300; attempt++) {{
                        const value = await condition();
                        if (value) return value;
                        await new Promise(resolve => setTimeout(resolve, 100));
                    }}
                    throw new Error(message);
                }};
                const data = JSON.parse(document.getElementById('pos-react-data').textContent);
                while (document.querySelector('aside .line')) {{
                    const count = document.querySelectorAll('aside .line').length;
                    document.querySelector('aside .line button').click();
                    await waitFor(() => document.querySelectorAll('aside .line').length < count, 'cart cleanup failed');
                }}
                const product = await waitFor(() => [...document.querySelectorAll('.product')].find(node => !node.disabled && node.querySelector('strong')?.textContent === expected.name), 'cash-rounding product missing');
                product.click();
                await waitFor(() => document.querySelector('aside .line')?.textContent.includes(expected.name), 'cash-rounding cart mutation failed');
                const pay = await waitFor(() => [...document.querySelectorAll('button')].find(button => button.textContent === 'Pay cash' && !button.disabled), 'cash payment unavailable');
                pay.click();
                const order = await waitFor(async () => (await posReact.rpc('pos.order', 'search_read', [[['session_id', '=', data.sessionId], ['state', '=', 'paid'], ['lines.product_id', '=', expected.id]], ['amount_total', 'amount_paid', 'payment_ids'], 0, 1, 'id desc']))[0], 'rounded order missing');
                const payments = await posReact.rpc('pos.payment', 'search_read', [[['id', 'in', order.payment_ids]], ['amount']]);
                if (order.amount_total !== expected.total || order.amount_paid !== expected.paid || payments.length !== 1 || payments[0].amount !== expected.paid) throw new Error(`cash-rounding persistence mismatch: ${{JSON.stringify({{ order, payments }})}}`);
                console.log('POS React cash-only rounding checkout succeeded');
            }})();
            """,
            "Boolean(document.querySelector('#pos-react-root .product') || document.querySelector('#pos-react-root[role=alert]'))",
            login="pos_user",
            success_signal="POS React cash-only rounding checkout succeeded",
        )

    def test_pos_react_browser(self):
        self.browser_js(
            f"/pos/react/{self.main_pos_config.id}",
            """
            (async () => {
            const check = (condition, message) => { if (!condition) throw new Error(message); };
            const waitFor = async (condition, message) => {
                for (let attempt = 0; attempt < 100; attempt++) {
                    const value = await condition();
                    if (value) return value;
                    await new Promise(resolve => setTimeout(resolve, 20));
                }
                throw new Error(message);
            };
            const initialData = JSON.parse(document.getElementById('pos-react-data').textContent);
            const sessionId = initialData.sessionId;
            const loadDraft = () => new Promise((resolve, reject) => {
                const name = `pos-react:${encodeURIComponent(initialData.tenantId)}:${encodeURIComponent(initialData.configId)}:${encodeURIComponent(initialData.userId)}`;
                const request = indexedDB.open(name);
                request.onerror = () => reject(request.error);
                request.onsuccess = () => {
                    const database = request.result;
                    const result = database.transaction('drafts').objectStore('drafts').get(`${initialData.tenantId}:${initialData.configId}:${initialData.userId}:${sessionId}:${initialData.companyId}`);
                    result.onerror = () => reject(result.error);
                    result.onsuccess = () => {
                        database.close();
                        resolve(result.result?.active);
                    };
                };
            });
            check(Number.isInteger(sessionId) && sessionId > 0, 'valid session ID');
            const root = document.getElementById('pos-react-root');
            check(root.getAttribute('role') !== 'alert', root.textContent);
            const products = [...document.querySelectorAll('.product')];
            const categories = [...document.querySelectorAll('nav button')];
            check(products.length > 0, 'real products rendered');
            check(categories.length > 1, 'real categories rendered');
            check(globalThis.posReact?.catalog && globalThis.posReact.metadataGraph, 'POS catalog graph unavailable');
            check(posReact.catalog.offline === false, 'POS catalog unexpectedly offline');
            const catalogProducts = posReact.catalog.records['product.product'];
            const catalogCategories = posReact.catalog.records['pos.category'];
            check(catalogProducts?.length > 0 && catalogCategories?.length > 0, 'catalog product/category records missing');
            for (const dto of initialData.products) {
                const source = catalogProducts.find(record => record.id === dto.id);
                const graph = posReact.metadataGraph.get('product.product', dto.id);
                check(source && graph, `product ${dto.id} missing from catalog graph`);
                check(dto.name === source.display_name && dto.name === graph.display_name, `product ${dto.id} DTO mismatch`);
            }
            for (const dto of initialData.categories) {
                const source = catalogCategories.find(record => record.id === dto.id);
                const graph = posReact.metadataGraph.get('pos.category', dto.id);
                check(source && graph, `category ${dto.id} missing from catalog graph`);
                check(dto.name === source.name && dto.name === graph.name, `category ${dto.id} DTO mismatch`);
            }
            check(products.every(item => initialData.products.some(dto => dto.name === item.querySelector('strong').textContent)), 'rendered product DTO mismatch');
            check(initialData.categories.every(dto => categories.some(item => item.textContent === dto.name)), 'rendered category DTO mismatch');
            const productIndex = initialData.products.findIndex(product => !product.taxIds.length);
            check(productIndex >= 0, 'untaxed product available');
            const product = products[productIndex];
            const name = product.querySelector('strong').textContent;
            const price = product.querySelector('span').textContent;
            const controllerProduct = catalogProducts.find(record => record.display_name === name);
            const normalizedPrice = Number(price.replace(/[^0-9.-]/g, ''));
            check(controllerProduct && normalizedPrice > 0, 'displayed/controller product price must be positive');
            const search = document.querySelector('input[aria-label="Search products"]');
            const setValue = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
            setValue.call(search, name);
            search.dispatchEvent(new Event('input', { bubbles: true }));
            await waitFor(() => document.querySelectorAll('.product').length === 1, 'search filtered');
            check(document.querySelectorAll('.product').length === 1, 'search filtered');
            setValue.call(search, '');
            search.dispatchEvent(new Event('input', { bubbles: true }));
            const findProduct = () => [...document.querySelectorAll('.product')].find(item => item.querySelector('strong').textContent === name);
            await waitFor(() => findProduct(), 'untaxed product restored after search');
            check(findProduct(), 'untaxed product restored after search');
            await waitFor(() => !findProduct()?.disabled, 'product not enabled for cart add');
            findProduct().click();
            await waitFor(async () => document.querySelector('.line')?.textContent.includes('× 1') && (await loadDraft())?.lines?.[0]?.[2]?.qty === 1, 'cart add');
            check(document.querySelector('.line').textContent.includes('× 1'), 'cart add');
            await waitFor(() => !findProduct()?.disabled, 'product not enabled for cart increment');
            findProduct().click();
            await waitFor(async () => document.querySelector('.line')?.textContent.includes('× 2') && (await loadDraft())?.lines?.[0]?.[2]?.qty === 2, 'cart increment');
            check(document.querySelector('.line').textContent.includes('× 2'), 'cart increment');
            await waitFor(() => !document.querySelector('.line button')?.disabled, 'remove not enabled for cart decrement');
            document.querySelector('.line button').click();
            await waitFor(async () => document.querySelector('.line')?.textContent.includes('× 1') && (await loadDraft())?.lines?.[0]?.[2]?.qty === 1, 'cart decrement');
            check(document.querySelector('.line').textContent.includes('× 1'), 'cart decrement');
            check(document.querySelector('aside footer strong:last-child').textContent === price, 'cart total');
            const payCash = await waitFor(() => [...document.querySelectorAll('button')].find(button => button.textContent === 'Pay cash' && !button.disabled), 'Pay cash enabled');
            check(payCash, 'Pay cash enabled');
            const checkoutDraft = await loadDraft();
            await waitFor(async () => await posReact.rpc('pos.order', 'search_count', [[['uuid', '=', checkoutDraft.uuid]]]) === 1, 'server draft exists before checkout');
            payCash.click();
            payCash.click();
            let orders = [];
            for (let attempt = 0; attempt < 50; attempt++) {
                orders = await posReact.rpc('pos.order', 'search_read', [[['uuid', '=', checkoutDraft.uuid]], ['id', 'uuid', 'pos_reference', 'lines', 'payment_ids', 'state']]);
                if (orders[0]?.state === 'paid') break;
                await new Promise(resolve => setTimeout(resolve, 100));
            }
            check(orders.length === 1 && orders[0].state === 'paid', 'server draft finalized exactly once');
            check(orders.length === 1 && orders[0].uuid === orders[0].pos_reference, 'server UUID/order queried');
            check(orders[0].lines.length === 1 && orders[0].payment_ids.length === 1, 'latest order has one line and payment');
            const capturedPayload = JSON.stringify(posReact.buildCashOrder({
                cart: { [controllerProduct.id]: 1 },
                products: [{ ...controllerProduct, price: normalizedPrice, taxIds: [] }],
                total: normalizedPrice,
                sessionId,
                companyId: initialData.companyId,
                cashMethodId: initialData.cashMethodId,
                accessToken: crypto.randomUUID(),
            }));
            const capturedOrder = JSON.parse(capturedPayload);
            await posReact.rpc('pos.order', 'sync_from_ui', [[JSON.parse(capturedPayload)]]);
            await posReact.rpc('pos.order', 'sync_from_ui', [[JSON.parse(capturedPayload)]]);
            const duplicateProbe = await posReact.rpc('pos.order', 'search_read', [[['uuid', '=', capturedOrder.uuid]], ['lines', 'payment_ids']]);
            check(duplicateProbe.length === 1, 'identical serialized payload creates one order');
            const capturedLines = await posReact.rpc('pos.order.line', 'search_read', [[['order_id', '=', duplicateProbe[0].id]], ['uuid']]);
            const capturedPayments = await posReact.rpc('pos.payment', 'search_read', [[['pos_order_id', '=', duplicateProbe[0].id]], ['uuid']]);
            check(capturedLines.length === 1 && capturedLines[0].uuid === capturedOrder.lines[0][2].uuid, 'no duplicate child UUIDs');
            check(capturedPayments.length === 1 && capturedPayments[0].uuid === capturedOrder.payment_ids?.[0]?.[2]?.uuid, `no duplicate payments: ${JSON.stringify({ capturedPayment: capturedOrder.payment_ids?.[0]?.[2], persistedPayments: capturedPayments })}`);
            const serverLines = await posReact.rpc('pos.order.line', 'search_read', [[['id', 'in', orders[0].lines]], ['product_id', 'qty']]);
            const payments = await posReact.rpc('pos.payment', 'search_read', [[['id', 'in', orders[0].payment_ids]], ['amount', 'payment_method_id']]);
            check(serverLines.length === 1 && serverLines[0].qty === 1, 'server order lines queried');
            check(payments.length === 1 && payments[0].amount > 0, 'server cash payment queried');
            const order = posReact.buildCashOrder({
                cart: { 7: 2 },
                products: [{ id: 7, price: 4, taxIds: [] }],
                total: 8,
                sessionId: 11,
                companyId: 12,
                cashMethodId: 13,
            });
            check(order.uuid === order.pos_reference, 'stable order UUID reference');
            check(order.lines[0][2].uuid && order.payment_ids[0][2].uuid, 'stable child UUIDs');
            check(order.lines[0][2].price_subtotal === 8 && order.lines[0][2].price_subtotal_incl === 8, 'required line totals serialized');
            check(order.lines[0][2].tax_ids[0][2].length === 0 && order.amount_tax === 0, 'untaxed order serialized');
            const legacyTotal = posReact.buildCashOrder({ cart: { 7: 2 }, products: [{ id: 7, price: 4, taxIds: [] }], total: 9, sessionId: 11, companyId: 12, cashMethodId: 13 });
            check(legacyTotal.amount_total === 9 && legacyTotal.amount_paid === 9 && legacyTotal.payment_ids[0][2].amount === 9, 'legacy object cart explicit total ignored');
            const arrayTotal = posReact.buildCashOrder({ cart: [{ uuid: crypto.randomUUID(), productId: 7, quantity: 2, price: 4, taxIds: [], discount: 0, extraTaxData: {} }], products: [{ id: 7, price: 4, taxIds: [] }], total: 9, sessionId: 11, companyId: 12, cashMethodId: 13 });
            check(arrayTotal.amount_total === 8 && arrayTotal.amount_paid === 8 && arrayTotal.payment_ids[0][2].amount === 8, 'array cart trusted legacy explicit total');
            const ack = {
                'pos.order': [{ id: 21, uuid: order.uuid, session_id: 11, state: 'paid', amount_total: 8, amount_paid: 8, amount_return: 0 }],
                'pos.order.line': [{ id: 22, uuid: order.lines[0][2].uuid, order_id: 21 }],
                'pos.payment': [{ id: 23, uuid: order.payment_ids[0][2].uuid, pos_order_id: 21, amount: 8 }],
            };
            check(posReact.validateCashAck(ack, order, 2), 'valid cash ACK rejected');
            const malformedAcks = [
                { ...ack, 'pos.order': [{ ...ack['pos.order'][0], uuid: crypto.randomUUID() }] },
                { ...ack, 'pos.order': [{ ...ack['pos.order'][0], id: 0 }] },
                { ...ack, 'pos.order': [{ ...ack['pos.order'][0], session_id: 12 }] },
                { ...ack, 'pos.order.line': [] },
                { ...ack, 'pos.order.line': [{ ...ack['pos.order.line'][0], order_id: 99 }] },
                { ...ack, 'pos.payment': [{ ...ack['pos.payment'][0], uuid: crypto.randomUUID() }] },
                { ...ack, 'pos.payment': [{ ...ack['pos.payment'][0], pos_order_id: 99 }] },
                { ...ack, 'pos.order': [{ ...ack['pos.order'][0], amount_total: NaN }] },
                { ...ack, 'pos.payment': [{ ...ack['pos.payment'][0], amount: 8.001 }] },
                { ...ack, 'pos.order': [{ ...ack['pos.order'][0], amount_paid: 7 }] },
                { ...ack, 'pos.order': [{ ...ack['pos.order'][0], state: 'draft' }] },
                { ...ack, 'pos.order': [{ ...ack['pos.order'][0], amount_return: 1 }] },
                { ...ack, 'pos.order': [{ ...ack['pos.order'][0], partner_id: [99, 'Wrong'] }] },
            ];
            malformedAcks.forEach((value, index) => check(!posReact.validateCashAck(value, order, 2), `malformed cash ACK accepted: ${index}`));
            const taxed = posReact.buildCashOrder({
                cart: { 7: 1 }, products: [{ id: 7, price: 100, taxIds: [3] }], sessionId: 11, companyId: 12, cashMethodId: 13,
                taxContext: { taxes: [{ id: 3, sequence: 1, amount_type: 'percent', amount: 10, price_include: false, include_base_amount: false, is_base_affected: true, has_negative_factor: false, children_tax_ids: [] }], precision: 0.01 },
            });
            check(taxed.lines[0][2].tax_ids[0][2][0] === 3 && taxed.amount_tax === 10 && taxed.amount_total === 110, 'taxed order serialized');
            check(order.session_id === 11 && order.company_id === 12, 'bootstrap IDs serialized');
            check(order.payment_ids[0][2].payment_method_id === 13, 'cash method serialized');
            const nativeFetch = globalThis.fetch;
            globalThis.fetch = async () => new Response(JSON.stringify({ error: { message: 'terminal server rejection' } }), { headers: { 'content-type': 'application/json' } });
            try {
                await posReact.rpc('pos.order', 'pos_react_sync_from_ui', [[order]]);
                throw new Error('server rejection was accepted');
            } catch (error) {
                check(error.permanent === true && error.message === 'terminal server rejection', 'server rejection was not permanent');
            } finally {
                globalThis.fetch = nativeFetch;
            }
            console.log('pos react browser succeeded');
            })();
            """,
            "Boolean(document.querySelector('#pos-react-root .product') || document.querySelector('#pos-react-root[role=alert]'))",
            login="pos_user",
            success_signal="pos react browser succeeded",
        )

    def test_electronic_payment_lifecycle(self):
        method = self.env["pos.payment.method"].create({
            "name": "Browser electronic",
            "journal_id": self.bank_journal.id,
            "payment_method_type": "terminal",
            "use_payment_terminal": "browser-oracle",
        })
        self.main_pos_config.payment_method_ids = [(4, method.id)]
        with patch("odoo.tests.common.ChromeBrowser", ElectronicPaymentOracleBrowser):
            self.browser_js(
                f"/pos/react/{self.main_pos_config.id}",
                f"""
                (async () => {{
                    const check = (condition, message) => {{ if (!condition) throw new Error(message); }};
                    const waitFor = async (probe, message) => {{
                        for (let attempt = 0; attempt < 150; attempt++) {{
                            const value = await probe();
                            if (value) return value;
                            await new Promise(resolve => setTimeout(resolve, 20));
                        }}
                        throw new Error(message);
                    }};
                    const product = await waitFor(() => [...document.querySelectorAll('.product')].find(button => !button.disabled), 'product unavailable');
                    product.click();
                    let total = await waitFor(() => {{
                        const value = Number(document.querySelector('aside footer strong:last-child')?.textContent.replace(/[^0-9.-]/g, ''));
                        return value > 0 && value;
                    }}, 'cart total unavailable');
                    while (total <= 4) {{
                        await waitFor(() => !product.disabled, 'product mutation did not settle');
                        const previous = total;
                        product.click();
                        total = await waitFor(() => {{
                            const value = Number(document.querySelector('aside footer strong:last-child')?.textContent.replace(/[^0-9.-]/g, ''));
                            return value > previous && value;
                        }}, 'cart total did not increase');
                    }}
                    const cash = document.querySelector('[aria-label="Cash amount"]');
                    Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set.call(cash, '4');
                    cash.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    await new Promise(resolve => setTimeout(resolve, 0));
                    const pay = await waitFor(() => [...document.querySelectorAll('button')].find(button => button.textContent === 'Browser oracle — Browser electronic' && !button.disabled), 'electronic method unavailable');
                    pay.click();
                    await waitFor(() => typeof window.releaseElectronicPayment === 'function', 'adapter did not start');
                    check(window.electronicPaymentAmounts[0] === total - 4, 'adapter did not receive remaining amount');
                    const before = await posReact.rpc('pos.order', 'search_count', [[['payment_ids.payment_method_id', '=', {method.id}], ['state', '=', 'paid']]]);
                    check(document.querySelector('[aria-label="Electronic payment"]')?.textContent.includes('pending'), 'unresolved adapter not pending');
                    check((await posReact.rpc('pos.order', 'search_count', [[['payment_ids.payment_method_id', '=', {method.id}], ['state', '=', 'paid']]])) === before, 'unresolved adapter finalized order');
                    [...document.querySelectorAll('button')].find(button => button.textContent === 'Cancel').click();
                    const newPayment = await waitFor(() => document.querySelector('[aria-label="Electronic payment"]')?.textContent.includes('cancelled') && [...document.querySelectorAll('button')].find(button => button.textContent === 'New payment' && !button.disabled), 'cancel did not settle');
                    check(window.electronicPaymentCancelCount === 1, 'adapter cancel not called exactly once');
                    window.releaseElectronicPayment();
                    await new Promise(resolve => setTimeout(resolve, 50));
                    check((await posReact.rpc('pos.order', 'search_count', [[['payment_ids.payment_method_id', '=', {method.id}], ['state', '=', 'paid']]])) === before, 'stale completion finalized cancelled payment');
                    newPayment.click();
                    (await waitFor(() => [...document.querySelectorAll('button')].find(button => button.textContent === 'Browser oracle — Browser electronic' && !button.disabled), 'new payment unavailable')).click();
                    const retry = await waitFor(() => document.querySelector('[aria-label="Electronic payment"]')?.textContent.includes('retry') && [...document.querySelectorAll('button')].find(button => button.textContent === 'Retry' && !button.disabled), 'new payment did not request retry');
                    check((await posReact.rpc('pos.order', 'search_count', [[['payment_ids.payment_method_id', '=', {method.id}], ['state', '=', 'paid']]])) === before, 'retry finalized early');
                    retry.click();
                    const order = await waitFor(async () => (await posReact.rpc('pos.order', 'search_read', [[['payment_ids.payment_method_id', '=', {method.id}], ['state', '=', 'paid']], ['payment_ids'], 0, 1, 'id desc']))[0], 'electronic order missing');
                    const payments = await posReact.rpc('pos.payment', 'search_read', [[['id', 'in', order.payment_ids]], ['uuid', 'payment_method_id', 'amount'], 0, 2, 'id']);
                    check(window.electronicPaymentStartCount === 3 && payments.length === 2, 'retry did not finalize exactly two slices');
                    check(payments[0].amount === 4 && payments[1].amount === total - 4 && payments[1].payment_method_id[0] === {method.id}, 'cash-first remaining slice mismatch');
                    check(new Set(payments.map(payment => payment.uuid)).size === 2, 'payment UUIDs not stable and distinct');
                    console.log('POS React electronic payment lifecycle succeeded');
                }})();
                """,
                "Boolean(document.querySelector('#pos-react-root .product') || document.querySelector('#pos-react-root[role=alert]'))",
                login="pos_user",
                success_signal="POS React electronic payment lifecycle succeeded",
            )

    def test_pos_react_offline_store(self):
        database_name = f"pos-react:test-{self.env.cr.dbname}:{self.main_pos_config.id}:test-user"
        self.browser_js(
            f"/pos/react/{self.main_pos_config.id}",
            f"""
            (async () => {{
            const check = (condition, message) => {{ if (!condition) throw new Error(message); }};
            const databaseName = {database_name!r};
            const deleteDatabase = () => new Promise((resolve, reject) => {{
                const request = indexedDB.deleteDatabase(databaseName);
                request.onsuccess = resolve;
                request.onerror = () => reject(request.error);
                request.onblocked = () => reject(new Error('database cleanup blocked'));
            }});
            let store;
            try {{
                await deleteDatabase();
                store = posReactOfflineStore.create({{
                    tenantId: 'test-' + {self.env.cr.dbname!r},
                    configId: {str(self.main_pos_config.id)!r},
                    userId: 'test-user', sessionId: 'test-session', companyId: 'test-company',
                    send: async () => {{ throw new Error('offline'); }},
                }});
                const firstId = await store.put({{ sequence: 1 }}, 'stable-first');
                await new Promise(resolve => setTimeout(resolve, 2));
                const secondId = await store.put({{ sequence: 2 }}, 'stable-second');
                check(firstId === 'stable-first' && secondId === 'stable-second', 'stable IDs');
                await store.close();

                const sent = [];
                let failOnce = true;
                store = posReactOfflineStore.create({{
                    tenantId: 'test-' + {self.env.cr.dbname!r},
                    configId: {str(self.main_pos_config.id)!r},
                    userId: 'test-user', sessionId: 'test-session', companyId: 'test-company',
                    send: async (payload, id) => {{
                        sent.push([payload.sequence, id]);
                        if (failOnce) {{
                            failOnce = false;
                            throw new Error('offline');
                        }}
                        return {{ accepted: id }};
                    }},
                    isValidAck: (ack, payload, id) => ack?.accepted === id,
                }});
                await store.drain();
                let records = await store.list();
                check(JSON.stringify(sent) === JSON.stringify([[1, 'stable-first'], [2, 'stable-second']]), 'transient failure does not stop later valid record');
                check(records.length === 1 && records[0].id === 'stable-first' && records[0].status === 'retry' && records[0].attempts === 1 && records[0].errorCode === 'TRANSPORT', 'failed drain persists retry status');
                await store.close();
                store = posReactOfflineStore.create({{
                    tenantId: 'test-' + {self.env.cr.dbname!r},
                    configId: {str(self.main_pos_config.id)!r},
                    userId: 'test-user', sessionId: 'test-session', companyId: 'test-company',
                    send: async () => null,
                }});
                await store.retryNow('stable-first');
                records = await store.list();
                check(records.length === 1 && records[0].id === 'stable-first' && records[0].status === 'blocked' && records[0].attempts === 2 && records[0].errorCode === 'INVALID_ACK', 'invalid ack is blocked and retained');
                await store.drain();
                check((await store.list()).length === 1, 'blocked invalid ack remains fail-closed');
                await store.put({{ sequence: 3 }}, 'ack-crash');
                let ackCrash = true;
                let replayed = 0;
                await store.close();
                store = posReactOfflineStore.create({{
                    tenantId: 'test-' + {self.env.cr.dbname!r},
                    configId: {str(self.main_pos_config.id)!r},
                    userId: 'test-user', sessionId: 'test-session', companyId: 'test-company',
                    send: async (payload, id) => {{
                        if (id !== 'ack-crash') return null;
                        replayed += 1;
                        return {{ accepted: id, sequence: payload.sequence }};
                    }},
                    isValidAck: (ack, payload, id) => {{
                        const valid = ack?.accepted === id && ack.sequence === payload.sequence;
                        if (valid && ackCrash) {{
                            ackCrash = false;
                            throw new Error('SIMULATED_ACK_BEFORE_DELETE_CRASH');
                        }}
                        return valid;
                    }},
                }});
                await store.retryNow('ack-crash');
                records = await store.list();
                check(records.some(record => record.id === 'ack-crash' && record.status === 'retry'), 'ack-before-delete crash lost durable outbox record');
                await store.close();
                store = posReactOfflineStore.create({{
                    tenantId: 'test-' + {self.env.cr.dbname!r},
                    configId: {str(self.main_pos_config.id)!r},
                    userId: 'test-user', sessionId: 'test-session', companyId: 'test-company',
                    send: async (payload, id) => {{
                        if (id !== 'ack-crash') return null;
                        replayed += 1;
                        return {{ accepted: id, sequence: payload.sequence }};
                    }},
                    isValidAck: (ack, payload, id) => ack?.accepted === id && ack.sequence === payload.sequence,
                }});
                await store.retryNow('ack-crash');
                check(replayed === 2 && !(await store.list()).some(record => record.id === 'ack-crash'), 'ack replay was not eventually acknowledged exactly once locally');
                console.log('pos react offline store succeeded');
            }} finally {{
                if (store) await store.close();
                await deleteDatabase();
            }}
            }})();
            """,
            "Boolean(globalThis.posReactOfflineStore)",
            login="pos_user",
            success_signal="pos react offline store succeeded",
        )

    def test_pos_react_offline_store_retry_policy(self):
        tenant_id = f"retry-policy-{self.env.cr.dbname}"
        database_name = f"pos-react:{tenant_id}:{self.main_pos_config.id}:retry-user"
        self.browser_js(
            f"/pos/react/{self.main_pos_config.id}",
            f"""
            (async () => {{
            const check = (condition, message) => {{ if (!condition) throw new Error(message); }};
            const tenantId = {tenant_id!r};
            const databaseName = {database_name!r};
            const scope = {{ tenantId, configId: {str(self.main_pos_config.id)!r}, userId: 'retry-user', sessionId: 'retry-session', companyId: 'retry-company' }};
            const deleteDatabase = () => new Promise((resolve, reject) => {{
                const request = indexedDB.deleteDatabase(databaseName);
                request.onsuccess = resolve;
                request.onerror = () => reject(request.error);
                request.onblocked = () => reject(new Error('database cleanup blocked'));
            }});
            const mutate = (id, callback) => new Promise((resolve, reject) => {{
                const request = indexedDB.open(databaseName, posReactOfflineStore.schemaVersion);
                request.onerror = () => reject(request.error);
                request.onsuccess = () => {{
                    const db = request.result;
                    const transaction = db.transaction('outbox', 'readwrite');
                    const store = transaction.objectStore('outbox');
                    const get = store.get(id);
                    get.onsuccess = () => store.put(callback(get.result));
                    transaction.oncomplete = () => {{ db.close(); resolve(); }};
                    transaction.onerror = () => {{ db.close(); reject(transaction.error); }};
                }};
            }});
            let clock = 1_000_000;
            let store;
            const sent = [];
            try {{
                await deleteDatabase();
                check(JSON.stringify(Array.from({{ length: 8 }}, (_, index) => posReactOfflineStore.retryDelay(index + 1) / 1000)) === JSON.stringify([2, 4, 8, 16, 32, 64, 128, 256]), 'retry delay sequence');
                check(posReactOfflineStore.retryDelay(9) === 300000 && posReactOfflineStore.retryDelay(20) === 300000, 'retry delay cap');
                store = posReactOfflineStore.create({{
                    ...scope,
                    now: () => clock,
                    send: async (payload, id) => {{ sent.push(id); if (id === 'exhaust') throw new Error('offline'); return {{ accepted: id }}; }},
                    isValidAck: (ack, payload, id) => ack?.accepted === id,
                }});
                await store.put({{ kind: 'old' }}, 'exhaust');
                let record = (await store.list())[0];
                check(record.createdAt === clock && record.updatedAt === clock && record.lastAttemptAt === null && record.nextAttemptAt === clock && record.status === 'pending' && record.attempts === 0 && record.errorCode === null && record.payloadHash && record.scope.tenantId === tenantId, 'put fields');
                for (let attempt = 1; attempt <= 8; attempt++) {{
                    await store.drain();
                    record = (await store.list()).find(item => item.id === 'exhaust');
                    check(record.attempts === attempt && record.lastAttemptAt === clock && record.updatedAt === clock, `attempt ${{attempt}} fields`);
                    if (attempt === 8) break;
                    const deadline = record.nextAttemptAt;
                    const sends = sent.length;
                    clock = deadline - 1;
                    await store.drain();
                    check(sent.length === sends && (await store.list()).find(item => item.id === 'exhaust').attempts === attempt, `attempt ${{attempt}} sent before deadline`);
                    await store.put({{ kind: 'unrelated' }}, `other-${{attempt}}`);
                    await store.drain();
                    check(sent.at(-1) === `other-${{attempt}}` && !(await store.list()).some(item => item.id === `other-${{attempt}}`), 'unrelated pending not sent');
                    clock = deadline;
                }}
                check(record.status === 'blocked' && record.errorCode === 'RETRY_EXHAUSTED' && record.nextAttemptAt === null, 'attempt 8 exhaustion');

                await store.put({{ kind: 'target' }}, 'target');
                await store.put({{ kind: 'non-target' }}, 'non-target');
                await mutate('target', item => ({{ ...item, status: 'retry', nextAttemptAt: clock + 999999 }}));
                await mutate('non-target', item => ({{ ...item, status: 'retry', nextAttemptAt: clock + 999999 }}));
                const beforeRetryNow = sent.length;
                await store.retryNow('target');
                check(sent.length === beforeRetryNow + 1 && sent.at(-1) === 'target' && (await store.list()).some(item => item.id === 'non-target'), 'retryNow only target');

                await store.put({{ kind: 'tampered' }}, 'tampered');
                await store.put({{ kind: 'scope' }}, 'scope');
                await mutate('tampered', item => ({{ ...item, payload: {{ kind: 'changed' }} }}));
                await mutate('scope', item => ({{ ...item, scope: {{ ...item.scope, tenantId: 'foreign' }} }}));
                const beforeManual = sent.length;
                await store.retryNow('tampered');
                await store.retryNow('scope');
                const blocked = Object.fromEntries((await store.list()).map(item => [item.id, item]));
                check(sent.length === beforeManual && blocked.tampered.status === 'blocked' && blocked.tampered.errorCode === 'PAYLOAD_TAMPERED', 'tampered manually blocked without send');
                check(blocked.scope.status === 'blocked' && blocked.scope.errorCode === 'SCOPE_MISMATCH', 'scope manually blocked without send');
                console.log('pos react retry policy succeeded');
            }} finally {{
                if (store) await store.close();
                await deleteDatabase();
            }}
            }})();
            """,
            "Boolean(globalThis.posReactOfflineStore)",
            login="pos_user",
            success_signal="pos react retry policy succeeded",
        )
