(() => {
    "use strict";

    const { createElement: h, useEffect, useMemo, useRef, useState } = React;
    const INITIAL_DATA = JSON.parse(document.getElementById("pos-react-data").textContent);
    const plugins = window.posReactPlugins;
    if (!plugins) throw new Error("POS React plugin registry is required");

    const resolved = Object.fromEntries(plugins.points.map((point) => [point, plugins.resolve(point)]));
    const values = (point) => resolved[point].map(({ id, value }) => {
        if (!value || typeof value !== "object") throw new Error(`Invalid POS React plugin contract: ${point}:${id}`);
        return { id, ...value };
    });
    const extensions = {
        screens: values("screen"),
        slots: values("slot"),
        actions: values("action"),
        payments: values("paymentAdapter"),
        receipt: values("receiptFragment"),
    };
    function applyDataRequirements(data) {
        for (const requirement of values("dataRequirement")) {
            if (typeof requirement.transform !== "function") throw new Error(`Invalid POS React data requirement: ${requirement.id}`);
            data = requirement.transform(data);
            if (!data || typeof data !== "object") throw new Error(`Invalid POS React data transform result: ${requirement.id}`);
        }
        return data;
    }

    function component(extension, props) {
        if (typeof extension.component !== "function") throw new Error(`Invalid POS React component: ${extension.id}`);
        return h(extension.component, { key: extension.id, ...props });
    }

    function updateCart(cart, product, delta, uuid = null) {
        const line = uuid ? cart.find((item) => item.uuid === uuid) : cart.find(({ productId }) => productId === product.id);
        const quantity = (line?.quantity || 0) + delta;
        if (quantity <= 0) return cart.filter((item) => item !== line);
        return line
            ? cart.map((item) => item === line ? { ...item, quantity } : item)
            : [...cart, { uuid: crypto.randomUUID(), productId: product.id, quantity, price: product.price, taxIds: product.taxIds, discount: 0, extraTaxData: {} }];
    }

    function effectiveLines(cart, products) {
        const isArrayCart = Array.isArray(cart);
        const lines = isArrayCart ? cart : Object.entries(cart).map(([productId, quantity]) => ({ uuid: crypto.randomUUID(), productId: Number(productId), quantity }));
        return lines.map((line) => {
            const product = products.find((item) => item.id === line.productId);
            if (!product) return null;
            return {
                ...line,
                product,
                ...(!line.isCustom && line.extraTaxData?.discount_percentage === undefined ? { price: product.price, taxIds: product.taxIds } : {}),
            };
        }).filter(Boolean);
    }

    async function rpc(model, method, args = [], kwargs = {}) {
        const response = await fetch("/api/model/call", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ jsonrpc: "2.0", method: "call", params: { model, method, args, kwargs } }),
        });
        if (!response.ok || !response.headers.get("content-type")?.toLowerCase().includes("application/json")) {
            throw new Error(`RPC failed with HTTP ${response.status}`);
        }
        const payload = await response.json();
        if (payload.error) {
            const error = new Error(payload.error.data?.message || payload.error.message);
            error.permanent = true;
            throw error;
        }
        return payload.result;
    }

    function doAction(action, { additionalContext = {} } = {}) {
        const query = new URLSearchParams(additionalContext);
        window.location.assign(`/insilos/action-${action}${query.size ? `?${query}` : ""}`);
    }

    function validateCashAck(ack, payload, decimalPlaces) {
        const orders = ack?.["pos.order"];
        const lines = ack?.["pos.order.line"];
        const payments = ack?.["pos.payment"];
        const order = Array.isArray(orders) && orders.length === 1 ? orders[0] : null;
        const positiveId = (value) => Number.isInteger(value) && value > 0;
        const rounded = (value) => Number.isFinite(value) && value === Number(value.toFixed(decimalPlaces));
        const exactUuids = (records, commands) => {
            const expected = commands.map(([, , values]) => values.uuid);
            return Array.isArray(records) && records.length === expected.length &&
                new Set(expected).size === expected.length && new Set(records.map(({ uuid }) => uuid)).size === records.length &&
                records.every(({ uuid }) => expected.includes(uuid));
        };
        if (!order || order.uuid !== payload.uuid || !positiveId(order.id) || !positiveId(order.session_id) || order.session_id !== payload.session_id || !["paid", "done"].includes(order.state)) return false;
        for (const field of ["partner_id", "pricelist_id", "fiscal_position_id"]) {
            const expected = payload[field] || false;
            const actual = order[field]?.[0] || order[field] || false;
            if (expected !== actual) return false;
        }
        if (!exactUuids(lines, payload.lines) || !lines.every((line) => positiveId(line.id) && line.order_id === order.id)) return false;
        if (!exactUuids(payments, payload.payment_ids) || !payments.every((payment) => positiveId(payment.id) && payment.pos_order_id === order.id && rounded(payment.amount))) return false;
        const total = order.amount_total;
        const paid = order.amount_paid;
        const change = order.amount_return;
        return rounded(total) && rounded(paid) && rounded(change) &&
            total === Number(payload.amount_total.toFixed(decimalPlaces)) &&
            paid === Number(payload.amount_paid.toFixed(decimalPlaces)) && change === 0 &&
            Number(payments.reduce((sum, payment) => sum + payment.amount, 0).toFixed(decimalPlaces)) === paid;
    }

    function validateDraftAck(ack, payload, decimalPlaces) {
        const orders = ack?.["pos.order"];
        const lines = ack?.["pos.order.line"];
        const payments = ack?.["pos.payment"] || [];
        const order = Array.isArray(orders) && orders.length === 1 ? orders[0] : null;
        const positiveId = (value) => Number.isInteger(value) && value > 0;
        const rounded = (value) => Number.isFinite(value) && value === Number(value.toFixed(decimalPlaces));
        const expectedUuids = payload.lines.map(([, , line]) => line.uuid);
        return Boolean(
            order && order.uuid === payload.uuid && order.state === "draft" &&
            positiveId(order.id) && order.session_id === payload.session_id &&
            rounded(order.amount_total) && order.amount_total === Number(payload.amount_total.toFixed(decimalPlaces)) &&
            order.amount_paid === 0 && Array.isArray(lines) && lines.length === expectedUuids.length &&
            new Set(expectedUuids).size === expectedUuids.length &&
            new Set(lines.map(({ uuid }) => uuid)).size === lines.length &&
            lines.every((line) => expectedUuids.includes(line.uuid) && positiveId(line.id) && line.order_id === order.id) &&
            Array.isArray(payments) && payments.length === 0
        );
    }

    const PAYMENT_STATES = new Set(["pending", "waiting", "done", "retry", "cancelled"]);
    function paymentState(result) {
        const state = typeof result === "string" ? result : result?.state;
        return state === "paid" || result === true ? "done" : (PAYMENT_STATES.has(state) ? state : "retry");
    }

    function buildCashOrder({ cart, products, total, taxContext = { taxes: [], precision: 0.01 }, cashRounding = { enabled: false }, partnerId = false, pricelistId = false, fiscalPositionId = false, tableId = false, tableNumber = false, customerCount = false, isVirtual = false, sessionId, companyId, employeeId = false, cashMethodId, electronicMethodId = false, cashAmount, accessToken, uuid = crypto.randomUUID(), cashPaymentUuid = crypto.randomUUID(), electronicPaymentUuid = crypto.randomUUID(),
    electronicPaymentData = {},
}) {
        const selected = effectiveLines(cart, products);
        const amounts = PosReactTaxEngine.computeLines(selected.map(({ product, quantity, price = product.price, taxIds = product.taxIds, discount = 0, extraTaxData = {} }) => ({
            product, price, quantity, discount, taxIds, extraTaxData,
        })), taxContext);
        const computedTotal = !Array.isArray(cart) && total !== undefined ? total : amounts.total;
        const roundedTotal = cashRounding.enabled
            ? PosReactTaxEngine.roundPrecision(computedTotal, cashRounding.precision, cashRounding.method)
            : computedTotal;
        const orderTotal = cashRounding.enabled && !cashRounding.onlyCash ? roundedTotal : computedTotal;
        const lines = amounts.lines.map((line, index) => {
            const { uuid, productId, quantity, product, price, taxIds, discount, extraTaxData, kitchenSent, kitchenSentAt, isCustom, ...attributes } = selected[index];
            return [0, 0, {
                ...attributes,
                uuid,
                product_id: line.product.id,
                qty: line.quantity,
                price_unit: line.price,
                price_subtotal: line.subtotal,
                price_subtotal_incl: line.total,
                discount: line.discount,
                tax_ids: [[6, 0, line.taxIds]],
                extra_tax_data: line.extraTaxData,
            }];
        });
        const cashSlice = cashAmount === undefined ? roundedTotal : cashAmount;
        const electronicSlice = Number((roundedTotal - cashSlice).toFixed(taxContext.precision.toString().split(".")[1]?.length || 0));
        const paymentDate = new Date().toISOString().slice(0, 19).replace("T", " ");
        const paymentIds = [];
        if (cashSlice) paymentIds.push([0, 0, {
            uuid: cashPaymentUuid, payment_method_id: cashMethodId, amount: cashSlice,
            payment_date: new Date().toISOString().slice(0, 19).replace("T", " "),
        }]);
        if (electronicSlice) paymentIds.push([0, 0, { uuid: electronicPaymentUuid, payment_method_id: electronicMethodId, amount: electronicSlice, payment_date: paymentDate, ...electronicPaymentData }]);
        const realTable = Boolean(tableId && !isVirtual && INITIAL_DATA?.restaurant?.enabled && INITIAL_DATA?.restaurant?.tables?.some((t) => t.id === tableId && !t.is_virtual));
        const tableNote = (tableId && !realTable)
            ? `[Table ${tableNumber || tableId}${customerCount ? ` (${customerCount}p)` : ""}]`
            : "";
        return {
            uuid,
            access_token: accessToken,
            name: "/",
            pos_reference: uuid,
            session_id: sessionId,
            company_id: companyId,
            ...(employeeId ? { employee_id: employeeId } : {}),
            partner_id: partnerId,
            pricelist_id: pricelistId,
            fiscal_position_id: fiscalPositionId,
            ...(realTable ? { table_id: tableId, customer_count: customerCount || false } : {}),
            ...(tableNote ? { general_customer_note: tableNote } : {}),
            state: "paid",
            amount_paid: roundedTotal,
            amount_total: orderTotal,
            amount_tax: amounts.tax,
            amount_return: 0,
            lines,
            payment_ids: paymentIds,
        };
    }

    function App({ configName, tenantId, userId, sessionId, configId, companyId, cashMethodId, electronicPaymentMethods, cashRounding, accessToken, websocketWorkerVersion, products, categories, currency, allowProductCreation, metadataGraph, ...bootstrapPluginData }) {
        const employeePolicy = extensions.actions.find(({ restore }) => typeof restore === "function");
        const employeeHintKey = `pos-react:employee:${tenantId}:${sessionId}`;
        const employeeLockKey = `pos-react:locked:${tenantId}:${sessionId}`;
        const initiallyLocked = Boolean(employeePolicy && sessionStorage.getItem(employeeLockKey));
        const [activeEmployee, setActiveEmployee] = useState(bootstrapPluginData.employee);
        const [locked, setLocked] = useState(initiallyLocked);
        const pluginData = { ...bootstrapPluginData, employee: activeEmployee, role: activeEmployee?.role || bootstrapPluginData.role };
        const company = (metadataGraph.models.has("rs.company") ? metadataGraph.get("rs.company", companyId) : false) || (metadataGraph.models.has("res.company") ? metadataGraph.get("res.company", companyId) : false) || (metadataGraph.models.has("organization.unit") ? metadataGraph.get("organization.unit", companyId) : null);
        const config = metadataGraph.get("pos.config", configId);
        const formatMoney = (amount) => {
            const value = PosReactTaxEngine.roundPrecision(amount, currency.rounding).toFixed(currency.decimalPlaces);
            return currency.position === "before" ? `${currency.symbol}${value}` : `${value} ${currency.symbol}`;
        };
        const [cart, setCart] = useState([]);
        const partnerModel = metadataGraph.models.has("rs.partner") ? "rs.partner" : (metadataGraph.models.has("res.partner") ? "res.partner" : "party.master");
        const customers = metadataGraph.models.has(partnerModel) ? metadataGraph.all(partnerModel).filter((partner) => !partner._deleted) : [];
        const defaultPricelist = config?.pricelist_id || null;
        const [customerId, setCustomerId] = useState(false);
        const [restaurantContext, setRestaurantContext] = useState({ tableId: false, customerCount: false });
        const customer = customerId ? metadataGraph.get(partnerModel, customerId) : null;
        const pricelist = customer?.specific_property_product_pricelist || customer?.property_product_pricelist || defaultPricelist;
        const fiscalPosition = customer?.fiscal_position_id || config?.default_fiscal_position_id || null;
        const pricedProducts = products.map((product) => ({
            ...product,
            price: PosReactPricelistEngine.computePrice(product, pricelist, cart.find(({ productId }) => productId === product.id)?.quantity || 1),
        }));
        const taxContext = useMemo(() => ({
            taxes: metadataGraph.all("account.tax").filter((tax) => !tax._deleted),
            fiscalPosition,
            precision: currency.rounding,
            roundingMethod: company?.tax_calculation_rounding_method || "round_per_line",
        }), [metadataGraph, company, fiscalPosition, currency.rounding]);
        const [categoryId, setCategoryId] = useState(null);
        const [query, setQuery] = useState("");
        const [screen, setScreen] = useState(null);
        const [selectedLineUuid, setSelectedLineUuid] = useState(null);
        const [numpadMode, setNumpadMode] = useState("qty");
        const [numpadBuffer, setNumpadBuffer] = useState("");
        const [showCustomerModal, setShowCustomerModal] = useState(false);
        const [showNoteModal, setShowNoteModal] = useState(false);
        const [orderNote, setOrderNote] = useState("");
        const [lastValidatedOrder, setLastValidatedOrder] = useState(null);
        const [orderTabs, setOrderTabs] = useState([{ id: 1, name: "Order 1" }]);
        const [activeTabId, setActiveTabId] = useState(1);
        const [tabCarts, setTabCarts] = useState({});
        const [tabContexts, setTabContexts] = useState({});
        const [pending, setPending] = useState([]);
        const [exportProofs, setExportProofs] = useState({});
        const [deleteConfirmations, setDeleteConfirmations] = useState({});
        const [recoveryMessage, setRecoveryMessage] = useState("");
        const [recoveryError, setRecoveryError] = useState("");
        const [activeAction, setActiveAction] = useState(null);
        const actionTriggerRef = useRef(null);
        const [recoveryBusy, setRecoveryBusy] = useState("");
        const [checkingOut, setCheckingOut] = useState(false);
        const [electronicPayment, setElectronicPayment] = useState(null);
        const [cashAmount, setCashAmount] = useState(0);
        const [refundLine, setRefundLine] = useState(null);
        const [refundQty, setRefundQty] = useState(1);
        const [realtimeStatus, setRealtimeStatus] = useState("connecting");
        const [draftReady, setDraftReady] = useState(false);
        const [mutating, setMutating] = useState(false);
        const [finalizedAlert, setFinalizedAlert] = useState("");
        const draftId = "active";
        const newDraftIdentity = () => ({ uuid: crypto.randomUUID(), cashPaymentUuid: crypto.randomUUID(), electronicPaymentUuid: crypto.randomUUID() });
        const draftIdentity = useRef(newDraftIdentity());
        const draftPayload = useRef(null);
        const checkoutLocked = useRef(false);
        const mutationLocked = useRef(false);
        const electronicPaymentLocked = useRef(false);
        const electronicPaymentAttempt = useRef(0);
        const draftSync = useRef(Promise.resolve());
        const store = useMemo(() => posReactOfflineStore.create({
            tenantId,
            configId,
            userId,
            sessionId,
            companyId,
            send: (order) => rpc("pos.order", "pos_react_sync_from_ui", [[order]]),
            isValidAck: (ack, order) => validateCashAck(ack, order, currency.decimalPlaces),
        }), [tenantId, configId, userId, sessionId, companyId, currency.decimalPlaces]);
        const retryTimer = useRef(null);
        const mounted = useRef(false);
        const mutationAllowed = extensions.actions.every((action) => action.canMutate?.({ pluginData, locked }) !== false);
        const refundAllowed = extensions.actions.every((action) => action.canRefund?.({ pluginData, locked }) !== false);
        const lock = () => {
            sessionStorage.removeItem(employeeHintKey);
            sessionStorage.setItem(employeeLockKey, "1");
            setLocked(true);
            setActiveAction(employeePolicy);
        };
        const unlock = (employee) => {
            sessionStorage.setItem(employeeHintKey, String(employee.id));
            sessionStorage.removeItem(employeeLockKey);
            setActiveEmployee(employee);
            setLocked(false);
        };
        const refreshPending = async () => {
            const items = await store.list();
            if (!mounted.current) return;
            setPending(items);
            clearTimeout(retryTimer.current);
            const nextAttemptAt = Math.min(...items.filter(({ status, nextAttemptAt }) => status !== "blocked" && Number.isFinite(nextAttemptAt)).map(({ nextAttemptAt }) => nextAttemptAt));
            if (Number.isFinite(nextAttemptAt)) retryTimer.current = setTimeout(recover, Math.max(0, nextAttemptAt - Date.now()));
        };
        const recover = async () => {
            await store.drain().catch(() => {});
            await refreshPending();
        };
        const lockFinalized = () => {
            checkoutLocked.current = true;
            mutationLocked.current = true;
            setFinalizedAlert("This order was finalized on another device. Editing and checkout are locked.");
        };
        const reconcileDraft = async () => {
            if (mutationLocked.current) return false;
            const { uuid, serverId } = draftIdentity.current;
            const payload = draftPayload.current;
            await draftSync.current.catch(() => {});
            if (mutationLocked.current || uuid !== draftIdentity.current.uuid || payload !== draftPayload.current) return false;
            const active = await rpc("pos.config", "read_config_open_orders", [configId, { "pos.order": [["uuid", "=", uuid]] }, { "pos.order": serverId ? [serverId] : [] }]);
            if (mutationLocked.current || uuid !== draftIdentity.current.uuid || payload !== draftPayload.current) return false;
            const serverOrder = active?.dynamic_records?.["pos.order"]?.find((order) => order.uuid === uuid);
            if ((serverOrder && serverOrder.state !== "draft") || (serverId && active?.deleted_record_ids?.["pos.order"]?.includes(serverId))) {
                lockFinalized();
                return true;
            }
            const query = posReactMetadataGraph.constructOpenOrderQuery(metadataGraph.all("pos.order").filter((order) => !order._deleted), [configId]);
            const response = await rpc("pos.config", "read_config_open_orders", [configId, query.domain, query.recordIds]);
            if (mutationLocked.current || uuid !== draftIdentity.current.uuid || payload !== draftPayload.current) return false;
            const records = Object.fromEntries(Object.entries(response?.dynamic_records || {})
                .filter(([model]) => metadataGraph.models.has(model))
                .map(([model, values]) => [model, values.map((record) => Object.fromEntries(Object.entries(record)
                    .filter(([field]) => field === "id" || metadataGraph.models.get(model).fields.has(field))))]));
            for (const [model, values] of Object.entries(active?.dynamic_records || {})) {
                if (!metadataGraph.models.has(model)) continue;
                const current = records[model] || [];
                const ids = new Set(values.map((record) => record.id));
                records[model] = [...current.filter((record) => !ids.has(record.id)), ...values];
            }
            await metadataGraph.completeRelations(records, (model, ids, fields) => rpc(model, "read", [ids, fields], { load: false }));
            const deletedRecords = Object.fromEntries(Object.entries(response?.deleted_record_ids || {})
                .filter(([model]) => metadataGraph.models.has(model)));
            metadataGraph.mergeDelta({ records, deleted: deletedRecords });
            const order = (serverId ? metadataGraph.get("pos.order", serverId) : null) || metadataGraph.all("pos.order").find((record) => record.uuid === uuid);
            if (order?.id && !serverId) draftIdentity.current.serverId = order.id;
            const deleted = Boolean(order?._deleted);
            const lineSnapshot = (line) => {
                const productId = line.product_id?.id || (Array.isArray(line.product_id) ? line.product_id[0] : (line.product_id || line.productId));
                return {
                    uuid: line.uuid,
                    product_id: productId,
                    qty: line.qty ?? line.quantity,
                    price_unit: line.price_unit ?? line.price,
                    discount: line.discount || 0,
                };
            };
            const localLines = (draftPayload.current?.lines || []).map(([, , line]) => lineSnapshot(line));
            const remoteLines = (order?.lines || []).map(lineSnapshot);
            const changed = order?.state === "draft" && JSON.stringify(remoteLines.sort((a, b) => a.uuid.localeCompare(b.uuid))) !== JSON.stringify(localLines.sort((a, b) => a.uuid.localeCompare(b.uuid)));
            const finalized = Boolean(deleted || changed || (order && order.state !== "draft"));
            if (finalized) lockFinalized();
            return finalized;
        };
        const queueDraftSync = (paidDraft) => {
            const payload = { ...paidDraft, state: "draft", amount_paid: 0, payment_ids: [] };
            const sync = async () => {
                const ack = await rpc("pos.order", "pos_react_sync_from_ui", [[payload]]);
                if (!validateDraftAck(ack, payload, currency.decimalPlaces)) throw new Error("Invalid draft synchronization acknowledgement");
                const records = Object.fromEntries(Object.entries(ack).filter(([model]) => metadataGraph.models.has(model))
                    .map(([model, values]) => [model, values.map((record) => Object.fromEntries(Object.entries(record)
                        .filter(([field]) => field === "id" || metadataGraph.models.get(model).fields.has(field))))]));
                metadataGraph.mergeDelta({ records });
                if (payload.uuid === draftIdentity.current.uuid) draftIdentity.current.serverId = ack["pos.order"][0].id;
            };
            draftSync.current = draftSync.current.catch(() => {}).then(sync);
            return draftSync.current;
        };
        useEffect(() => {
            mounted.current = true;
            if (employeePolicy) {
                const employeeId = Number(sessionStorage.getItem(employeeHintKey));
                if (initiallyLocked) setActiveAction(employeePolicy);
                else if (employeeId) employeePolicy.restore({ rpc, sessionId }, employeeId).then((employee) => {
                    if (mounted.current && employee) unlock(employee);
                    else sessionStorage.removeItem(employeeHintKey);
                }).catch(() => sessionStorage.removeItem(employeeHintKey));
            }
            store.loadDraft(draftId).then((draft) => {
                if (!mounted.current) return;
                if (draft) {
                    draftPayload.current = draft;
                    const restoredCart = draft.lines.map(([, , line]) => {
                        const { product_id: productId, qty: quantity, price_unit: price, tax_ids: taxIds, extra_tax_data: extraTaxData, ...attributes } = line;
                        return { ...attributes, productId, quantity, price, taxIds: taxIds?.[0]?.[2] || taxIds || [], extraTaxData: extraTaxData || {} };
                    });
                    draftIdentity.current = {
                        uuid: draft.uuid,
                        cashPaymentUuid: draft.payment_ids[0]?.[2].uuid || crypto.randomUUID(),
                        electronicPaymentUuid: draft.payment_ids[1]?.[2].uuid || crypto.randomUUID(),
                    };
                    setRestaurantContext({
                        tableId: draft.table_id?.[0] || draft.table_id || false,
                        customerCount: draft.customer_count || false,
                    });
                    setCart(restoredCart);
                    queueDraftSync(draft).catch(() => {});
                    reconcileDraft().catch(() => {});
                }
                setDraftReady(true);
            }).catch((error) => {
                if (mounted.current) setRecoveryError(error?.message || "Could not restore cart draft");
            });
            recover();
            const realtime = posReactRealtime.connect({
                token: accessToken,
                version: websocketWorkerVersion,
                onSynchronisation: recover,
                onStatus: (status) => {
                    if (mounted.current) setRealtimeStatus(status);
                    if (status === "connected") {
                        recover();
                        reconcileDraft().catch(() => {});
                    }
                },
            });
            const reconnect = () => {
                recover();
                reconcileDraft().catch(() => {});
            };
            globalThis.addEventListener("online", reconnect);
            return () => {
                mounted.current = false;
                electronicPaymentAttempt.current += 1;
                clearTimeout(retryTimer.current);
                globalThis.removeEventListener("online", reconnect);
                realtime.close();
                store.close();
            };
        }, [store]);
        const replaceCart = async (next) => {
            if (!mutationAllowed || !draftReady || mutationLocked.current || checkoutLocked.current || !Array.isArray(next)) return false;
            mutationLocked.current = true;
            setMutating(true);
            setRecoveryError("");
            const identity = draftIdentity.current;
            const transformContext = { cart: next, lines: effectiveLines(next, pricedProducts), pluginData, taxContext };
            for (const { value } of plugins.resolve("action")) {
                if (typeof value.transformCart === "function") {
                    transformContext.cart = value.transformCart(transformContext);
                    transformContext.lines = effectiveLines(transformContext.cart, pricedProducts);
                }
            }
            next = transformContext.cart;
            setCart(next);
            try {
                if (next.length) {
                    const paidDraft = buildCashOrder({ cart: next, products: pricedProducts, taxContext, cashRounding, partnerId: customerId, pricelistId: pricelist?.id || false, fiscalPositionId: fiscalPosition?.id || false, ...restaurantContext, sessionId, companyId, employeeId: pluginData.employee?.id || false, cashMethodId, accessToken, ...identity });
                    await store.saveDraft(draftId, paidDraft);
                    draftPayload.current = paidDraft;
                    queueDraftSync(paidDraft).catch(() => {});
                } else {
                    await store.deleteDraft(draftId);
                    await draftSync.current.catch(() => {});
                    await rpc("pos.order", "pos_react_cancel_draft", [identity.uuid, sessionId]);
                    draftIdentity.current = newDraftIdentity();
                }
                return true;
            } catch (error) {
                setRecoveryError(error?.message || "Could not save cart draft");
                return false;
            } finally {
                mutationLocked.current = false;
                setMutating(false);
            }
        };
        const mutateCart = (product, delta, uuid = null) => replaceCart(updateCart(cart, product, delta, uuid));
        const checkoutDraft = async (customPayload = null) => {
            if (!mutationAllowed || checkoutLocked.current || mutationLocked.current || !draftReady || mutating || !total) return false;
            checkoutLocked.current = true;
            mutationLocked.current = true;
            setCheckingOut(true);
            try {
                const snapshotPayload = customPayload || draftPayload.current;
                await store.commitDraft(draftId);
                setLastValidatedOrder(snapshotPayload);
                setCart([]);
                draftIdentity.current = newDraftIdentity();
                await store.drain().catch(() => {});
                await refreshPending();
                return true;
            } finally {
                mutationLocked.current = false;
                checkoutLocked.current = false;
                setCheckingOut(false);
            }
        };
        const checkoutCash = () => cashMethodId ? checkoutDraft() : false;
        const runElectronicPayment = async (adapter, method, retry = false) => {
            if (!mutationAllowed) return;
            const cashSlice = Number(cashAmount);
            const remaining = Number((total - cashSlice).toFixed(currency.decimalPlaces));
            if (!total || cashSlice < 0 || remaining <= 0 || electronicPaymentLocked.current || (electronicPayment && !retry)) return;
            electronicPaymentLocked.current = true;
            const attempt = ++electronicPaymentAttempt.current;
            const payment = retry ? electronicPayment : { method, adapter, amount: remaining, cashAmount: cashSlice, state: "pending" };
            setElectronicPayment(payment);
            setCheckingOut(true);
            setRecoveryError("");
            try {
                const result = await adapter.start({ ...context, payment, pluginData: { ...pluginData, payment } });
                if (!mounted.current || attempt !== electronicPaymentAttempt.current) return;
                const state = paymentState(result);
                setElectronicPayment({ ...payment, adapter, state });
                if (state === "done") {
                    const electronicPaymentData = result && typeof result === "object"
                        ? { transaction_id: result.transaction_id || false, card_type: result.card_type || false }
                        : {};
                    const paidDraft = buildCashOrder({ cart, products: pricedProducts, taxContext, cashRounding, partnerId: customerId, pricelistId: pricelist?.id || false, fiscalPositionId: fiscalPosition?.id || false, ...restaurantContext, sessionId, companyId, employeeId: pluginData.employee?.id || false, cashMethodId, electronicMethodId: method.id, cashAmount: payment.cashAmount, electronicPaymentData, accessToken, ...draftIdentity.current });
                    await store.saveDraft(draftId, paidDraft);
                    draftPayload.current = paidDraft;
                    await queueDraftSync(paidDraft);
                    if (!await checkoutDraft()) throw new Error("Electronic payment could not finalize order");
                }
            } catch (error) {
                if (attempt !== electronicPaymentAttempt.current) return;
                setElectronicPayment({ ...payment, adapter, state: "retry" });
                setRecoveryError(error?.message || "Electronic payment failed");
            } finally {
                if (attempt === electronicPaymentAttempt.current) {
                    electronicPaymentLocked.current = false;
                    setCheckingOut(false);
                }
            }
        };
        const cancelElectronicPayment = async () => {
            if (!mutationAllowed) return;
            const payment = electronicPayment;
            if (!payment || payment.state === "done") return;
            electronicPaymentAttempt.current += 1;
            electronicPaymentLocked.current = false;
            setCheckingOut(true);
            try {
                if (typeof payment.adapter?.cancel === "function") await payment.adapter.cancel({ ...context, payment });
                setElectronicPayment({ ...payment, state: "cancelled" });
            } finally {
                setCheckingOut(false);
            }
        };
        const refundCash = async () => {
            if (!mutationAllowed || !refundAllowed) return;
            const quantity = Number(refundQty);
            if (!refundLine || !Number.isFinite(quantity) || quantity <= 0 || quantity > refundLine.remaining) return;
            setCheckingOut(true);
            setRecoveryError("");
            try {
                const config = pluginData.discount;
                const refundUuid = crypto.randomUUID();
                const refundProducts = [{ id: refundLine.product_id, price: refundLine.price_unit, taxIds: refundLine.tax_ids || [] }];
                let refundCart = [{ uuid: refundUuid, productId: refundLine.product_id, quantity: -quantity }];
                if (config?.enabled && config.product) {
                    const [sourceDiscount] = await rpc("pos.order.line", "search_read", [[
                        ["order_id", "=", refundLine.order_id],
                        ["product_id", "=", config.product.id],
                    ], ["extra_tax_data"], 0, 1, "id"]);
                    const percentage = sourceDiscount?.extra_tax_data?.discount_percentage;
                    if (Number.isFinite(percentage)) {
                        refundProducts.push({ id: config.product.id, price: 0, taxIds: [] });
                        const transformContext = { cart: refundCart, lines: effectiveLines(refundCart, refundProducts), pluginData, taxContext };
                        for (const { value } of plugins.resolve("action")) {
                            if (typeof value.transformCart === "function") {
                                transformContext.cart = value.transformCart(transformContext, percentage);
                                transformContext.lines = effectiveLines(transformContext.cart, refundProducts);
                            }
                        }
                        refundCart = transformContext.cart;
                    }
                }
                const preview = buildCashOrder({ cart: refundCart, products: refundProducts, taxContext, sessionId, companyId, cashMethodId, accessToken });
                const refundAmount = preview.amount_total;
                const sourcePayments = await rpc("pos.payment", "search_read", [[
                    ["pos_order_id", "=", refundLine.order_id],
                    ["transaction_id", "!=", false],
                    ["amount", ">=", Math.abs(refundAmount)],
                ], ["payment_method_id", "transaction_id"], 0, false, "id"]);
                const source = sourcePayments.map((payment) => {
                    const method = electronicPaymentMethods.find(({ id }) => id === payment.payment_method_id[0]);
                    const adapter = method && extensions.payments.find(({ id, refund }) => id === method.terminal && typeof refund === "function");
                    return adapter && { payment, method, adapter };
                }).find(Boolean);
                const method = source?.method;
                const result = source && await source.adapter.refund({ ...context, payment: {
                    method,
                    amount: refundAmount,
                    transaction_id: source.payment.transaction_id,
                }});
                const payload = buildCashOrder({
                    cart: refundCart,
                    products: refundProducts,
                    taxContext,
                    sessionId,
                    companyId,
                    employeeId: pluginData.employee?.id || false,
                    cashMethodId,
                    electronicMethodId: method?.id || false,
                    cashAmount: source ? 0 : undefined,
                    electronicPaymentData: source ? { transaction_id: result.transaction_id } : {},
                    accessToken,
                });
                payload.is_refund = true;
                payload.lines[0][2].refunded_orderline_id = refundLine.id;
                await rpc("pos.order", "pos_react_sync_from_ui", [[payload]]);
                setRefundLine(null);
            } catch (error) {
                setRecoveryError(error?.message || "Could not refund order line");
            } finally {
                setCheckingOut(false);
            }
        };
        const recoveryAction = async (id, label, action) => {
            setRecoveryError("");
            setRecoveryBusy(`${label} order ${id}`);
            try {
                await action();
            } catch (error) {
                setRecoveryError(error?.message || `Could not ${label.toLowerCase()} order ${id}`);
            } finally {
                setRecoveryBusy("");
            }
        };
        const exportPending = (id) => recoveryAction(id, "Exporting", async () => {
            const exported = await store.exportRecord(id);
            const link = document.createElement("a");
            link.href = URL.createObjectURL(new Blob([JSON.stringify(exported, null, 2)], { type: "application/json" }));
            link.download = `pos-order-${id}.json`;
            link.click();
            URL.revokeObjectURL(link.href);
            setExportProofs((proofs) => ({ ...proofs, [id]: exported.proof }));
            setRecoveryMessage(`Order ${id} exported. Type its exact ID to delete its local copy.`);
        });
        const deletePending = (id) => recoveryAction(id, "Deleting", async () => {
            await store.deleteExported(id, exportProofs[id], deleteConfirmations[id]);
            setRecoveryMessage(`Order ${id} deleted from this device.`);
            setDeleteConfirmations((values) => ({ ...values, [id]: "" }));
            await refreshPending();
        });
        const retryPending = (id) => recoveryAction(id, "Retrying", async () => {
            await store.retryNow(id);
            await refreshPending();
        });
        const startRefund = async () => {
            if (!mutationAllowed) return;
            setRecoveryError("");
            try {
                const [line] = await rpc("pos.order.line", "search_read", [[['order_id.state', 'in', ['paid', 'done']], ['qty', '>', 0]], ['id', 'order_id', 'product_id', 'qty', 'refunded_qty', 'price_unit', 'tax_ids'], 0, 1, 'id desc']);
                if (!line || line.qty <= line.refunded_qty) throw new Error("No refundable cash sale found");
                setRefundLine({ ...line, order_id: line.order_id[0], product_id: line.product_id[0], remaining: line.qty - line.refunded_qty });
                setRefundQty(1);
            } catch (error) {
                setRecoveryError(error?.message || "Could not load refundable sale");
            }
        };
        const normalizedQuery = query.trim().toLocaleLowerCase();
        const visible = pricedProducts.filter((product) =>
            (!categoryId || product.categoryIds.includes(categoryId)) &&
            (!normalizedQuery || product.name.toLocaleLowerCase().includes(normalizedQuery))
        );
        const lines = effectiveLines(cart, pricedProducts);
        const amounts = useMemo(() => PosReactTaxEngine.computeLines(lines.map(({ product, quantity, price = product.price, taxIds = product.taxIds, discount = 0, extraTaxData = {} }) => ({ product, price, quantity, discount, taxIds, extraTaxData })), taxContext), [cart, pricedProducts, taxContext]);
        const total = amounts.total;
        const selectedLine = lines.find((l) => l.uuid === selectedLineUuid) || (lines.length ? lines[lines.length - 1] : null);

        const handleSelectTab = (tabId) => {
            if (tabId === activeTabId) return;
            setTabCarts((prev) => ({ ...prev, [activeTabId]: cart }));
            setTabContexts((prev) => ({ ...prev, [activeTabId]: { restaurantContext, customerId, orderNote } }));
            setCart(tabCarts[tabId] || []);
            setRestaurantContext(tabContexts[tabId]?.restaurantContext || { tableId: false, customerCount: false });
            setCustomerId(tabContexts[tabId]?.customerId || false);
            setOrderNote(tabContexts[tabId]?.orderNote || "");
            setActiveTabId(tabId);
            setSelectedLineUuid(null);
            setNumpadBuffer("");
        };
        const handleAddTab = () => {
            const nextId = Math.max(...orderTabs.map((t) => t.id), 0) + 1;
            setTabCarts((prev) => ({ ...prev, [activeTabId]: cart }));
            setTabContexts((prev) => ({ ...prev, [activeTabId]: { restaurantContext, customerId, orderNote } }));
            setOrderTabs([...orderTabs, { id: nextId, name: `Order ${nextId}` }]);
            setActiveTabId(nextId);
            setCart([]);
            setRestaurantContext({ tableId: false, customerCount: false });
            setCustomerId(false);
            setOrderNote("");
            setSelectedLineUuid(null);
            setNumpadBuffer("");
        };
        const handleCloseTab = (e, tabId) => {
            e.stopPropagation();
            if (orderTabs.length <= 1) return;
            const remaining = orderTabs.filter((t) => t.id !== tabId);
            setOrderTabs(remaining);
            const nextCarts = { ...tabCarts };
            delete nextCarts[tabId];
            setTabCarts(nextCarts);
            const nextContexts = { ...tabContexts };
            delete nextContexts[tabId];
            setTabContexts(nextContexts);
            if (activeTabId === tabId) {
                const nextActiveId = remaining[remaining.length - 1].id;
                setActiveTabId(nextActiveId);
                setCart(tabCarts[nextActiveId] || []);
                setRestaurantContext(tabContexts[nextActiveId]?.restaurantContext || { tableId: false, customerCount: false });
                setCustomerId(tabContexts[nextActiveId]?.customerId || false);
                setOrderNote(tabContexts[nextActiveId]?.orderNote || "");
            }
        };

        const handleOrderKitchen = () => {
            if (!cart.length || !mutationAllowed) return;
            const currentTable = restaurantContext?.tableNumber || restaurantContext?.tableId
                ? `Table ${restaurantContext.tableNumber || restaurantContext.tableId}`
                : "Takeout";
            const currentOrderNum = orderTabs.find((t) => t.id === activeTabId)?.name || `#${activeTabId}`;

            if (window.posReactKitchenService) {
                window.posReactKitchenService.dispatchOrder({
                    orderNumber: currentOrderNum,
                    tableNumber: currentTable,
                    lines: lines.map((l) => ({ name: l.product.name, qty: l.quantity, note: l.note })),
                    note: orderNote,
                });
            }

            const nowTime = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
            const updatedCart = cart.map((item) => ({ ...item, kitchenSent: true, kitchenSentAt: nowTime }));
            replaceCart(updatedCart);
        };

        const handleNumpadInput = (val) => {
            if (!selectedLine || !mutationAllowed) return;
            const targetUuid = selectedLine.uuid;
            if (val === "+/-") {
                if (numpadMode === "qty") {
                    const newQty = -selectedLine.quantity;
                    replaceCart(cart.map((item) => item.uuid === targetUuid ? { ...item, quantity: newQty } : item));
                }
                return;
            }

            let nextStr = (numpadBuffer ? numpadBuffer : "") + val;
            if (val === "." && numpadBuffer.includes(".")) return;
            setNumpadBuffer(nextStr);

            const num = parseFloat(nextStr);
            if (Number.isFinite(num)) {
                if (numpadMode === "qty") {
                    replaceCart(cart.map((item) => item.uuid === targetUuid ? { ...item, quantity: num } : item));
                } else if (numpadMode === "% Disc") {
                    const discount = Math.min(100, Math.max(0, num));
                    replaceCart(cart.map((item) => item.uuid === targetUuid ? { ...item, discount } : item));
                } else if (numpadMode === "Price") {
                    replaceCart(cart.map((item) => item.uuid === targetUuid ? { ...item, price: num, isCustom: true } : item));
                }
            }
        };

        const handleNumpadDelete = () => {
            if (!selectedLine || !mutationAllowed) return;
            const targetUuid = selectedLine.uuid;
            if (numpadBuffer.length > 0) {
                const nextStr = numpadBuffer.slice(0, -1);
                setNumpadBuffer(nextStr);
                if (nextStr.length === 0) {
                    if (numpadMode === "qty") {
                        replaceCart(cart.filter((item) => item.uuid !== targetUuid));
                    }
                } else {
                    const num = parseFloat(nextStr);
                    if (Number.isFinite(num)) {
                        if (numpadMode === "qty") {
                            replaceCart(cart.map((item) => item.uuid === targetUuid ? { ...item, quantity: num } : item));
                        } else if (numpadMode === "% Disc") {
                            replaceCart(cart.map((item) => item.uuid === targetUuid ? { ...item, discount: num } : item));
                        } else if (numpadMode === "Price") {
                            replaceCart(cart.map((item) => item.uuid === targetUuid ? { ...item, price: num, isCustom: true } : item));
                        }
                    }
                }
            } else {
                replaceCart(cart.filter((item) => item.uuid !== targetUuid));
            }
        };

        const handleNumpadClear = () => {
            setNumpadBuffer("");
        };

        const handleQuickCreatePartner = async ({ name, phone, email }) => {
            try {
                const partnerId = await rpc("res.partner", "create", [{
                    name,
                    phone: phone || false,
                    email: email || false,
                }]);
                if (partnerId) {
                    const [created] = await rpc("res.partner", "read", [[partnerId], ["id", "name", "display_name", "phone", "email", "vat"]]);
                    if (created) {
                        metadataGraph.mergeDelta({ records: { [partnerModel]: [created] } });
                        return created;
                    }
                }
            } catch (err) {
                setRecoveryError(err?.message || "Failed to create partner");
            }
            return null;
        };

        const handlePaymentValidate = async ({ paymentLines, toInvoice, change }) => {
            setCheckingOut(true);
            setRecoveryError("");
            try {
                const cashLine = paymentLines.find((l) => l.isCash);
                const electronicLine = paymentLines.find((l) => !l.isCash);
                const cashSlice = cashLine ? cashLine.amount : 0;

                const paidDraft = buildCashOrder({
                    cart,
                    products: pricedProducts,
                    taxContext,
                    cashRounding,
                    partnerId: customerId,
                    pricelistId: pricelist?.id || false,
                    fiscalPositionId: fiscalPosition?.id || false,
                    ...restaurantContext,
                    sessionId,
                    companyId,
                    employeeId: pluginData.employee?.id || false,
                    cashMethodId: cashMethodId || (cashLine?.methodId || false),
                    electronicMethodId: electronicLine?.methodId || false,
                    cashAmount: cashSlice,
                    electronicPaymentData: electronicLine ? { transaction_id: electronicLine.id } : {},
                    accessToken,
                    ...draftIdentity.current
                });

                if (orderNote) {
                    paidDraft.general_customer_note = orderNote;
                }

                await store.saveDraft(draftId, paidDraft);
                draftPayload.current = paidDraft;
                await queueDraftSync(paidDraft);
                const committed = await checkoutDraft(paidDraft);
                if (!committed) throw new Error("Could not finalize payment draft");
                setLastValidatedOrder(paidDraft);
                setScreen("receipt");
            } catch (err) {
                setRecoveryError(err?.message || "Payment validation failed");
                throw err;
            } finally {
                setCheckingOut(false);
            }
        };

        const handleNewOrder = () => {
            setCart([]);
            setOrderNote("");
            setSelectedLineUuid(null);
            setLastValidatedOrder(null);
            setNumpadBuffer("");
            setRestaurantContext({ tableId: false, customerCount: false });
            setCustomerId(false);
            setScreen(null);
        };

        const context = { cart, lines: amounts.lines, total, sessionId, pluginData, locked, lock, unlock, metadataGraph, formatMoney, setScreen, reportError: setRecoveryError, closeAction: () => {
            setActiveAction(null);
            requestAnimationFrame(() => actionTriggerRef.current?.focus());
        }, rpc, doAction, replaceCart, taxContext, restaurant: INITIAL_DATA.restaurant, restaurantContext: { ...restaurantContext, locked: Boolean(cart.length) }, setRestaurantContext: (values) => {
            if (mutationAllowed) setRestaurantContext((current) => ({ ...current, ...values }));
        }, allowProductCreation: async () => mutationAllowed && allowProductCreation };

        const activeScreen = extensions.screens.find(({ id }) => id === screen);
        if (activeScreen) return component(activeScreen, context);

        if (screen === "payment" && window.PosReactPaymentScreen) {
            return h(window.PosReactPaymentScreen, {
                context: { ...context, currency, cashMethodId, electronicPaymentMethods, customer, configName },
                onValidate: handlePaymentValidate,
                onBack: () => setScreen(null),
                onCustomerClick: () => setShowCustomerModal(true),
            });
        }

        if (screen === "receipt" && window.PosReactReceiptScreen) {
            return h(window.PosReactReceiptScreen, {
                order: lastValidatedOrder || draftPayload.current,
                context: { ...context, products: pricedProducts, company, currency, formatMoney, cashierName: activeEmployee?.name || pluginData.employee?.name || "Cashier", customer, configName },
                onNewOrder: handleNewOrder,
            });
        }

        return h("div", { className: "pos-shell" },
            // Fiori / Carbon Top Navigation Header
            h("header", { className: "pos-header" },
                h("div", { className: "pos-header-left" },
                    h("div", { className: "pos-brand-title" },
                        h("span", { style: { color: "var(--pos-accent)", fontSize: "18px" } }, "⚡"),
                        h("span", null, configName),
                        h("span", { className: "pos-brand-badge" }, "React POS")
                    ),
                    // Multi-Order Tabs
                    h("div", { className: "pos-order-tabs", role: "tablist", "aria-label": "Active Orders" },
                        orderTabs.map((tab) =>
                            h("button", {
                                key: tab.id,
                                type: "button",
                                role: "tab",
                                "aria-selected": activeTabId === tab.id,
                                className: `pos-order-tab ${activeTabId === tab.id ? "active" : ""}`,
                                onClick: () => handleSelectTab(tab.id),
                            },
                                h("span", null, tab.name),
                                orderTabs.length > 1 ? h("span", {
                                    className: "pos-order-tab-close",
                                    title: "Close order tab",
                                    onClick: (e) => handleCloseTab(e, tab.id),
                                }, "×") : null
                            )
                        ),
                        h("button", {
                            type: "button",
                            className: "pos-order-tab-add",
                            title: "New order tab",
                            onClick: handleAddTab,
                        }, "+")
                    ),
                    // Table Floor Plan Button
                    h("button", {
                        type: "button",
                        className: `pos-table-indicator-btn ${restaurantContext?.tableId ? "has-table" : ""}`,
                        onClick: () => setScreen("pos_react.restaurant.floor"),
                        title: "Restaurant Floor Plan"
                    },
                        h("span", null, "🪑"),
                        h("span", null, restaurantContext?.tableId ? `Table ${restaurantContext.tableNumber || restaurantContext.tableId} (${restaurantContext.customerCount || 2}p)` : "Floor Plan")
                    )
                ),
                h("div", { className: "pos-header-right" },
                    // Kitchen Prep Screen Shortcut
                    h("button", {
                        type: "button",
                        className: "pos-header-btn",
                        style: { display: "flex", alignItems: "center", gap: "6px" },
                        onClick: () => setScreen("pos_react.kitchen.display"),
                        title: "Kitchen & Bar Preparation Display Screen"
                    },
                        h("span", null, "👨‍🍳"),
                        h("span", null, "Kitchen Prep")
                    ),
                    // Realtime Connection Pulse
                    h("div", { className: "pos-sync-indicator", role: "status", "aria-label": "Realtime connection" },
                        h("span", { className: `pos-sync-dot ${realtimeStatus === "connected" ? "connected" : (realtimeStatus === "connecting" ? "connecting" : "offline")}` }),
                        h("span", null, realtimeStatus === "connected" ? "Sync Live" : realtimeStatus)
                    ),
                    // Cashier Pill
                    h("button", {
                        type: "button",
                        className: "pos-cashier-pill",
                        onClick: lock,
                        title: "Current cashier (Click to lock)",
                    },
                        h("span", null, "👤"),
                        h("span", null, activeEmployee?.name || pluginData.employee?.name || "Cashier")
                    ),
                    // Extension Actions (e.g. Sales summary, barcode lookup)
                    extensions.actions.filter((action) => action.isVisible?.(context) !== false).map((action) => {
                        if ((!action.component && typeof action.run !== "function") || typeof action.label !== "string") throw new Error(`Invalid POS React action: ${action.id}`);
                        return h("button", {
                            key: action.id,
                            className: "pos-header-btn",
                            "data-action-id": action.id,
                            disabled: locked && action !== employeePolicy,
                            onClick: (event) => {
                                if (action.component) {
                                    actionTriggerRef.current = event.currentTarget;
                                    setActiveAction(action);
                                } else {
                                    action.run(context);
                                }
                            }
                        }, action.label);
                    })
                )
            ),
            activeAction ? component(activeAction, context) : null,
            extensions.slots.filter(({ slot }) => slot === "header").map((slot) => component(slot, context)),

            // Main Dual-Pane Workspace
            h("div", { className: "pos-workspace workspace" },
                // Left Pane: Catalog, Categories & Products Grid
                h("div", { className: "pos-pane-catalog" },
                    // Toolbar: Search & Customer dropdown
                    h("div", { className: "pos-catalog-toolbar" },
                        h("div", { className: "pos-search-wrapper" },
                            h("span", { className: "pos-search-icon" }, "🔍"),
                            h("input", {
                                type: "search",
                                className: "pos-search-input",
                                value: query,
                                placeholder: "Search products",
                                "aria-label": "Search products",
                                onChange: (event) => setQuery(event.target.value)
                            })
                        ),
                        // Customer select dropdown (backward-compatible with E2E tests)
                        h("select", {
                            value: customerId || "",
                            "aria-label": "Customer",
                            disabled: Boolean(cart.length),
                            className: "pos-header-btn",
                            style: { maxWidth: "220px", textOverflow: "ellipsis" },
                            onChange: (event) => setCustomerId(Number(event.target.value) || false)
                        },
                            h("option", { value: "" }, "No customer"),
                            customers.map((partner) => h("option", { key: partner.id, value: partner.id }, partner.display_name || partner.name))
                        )
                    ),
                    // Categories horizontal bar
                    h("nav", { className: "pos-categories-bar", "aria-label": "Product categories" },
                        h("button", { type: "button", className: `pos-category-chip ${categoryId === null ? "active" : ""}`, onClick: () => setCategoryId(null) }, "All"),
                        categories.map((category) => h("button", { key: category.id, type: "button", className: `pos-category-chip ${category.id === categoryId ? "active" : ""}`, onClick: () => setCategoryId(category.id) }, category.name)),
                        extensions.screens.map((item) => h("button", { key: item.id, type: "button", className: "pos-category-chip", onClick: () => setScreen(item.id) }, item.label || item.id))
                    ),
                    extensions.slots.filter(({ slot }) => slot === "beforeProducts").map((slot) => component(slot, context)),
                    // Products Grid
                    h("div", { className: "pos-product-grid products" },
                        visible.map((product) =>
                            h("button", {
                                key: product.id,
                                type: "button",
                                className: "pos-product-card product",
                                disabled: !draftReady || mutating || checkingOut || Boolean(finalizedAlert),
                                onClick: () => {
                                    mutateCart(product, 1);
                                }
                            },
                                h("strong", { className: "pos-product-name" }, product.name),
                                h("span", { className: "pos-product-price" }, formatMoney(product.price))
                            )
                        )
                    )
                ),

                // Right Pane: Cart, Orderlines & Numpad Keypad (aside)
                h("aside", { className: "pos-pane-cart" },
                    h("h2", { style: { display: "none" } }, "Cart"),
                    // Customer & Table summary bar
                    h("div", { className: "pos-cart-customer-bar" },
                        h("button", {
                            type: "button",
                            className: "pos-customer-selector-btn",
                            onClick: () => setShowCustomerModal(true),
                            title: "Select customer"
                        },
                            h("span", null, "👤"),
                            h("span", null, customer ? (customer.name || customer.display_name) : "Walk-in Guest")
                        ),
                        restaurantContext?.tableId ? h("button", {
                            type: "button",
                            className: "pos-table-chip",
                            onClick: () => setScreen("pos_react.restaurant.floor"),
                            title: "Change Table"
                        }, `🪑 T${restaurantContext.tableNumber || restaurantContext.tableId} (${restaurantContext.customerCount || 2}p)`) : null,
                        orderNote ? h("span", { style: { fontSize: "11px", color: "var(--pos-accent)", cursor: "pointer" }, onClick: () => setShowNoteModal(true) }, `📝 Note`) : null
                    ),
                    extensions.slots.filter(({ slot }) => slot === "cartControls").map((slot) => component(slot, context)),

                    // Cart Lines List
                    h("div", { className: "pos-cart-lines" },
                        lines.length ? lines.map((line) => {
                            const isSelected = line.uuid === selectedLine?.uuid;
                            return h("div", {
                                key: line.uuid,
                                className: `pos-cart-line line ${isSelected ? "active" : ""}`,
                                onClick: () => {
                                    setSelectedLineUuid(line.uuid);
                                    setNumpadBuffer("");
                                }
                            },
                                h("div", { className: "pos-cart-line-main" },
                                    h("span", { className: "pos-cart-line-title" }, `${line.product.name} × ${line.quantity}`),
                                    line.discount ? h("span", { className: "pos-cart-line-discount-tag" }, `Discount: ${line.discount}%`) : null,
                                    line.extraTaxData?.discount_percentage ? h("span", { className: "pos-cart-line-discount-tag" }, `Special Disc: ${line.extraTaxData.discount_percentage}%`) : null,
                                    line.kitchenSent ? h("span", { className: "pos-cart-line-kitchen-badge" }, `🍳 Kitchen Sent (${line.kitchenSentAt || "Now"})`) : null,
                                    h("span", { className: "pos-cart-line-desc" }, `Unit: ${formatMoney(line.price)}`)
                                ),
                                h("span", { className: "pos-cart-line-total" }, formatMoney(line.total || (line.price * line.quantity))),
                                extensions.actions.every((action) => action.canMutateLine?.(line, context) !== false)
                                    ? h("button", {
                                        type: "button",
                                        className: "pos-order-tab-close",
                                        "aria-label": `Remove one ${line.product.name}`,
                                        disabled: !draftReady || mutating || checkingOut || Boolean(finalizedAlert),
                                        onClick: (e) => {
                                            e.stopPropagation();
                                            mutateCart(line.product, -1, line.uuid);
                                        }
                                    }, "−")
                                    : null
                            );
                        }) : h("div", { className: "pos-cart-empty" },
                            h("span", { style: { fontSize: "32px", opacity: 0.5 } }, "🛒"),
                            h("p", null, "Cart is empty")
                        )
                    ),

                    // Quick Cash First input (kept for test compatibility)
                    h("div", { style: { padding: "6px 16px", background: "var(--pos-bg-card)", borderTop: "1px solid var(--pos-border)", display: "flex", justifyContent: "space-between", alignItems: "center" } },
                        h("label", { style: { fontSize: "12px", color: "var(--pos-text-secondary)" } }, "Cash first"),
                        h("input", {
                            type: "number",
                            min: 0,
                            max: total,
                            step: currency.rounding,
                            value: cashAmount,
                            disabled: checkingOut || Boolean(electronicPayment),
                            "aria-label": "Cash amount",
                            style: { width: "100px", background: "var(--pos-bg-surface)", border: "1px solid var(--pos-border)", borderRadius: "4px", padding: "4px 8px", color: "var(--pos-text-primary)", textAlign: "right" },
                            onChange: (event) => setCashAmount(event.target.value)
                        })
                    ),

                    // Cart Summary (Subtotal & Total)
                    h("div", { className: "pos-cart-summary" },
                        h("div", { className: "pos-summary-row" },
                            h("span", null, `${lines.reduce((s, l) => s + l.quantity, 0)} items`),
                            h("span", null, formatMoney(total))
                        ),
                        h("div", { className: "pos-summary-row total-row" },
                            h("span", null, "Total"),
                            h("span", { style: { color: "var(--pos-accent)" } }, formatMoney(total))
                        )
                    ),

                    // Tactile 4x4 Numpad Keypad & Action Bar
                    typeof window.PosReactNumpad === "function" ? h(window.PosReactNumpad, {
                        activeMode: numpadMode,
                        setMode: (mode) => {
                            setNumpadMode(mode);
                            setNumpadBuffer("");
                        },
                        onInput: handleNumpadInput,
                        onDelete: handleNumpadDelete,
                        onClear: handleNumpadClear,
                        onCustomerClick: () => setShowCustomerModal(true),
                        onNoteClick: () => setShowNoteModal(true),
                        onRefundClick: startRefund,
                        onPayClick: () => setScreen("payment"),
                        disabled: !draftReady || mutating || checkingOut || Boolean(finalizedAlert),
                        total,
                        formatMoney,
                        selectedLine,
                        customerName: customer ? (customer.name || customer.display_name) : null,
                    }) : null,

                    // Quick "Pay cash", "Order kitchen" and "Refund cash" buttons for test and fast checkout
                    h("div", { style: { display: "flex", gap: "8px", padding: "8px 12px", background: "var(--pos-bg-card)", borderTop: "1px solid var(--pos-border)" } },
                        refundAllowed ? h("button", {
                            type: "button",
                            className: "pos-header-btn",
                            style: { flex: 1 },
                            disabled: locked || checkingOut || Boolean(cart.length),
                            onClick: startRefund
                        }, "Refund cash") : null,
                        h("button", {
                            type: "button",
                            className: "pos-action-btn kitchen-btn",
                            style: { flex: 1.2, height: "40px", display: "flex", alignItems: "center", justifyContent: "center", gap: "6px", fontWeight: 700 },
                            disabled: !lines.length || !draftReady || mutating || checkingOut,
                            onClick: handleOrderKitchen,
                            title: "Send order to kitchen and bar displays"
                        },
                            h("span", null, "👨‍🍳"),
                            h("span", null, lines.some((l) => l.kitchenSent) ? "Resend Kitchen" : "Order Kitchen")
                        ),
                        h("button", {
                            type: "button",
                            className: "pos-action-btn pay-btn",
                            style: { flex: 2, height: "40px" },
                            disabled: !draftReady || mutating || checkingOut || Boolean(finalizedAlert) || !cashMethodId || !total,
                            onClick: checkoutCash
                        }, checkingOut ? "Processing…" : "Pay cash")
                    ),

                    // Refund Line Drawer
                    refundAllowed && refundLine ? h("section", { "aria-label": "Cash refund", style: { padding: "8px 12px", background: "var(--pos-bg-card)", borderTop: "1px solid var(--pos-border)" } },
                        h("label", null, `Refund quantity (max ${refundLine.remaining})`,
                            h("input", { type: "number", min: 0.01, max: refundLine.remaining, step: 0.01, value: refundQty, "aria-label": "Refund quantity", onChange: (event) => setRefundQty(event.target.value) })
                        ),
                        h("button", { disabled: checkingOut || !(Number(refundQty) > 0) || Number(refundQty) > refundLine.remaining, onClick: refundCash }, "Confirm cash refund")
                    ) : null,

                    // Electronic Payment Status
                    electronicPayment ? h("section", { "aria-label": "Electronic payment", role: "status", "aria-live": "polite", style: { padding: "8px 12px", background: "var(--pos-bg-card)" } },
                        h("p", null, `${electronicPayment.method.name}: ${electronicPayment.state}`),
                        electronicPayment.state === "retry" ? h("button", { disabled: checkingOut, onClick: () => runElectronicPayment(electronicPayment.adapter, electronicPayment.method, true) }, "Retry") : null,
                        !["done", "cancelled"].includes(electronicPayment.state) ? h("button", { onClick: cancelElectronicPayment }, "Cancel") : null,
                        electronicPayment.state === "cancelled" ? h("button", { disabled: checkingOut, onClick: () => setElectronicPayment(null) }, "New payment") : null
                    ) : null,

                    // Recovery Section
                    pending.length ? h("section", { className: "recovery", "aria-labelledby": "recovery-title", style: { padding: "8px 12px" } },
                        h("h3", { id: "recovery-title" }, `${pending.length} order${pending.length === 1 ? "" : "s"} need recovery`),
                        pending.map((item) => h("div", { className: "recovery-item", key: item.id },
                            h("span", null, `${item.id} — ${item.status}`),
                            h("div", null,
                                h("button", { disabled: Boolean(recoveryBusy), onClick: () => retryPending(item.id) }, "Retry"),
                                h("button", { disabled: Boolean(recoveryBusy), onClick: () => exportPending(item.id) }, "Export"),
                                exportProofs[item.id] ? h("label", null, `Type ${item.id} to confirm deletion`,
                                    h("input", { value: deleteConfirmations[item.id] || "", "aria-label": `Type exact order ID ${item.id} to confirm deletion`, onChange: (event) => setDeleteConfirmations((values) => ({ ...values, [item.id]: event.target.value })) })
                                ) : null,
                                h("button", { disabled: Boolean(recoveryBusy) || !exportProofs[item.id] || deleteConfirmations[item.id] !== item.id, onClick: () => deletePending(item.id) }, "Delete exported copy")
                            )
                        ))
                    ) : null,

                    // Status and Alert notifications
                    h("p", { role: "status", "aria-label": "Recovery operation", "aria-live": "polite", style: { margin: "2px 8px", fontSize: "11px", color: "var(--pos-accent)" } }, recoveryBusy),
                    h("p", { role: "alert", "aria-label": "Finalized order", "aria-live": "assertive", style: { margin: "2px 8px", fontSize: "11px", color: "var(--pos-danger)" } }, finalizedAlert),
                    h("p", { role: "alert", "aria-label": "Recovery error", "aria-live": "assertive", style: { margin: "2px 8px", fontSize: "11px", color: "var(--pos-danger)" } }, recoveryError),
                    h("p", { role: "status", "aria-label": "Pending orders", "aria-live": "polite", style: { margin: "2px 8px", fontSize: "11px", color: "var(--pos-text-muted)" } }, recoveryMessage || (pending.length ? `${pending.length} order${pending.length === 1 ? "" : "s"} pending sync` : "")),
                    // Hidden footer for backward compatibility
                    h("footer", { style: { display: "none" } }, h("strong", null, "Total"), h("strong", null, formatMoney(total)))
                )
            ),

            // Modal Overlays
            showCustomerModal && window.PosReactModals?.CustomerModal ? h(window.PosReactModals.CustomerModal, {
                customers,
                customerId,
                onSelect: (id) => setCustomerId(id),
                onClose: () => setShowCustomerModal(false),
                onQuickCreate: handleQuickCreatePartner,
            }) : null,

            showNoteModal && window.PosReactModals?.NoteModal ? h(window.PosReactModals.NoteModal, {
                initialNote: orderNote,
                onSave: (note) => {
                    setOrderNote(note);
                    setShowNoteModal(false);
                },
                onClose: () => setShowNoteModal(false),
            }) : null,

            extensions.slots.filter(({ slot }) => slot === "footer").map((slot) => component(slot, context))
        );
    }

    const root = document.getElementById("pos-react-root");
    posReactOfflineStore.loadMetadata(INITIAL_DATA, () => rpc("pos.session", "load_data_params", [INITIAL_DATA.sessionId])).then(async (metadata) => {
        const uniqueModels = new Set(["pos.session", "rs.users", "res.users", "rs.company", "res.company", "organization.unit"]);
        const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(`${metadata.hash}:${INITIAL_DATA.lastDataChange}`));
        const catalogHash = [...new Uint8Array(digest)].map((byte) => byte.toString(16).padStart(2, "0")).join("");
        const catalog = await posReactOfflineStore.loadRecords(INITIAL_DATA, async (cursor, idsByModel) => {
            const loaded = await rpc("pos.session", "load_data", [INITIAL_DATA.sessionId, []], { context: { pos_last_server_date: cursor || false } });
            const records = Object.fromEntries(Object.entries(loaded).map(([model, values]) => [model, [...new Map(values.map((record) => [String(record.id), record])).values()]]));
            const deleted = await rpc("pos.session", "filter_local_data", [INITIAL_DATA.sessionId, {
                "product.template": idsByModel["product.template"] || [],
                "product.product": idsByModel["product.product"] || [],
            }]);
            const serverDate = records["pos.config"]?.[0]?._data_server_date || cursor;
            return {
                records,
                deleted,
                replace: Object.keys(records).filter((model) => uniqueModels.has(model) && records[model].length),
                cursor: serverDate,
                hash: catalogHash,
            };
        }, { hash: catalogHash });
        const metadataGraph = posReactMetadataGraph.create(metadata.data);
        const graphRecords = Object.fromEntries(Object.entries(catalog.records).map(([model, records]) => [model, metadataGraph.mergeMany(model, records.map((record) => Object.fromEntries(Object.entries(record).filter(([field]) => field === "id" || metadataGraph.models.get(model)?.fields.has(field)))))]));
        const ids = (records) => (records || []).map(({ id }) => id);
        const products = (graphRecords["product.product"] || []).map((product) => ({
            id: product.id,
            name: product.display_name,
            price: product.lst_price,
            lst_price: product.lst_price,
            categoryIds: ids(product.product_tmpl_id?.pos_categ_ids),
            parentCategories: ids(product.product_tmpl_id?.categ_id?.parent_path ? metadataGraph.all("product.category").filter((category) => product.product_tmpl_id.categ_id.parent_path.split("/").includes(String(category.id))) : [product.product_tmpl_id?.categ_id].filter(Boolean)),
            product_tmpl_id: product.product_tmpl_id,
            standard_price: product.standard_price,
            taxIds: ids(product.taxes_id?.length ? product.taxes_id : product.product_tmpl_id?.taxes_id),
        }));
        const categories = (graphRecords["pos.category"] || []).map(({ id, name }) => ({ id, name }));
        const dto = { ...INITIAL_DATA, products, categories, metadataGraph };
        ReactDOM.createRoot(root).render(h(App, { configName: root.dataset.configName, ...applyDataRequirements(dto) }));
        if (navigator.onLine && "serviceWorker" in navigator) {
            navigator.serviceWorker.register("/pos/react/service-worker.js", { scope: "/pos/react/" }).then(async (registration) => {
                const worker = registration.active || await navigator.serviceWorker.ready.then(({ active }) => active);
                const assets = [...document.querySelectorAll('script[src], link[rel="stylesheet"][href]')].map((node) => node.src || node.href);
                worker?.postMessage({ type: "CACHE_NAVIGATION", url: location.href, assets, owner: `${INITIAL_DATA.tenantId}:${INITIAL_DATA.userId}` });
            }).catch(() => {});
        }
        window.posReact = Object.freeze({ updateCart, effectiveLines, buildCashOrder, validateCashAck, rpc, metadata, metadataGraph, catalog });
    }).catch((error) => {
        root.textContent = `POS metadata unavailable: ${error.message}`;
        root.setAttribute("role", "alert");
    });
})();
