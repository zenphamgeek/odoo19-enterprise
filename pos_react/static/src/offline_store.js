(() => {
    "use strict";

    const STORE = "outbox";
    const METADATA_STORE = "metadata";
    const RECORDS_STORE = "records";
    const STATE_STORE = "state";
    const DRAFTS_STORE = "drafts";
    const SCHEMA_VERSION = 4;

    function transactionDone(transaction) {
        return new Promise((resolve, reject) => {
            transaction.oncomplete = () => resolve();
            transaction.onerror = () => reject(transaction.error || new Error("IndexedDB transaction failed"));
            transaction.onabort = () => reject(transaction.error || new Error("IndexedDB transaction aborted"));
        });
    }

    function requestResult(request) {
        return new Promise((resolve, reject) => {
            request.onsuccess = () => resolve(request.result);
            request.onerror = () => reject(request.error || new Error("IndexedDB request failed"));
        });
    }

    function scopeFor({ tenantId, configId, userId, sessionId, companyId }) {
        const scope = { tenantId, configId, userId, sessionId, companyId };
        if (Object.values(scope).some((value) => !String(value).trim())) throw new Error("tenantId, configId, userId, sessionId and companyId are required");
        return scope;
    }

    function openDatabase(scope) {
        if (!globalThis.indexedDB || !globalThis.crypto?.randomUUID) {
            throw new Error("Native IndexedDB and crypto.randomUUID are required");
        }
        const namespace = [scope.tenantId, scope.configId, scope.userId].map((value) => encodeURIComponent(value)).join(":");
        const request = indexedDB.open(`pos-react:${namespace}`, SCHEMA_VERSION);
        request.onupgradeneeded = () => {
            if (!request.result.objectStoreNames.contains(STORE)) {
                const store = request.result.createObjectStore(STORE, { keyPath: "id" });
                store.createIndex("createdAt", "createdAt");
            }
            if (!request.result.objectStoreNames.contains(METADATA_STORE)) {
                request.result.createObjectStore(METADATA_STORE);
            }
            if (!request.result.objectStoreNames.contains(RECORDS_STORE)) {
                const store = request.result.createObjectStore(RECORDS_STORE, { keyPath: ["scopeKey", "model", "id"] });
                store.createIndex("scopeModel", ["scopeKey", "model"]);
            }
            if (!request.result.objectStoreNames.contains(STATE_STORE)) {
                request.result.createObjectStore(STATE_STORE);
            }
            if (!request.result.objectStoreNames.contains(DRAFTS_STORE)) {
                request.result.createObjectStore(DRAFTS_STORE);
            }
        };
        return requestResult(request);
    }

    function validateMetadata(data) {
        const invalid = () => { throw new Error("Invalid load_data_params metadata"); };
        if (!data || typeof data !== "object" || Array.isArray(data) || !Object.keys(data).length) invalid();
        for (const [model, definition] of Object.entries(data)) {
            if (!model || !definition || typeof definition !== "object" || Array.isArray(definition) || !Array.isArray(definition.fields) || definition.fields.some((field) => typeof field !== "string" || !field) || !definition.relations || typeof definition.relations !== "object" || Array.isArray(definition.relations)) invalid();
            const fieldNames = new Set(definition.fields);
            const relationNames = Object.keys(definition.relations);
            if (definition.fields.length && (fieldNames.size !== relationNames.length || relationNames.some((field) => !fieldNames.has(field)))) invalid();
            if (!definition.fields.length && !relationNames.length) invalid();
            for (const [name, relation] of Object.entries(definition.relations)) {
                if (!relation || typeof relation !== "object" || Array.isArray(relation) || relation.name !== name || typeof relation.type !== "string" || !relation.type || typeof relation.compute !== "boolean" || typeof relation.related !== "boolean") invalid();
                for (const field of ["model", "relation", "ondelete", "inverse_name", "relation_table"]) {
                    if (field in relation && relation[field] !== null && relation[field] !== false && (typeof relation[field] !== "string" || !relation[field])) invalid();
                }
                if (["many2one", "one2many", "many2many"].includes(relation.type) && (typeof relation.relation !== "string" || !relation.relation)) invalid();
            }
        }
        return data;
    }

    function canonical(value) {
        if (Array.isArray(value)) return value.map(canonical);
        if (value && typeof value === "object") return Object.fromEntries(Object.keys(value).sort().map((key) => [key, canonical(value[key])]));
        return value;
    }

    function retryDelay(attempts) {
        return Math.min(2000 * 2 ** (attempts - 1), 300000);
    }

    async function valueHash(data) {
        const bytes = new TextEncoder().encode(JSON.stringify(canonical(data)));
        const digest = await crypto.subtle.digest("SHA-256", bytes);
        return [...new Uint8Array(digest)].map((byte) => byte.toString(16).padStart(2, "0")).join("");
    }

    async function loadMetadata(scopeValues, fetchMetadata) {
        if (typeof fetchMetadata !== "function") throw new TypeError("fetchMetadata must be a function");
        const scope = scopeFor(scopeValues);
        const database = openDatabase(scope);
        let fetched;
        try {
            fetched = await fetchMetadata();
        } catch {
            const db = await database;
            const transaction = db.transaction(METADATA_STORE, "readonly");
            const cached = await requestResult(transaction.objectStore(METADATA_STORE).get("singleton"));
            await transactionDone(transaction);
            try {
                if (!cached || cached.schemaVersion !== SCHEMA_VERSION || !Array.isArray(cached.models) || cached.models.join(",") !== Object.keys(cached.data || {}).sort().join(",") || cached.hash !== await valueHash(validateMetadata(cached.data))) throw new Error("Valid cached POS metadata is unavailable");
                return Object.freeze(cached);
            } catch {
                throw new Error("Valid cached POS metadata is unavailable");
            } finally {
                db.close();
            }
        }
        const data = validateMetadata(fetched);
        const cached = Object.freeze({ schemaVersion: SCHEMA_VERSION, models: Object.keys(data).sort(), hash: await valueHash(data), data });
        const db = await database;
        const transaction = db.transaction(METADATA_STORE, "readwrite");
        transaction.objectStore(METADATA_STORE).put(cached, "singleton");
        await transactionDone(transaction);
        db.close();
        return cached;
    }

    function scopeKey(scope) {
        return [scope.tenantId, scope.configId, scope.userId, scope.sessionId, scope.companyId].map(String).join(":" );
    }

    function validateDelta(delta) {
        const invalid = (detail) => { throw new Error(`Invalid POS records delta: ${detail}`); };
        if (!delta || typeof delta !== "object" || Array.isArray(delta) || !delta.records || typeof delta.records !== "object" || Array.isArray(delta.records)) invalid("records");
        if (delta.cursor !== null && delta.cursor !== undefined && typeof delta.cursor !== "string" && typeof delta.cursor !== "number") invalid("cursor");
        if (delta.hash !== undefined && (typeof delta.hash !== "string" || !delta.hash)) invalid("hash");
        if (delta.replace !== undefined && (!Array.isArray(delta.replace) || new Set(delta.replace).size !== delta.replace.length || delta.replace.some((model) => typeof model !== "string" || !model))) invalid("replace");
        if (delta.deleted !== undefined && (!delta.deleted || typeof delta.deleted !== "object" || Array.isArray(delta.deleted))) invalid("deleted");
        for (const [model, records] of Object.entries(delta.records)) {
            if (!model || !Array.isArray(records) || records.some((record) => !record || typeof record !== "object" || Array.isArray(record) || !(typeof record.id === "string" || typeof record.id === "number"))) invalid(`records.${model}`);
            if (new Set(records.map((record) => String(record.id))).size !== records.length) invalid(`duplicate.${model}`);
        }
        for (const [model, ids] of Object.entries(delta.deleted || {})) {
            if (!model || !Array.isArray(ids) || ids.some((id) => typeof id !== "string" && typeof id !== "number")) invalid(`deleted.${model}`);
        }
        return delta;
    }

    async function loadRecords(scopeValues, fetchDelta, options = {}) {
        if (typeof fetchDelta !== "function") throw new TypeError("fetchDelta must be a function");
        if (!options || typeof options !== "object" || Array.isArray(options)) throw new TypeError("options must be an object");
        if (options.hash !== undefined && (typeof options.hash !== "string" || !options.hash)) throw new TypeError("options.hash must be a non-empty string");
        const scope = scopeFor(scopeValues);
        const key = scopeKey(scope);
        const db = await openDatabase(scope);
        const stateKey = `records:${key}`;
        const readCached = async () => {
            const transaction = db.transaction([RECORDS_STORE, STATE_STORE], "readonly");
            const records = await requestResult(transaction.objectStore(RECORDS_STORE).index("scopeModel").getAll(IDBKeyRange.bound([key, ""], [key, "\uffff"])));
            const state = await requestResult(transaction.objectStore(STATE_STORE).get(stateKey));
            await transactionDone(transaction);
            return { records: records.reduce((result, item) => ((result[item.model] ||= []).push(item.data), result), {}), cursor: state?.cursor ?? null, hash: state?.hash ?? null, offline: true };
        };
        const current = await readCached();
        const hashMismatch = options.hash !== undefined && options.hash !== current.hash;
        const idsByModel = Object.fromEntries(Object.entries(current.records).map(([model, records]) => [model, records.map(({ id }) => id)]));
        let fetched;
        try {
            fetched = await fetchDelta(hashMismatch ? null : current.cursor, hashMismatch ? {} : idsByModel);
        } catch (error) {
            db.close();
            if (hashMismatch) throw new Error("POS records hash mismatch");
            if (Object.keys(current.records).length) return current;
            throw error;
        }
        const delta = validateDelta(fetched);
        if (delta.hash && options.hash && delta.hash !== options.hash) {
            db.close();
            throw new Error("POS records hash mismatch");
        }
        const transaction = db.transaction([RECORDS_STORE, STATE_STORE], "readwrite");
        const store = transaction.objectStore(RECORDS_STORE);
        if (hashMismatch) {
            const keys = await requestResult(store.index("scopeModel").getAllKeys(IDBKeyRange.bound([key, ""], [key, "\uffff"])));
            for (const recordKey of keys) store.delete(recordKey);
        }
        const replace = new Set(delta.replace || []);
        for (const model of replace) {
            if (!(model in delta.records)) {
                transaction.abort();
                db.close();
                throw new Error("Replacement model has no records");
            }
            const keys = await requestResult(store.index("scopeModel").getAllKeys([key, model]));
            for (const recordKey of keys) store.delete(recordKey);
        }
        for (const [model, records] of Object.entries(delta.records)) {
            for (const record of records) store.put({ scopeKey: key, model, id: record.id, scope, data: record });
        }
        for (const [model, ids] of Object.entries(delta.deleted || {})) {
            for (const id of ids) store.delete([key, model, id]);
        }
        const hash = delta.hash ?? options.hash ?? current.hash;
        transaction.objectStore(STATE_STORE).put({ cursor: delta.cursor ?? null, hash }, stateKey);
        await transactionDone(transaction);
        db.close();
        const reopened = await openDatabase(scope);
        const read = reopened.transaction(RECORDS_STORE, "readonly");
        const rows = await requestResult(read.objectStore(RECORDS_STORE).index("scopeModel").getAll(IDBKeyRange.bound([key, ""], [key, "\uffff"])));
        await transactionDone(read);
        reopened.close();
        const records = rows.reduce((result, item) => ((result[item.model] ||= []).push(item.data), result), {});
        return { records, cursor: delta.cursor ?? null, hash, offline: false };
    }

    function createOfflineStore({ tenantId, configId, userId, sessionId, companyId, send, isValidAck = Boolean, isPermanentError = (error) => error?.permanent === true, now = Date.now }) {
        if (typeof send !== "function") throw new TypeError("send must be a function");
        if (typeof isValidAck !== "function") throw new TypeError("isValidAck must be a function");
        if (typeof isPermanentError !== "function") throw new TypeError("isPermanentError must be a function");
        if (typeof now !== "function") throw new TypeError("now must be a function");
        const scope = scopeFor({ tenantId, configId, userId, sessionId, companyId });
        const database = openDatabase(scope);
        let draining = null;
        let drainAgain = false;
        let closed = false;
        const sendingIds = new Set();

        function immutableJson(value) {
            const copy = JSON.parse(JSON.stringify(value));
            const freeze = (item) => {
                if (item && typeof item === "object") {
                    Object.values(item).forEach(freeze);
                    Object.freeze(item);
                }
                return item;
            };
            return freeze(copy);
        }

        function validatePayload(payload) {
            if (!payload || typeof payload !== "object" || Array.isArray(payload)) throw new TypeError("payload must be an object");
        }

        function validateId(id) {
            if (typeof id !== "string" || !id) throw new TypeError("id must be a non-empty string");
        }

        async function put(payload, id = crypto.randomUUID()) {
            if (closed) throw new Error("Offline store is closed");
            validatePayload(payload);
            validateId(id);
            const payloadHash = await valueHash(payload);
            const db = await database;
            const transaction = db.transaction(STORE, "readwrite");
            const store = transaction.objectStore(STORE);
            if (await requestResult(store.get(id))) throw new Error("Outbox record already exists");
            const createdAt = now();
            store.add({ id, createdAt, updatedAt: createdAt, lastAttemptAt: null, nextAttemptAt: createdAt, scope, payload, payloadHash, status: "pending", attempts: 0, errorCode: null });
            await transactionDone(transaction);
            return id;
        }

        async function loadDraft(id) {
            if (closed) throw new Error("Offline store is closed");
            validateId(id);
            const db = await database;
            const transaction = db.transaction(DRAFTS_STORE, "readonly");
            const drafts = await requestResult(transaction.objectStore(DRAFTS_STORE).get(scopeKey(scope)));
            await transactionDone(transaction);
            return drafts && id in drafts ? immutableJson(drafts[id]) : null;
        }

        async function saveDraft(id, payload) {
            if (closed) throw new Error("Offline store is closed");
            validateId(id);
            validatePayload(payload);
            const db = await database;
            const transaction = db.transaction(DRAFTS_STORE, "readwrite");
            const store = transaction.objectStore(DRAFTS_STORE);
            const key = scopeKey(scope);
            const drafts = await requestResult(store.get(key)) || {};
            drafts[id] = payload;
            store.put(drafts, key);
            await transactionDone(transaction);
            return id;
        }

        async function deleteDraft(id) {
            if (closed) throw new Error("Offline store is closed");
            validateId(id);
            const db = await database;
            const transaction = db.transaction(DRAFTS_STORE, "readwrite");
            const store = transaction.objectStore(DRAFTS_STORE);
            const key = scopeKey(scope);
            const drafts = await requestResult(store.get(key)) || {};
            delete drafts[id];
            Object.keys(drafts).length ? store.put(drafts, key) : store.delete(key);
            await transactionDone(transaction);
        }

        async function commitDraft(id) {
            if (closed) throw new Error("Offline store is closed");
            validateId(id);
            const db = await database;
            const key = scopeKey(scope);
            const read = db.transaction(DRAFTS_STORE, "readonly");
            const snapshot = await requestResult(read.objectStore(DRAFTS_STORE).get(key)) || {};
            await transactionDone(read);
            const payload = snapshot[id];
            validatePayload(payload);
            validateId(payload.uuid);
            const outboxId = payload.uuid;
            const payloadHash = await valueHash(payload);
            const transaction = db.transaction([DRAFTS_STORE, STORE], "readwrite");
            const draftsStore = transaction.objectStore(DRAFTS_STORE);
            const outbox = transaction.objectStore(STORE);
            const drafts = await requestResult(draftsStore.get(key)) || {};
            if (JSON.stringify(canonical(drafts[id])) !== JSON.stringify(canonical(payload))) {
                transaction.abort();
                throw new Error("Draft changed or does not exist");
            }
            if (await requestResult(outbox.get(outboxId))) {
                transaction.abort();
                throw new Error("Outbox record already exists");
            }
            const createdAt = now();
            outbox.add({ id: outboxId, createdAt, updatedAt: createdAt, lastAttemptAt: null, nextAttemptAt: createdAt, scope, payload, payloadHash, status: "pending", attempts: 0, errorCode: null });
            delete drafts[id];
            Object.keys(drafts).length ? draftsStore.put(drafts, key) : draftsStore.delete(key);
            await transactionDone(transaction);
            return outboxId;
        }

        async function list() {
            if (closed) throw new Error("Offline store is closed");
            const db = await database;
            const transaction = db.transaction(STORE, "readonly");
            const result = requestResult(transaction.objectStore(STORE).index("createdAt").getAll());
            await transactionDone(transaction);
            return result;
        }

        async function exportRecord(id) {
            if (closed) throw new Error("Offline store is closed");
            if (typeof id !== "string" || !id) throw new TypeError("id must be a non-empty string");
            const db = await database;
            const transaction = db.transaction(STORE, "readonly");
            const record = await requestResult(transaction.objectStore(STORE).get(id));
            await transactionDone(transaction);
            if (!record) throw new Error("Outbox record does not exist");
            return immutableJson({ schemaVersion: SCHEMA_VERSION, exportedAt: now(), proof: await valueHash(record), record });
        }

        async function deleteExported(id, proof, confirmation) {
            if (closed) throw new Error("Offline store is closed");
            if (typeof id !== "string" || !id) throw new TypeError("id must be a non-empty string");
            if (typeof confirmation !== "string" || confirmation !== id) throw new Error("Deletion confirmation must exactly match id");
            if (sendingIds.has(id)) throw new Error("Cannot delete a record while sending");
            const db = await database;
            const read = db.transaction(STORE, "readonly");
            const record = await requestResult(read.objectStore(STORE).get(id));
            await transactionDone(read);
            if (!record) throw new Error("Outbox record does not exist");
            if (typeof proof !== "string" || proof !== await valueHash(record)) throw new Error("Export proof does not match current record");
            if (sendingIds.has(id)) throw new Error("Cannot delete a record while sending");
            const transaction = db.transaction(STORE, "readwrite");
            const store = transaction.objectStore(STORE);
            const current = await requestResult(store.get(id));
            if (!current || JSON.stringify(canonical(current)) !== JSON.stringify(canonical(record)) || sendingIds.has(id)) {
                transaction.abort();
                throw new Error("Outbox record changed, is missing, or is sending");
            }
            store.delete(id);
            await transactionDone(transaction);
        }

        async function deleteAcked(id) {
            const db = await database;
            const transaction = db.transaction(STORE, "readwrite");
            transaction.objectStore(STORE).delete(id);
            await transactionDone(transaction);
        }

        async function update(item, values) {
            const db = await database;
            const transaction = db.transaction(STORE, "readwrite");
            transaction.objectStore(STORE).put({ ...item, ...values });
            await transactionDone(transaction);
        }

        function errorCode(error, fallback) {
            return String(error?.code || fallback);
        }

        let forceAgain = false;
        let targetAgain = null;

        function drain(force = false, targetId = null) {
            if (draining) {
                drainAgain = true;
                forceAgain ||= force;
                targetAgain ??= targetId;
                return draining;
            }
            draining = (async () => {
                do {
                    const targetThisPass = targetId ?? targetAgain;
                    const forceThisPass = targetThisPass !== null && (force || forceAgain);
                    force = false;
                    targetId = null;
                    drainAgain = false;
                    forceAgain = false;
                    targetAgain = null;
                    for (const item of await list()) {
                        if (targetThisPass !== null && item.id !== targetThisPass) continue;
                        if (item.status === "blocked" && (!forceThisPass || !["RETRY_EXHAUSTED", "PERMANENT", "INVALID_ACK"].includes(item.errorCode))) continue;
                        if (!forceThisPass && (item.nextAttemptAt ?? 0) > now()) continue;
                        const attemptedAt = now();
                        const attempts = (item.attempts || 0) + 1;
                        const attempt = { attempts, lastAttemptAt: attemptedAt, updatedAt: attemptedAt };
                        if (!item.scope || Object.keys(scope).some((key) => String(item.scope[key]) !== String(scope[key]))) {
                            await update(item, { ...attempt, status: "blocked", errorCode: "SCOPE_MISMATCH" });
                            continue;
                        }
                        if (!item.payloadHash || item.payloadHash !== await valueHash(item.payload)) {
                            await update(item, { ...attempt, status: "blocked", errorCode: "PAYLOAD_TAMPERED" });
                            continue;
                        }
                        try {
                            sendingIds.add(item.id);
                            let ack;
                            try {
                                ack = await send(item.payload, item.id);
                            } finally {
                                sendingIds.delete(item.id);
                            }
                            if (!isValidAck(ack, item.payload, item.id)) {
                                await update(item, { ...attempt, status: "blocked", errorCode: "INVALID_ACK" });
                                continue;
                            }
                            await deleteAcked(item.id);
                        } catch (error) {
                            const permanent = isPermanentError(error);
                            const exhausted = !permanent && attempts >= 8;
                            await update(item, {
                                ...attempt,
                                status: permanent || exhausted ? "blocked" : "retry",
                                errorCode: exhausted ? "RETRY_EXHAUSTED" : errorCode(error, permanent ? "PERMANENT" : "TRANSPORT"),
                                nextAttemptAt: permanent || exhausted ? null : attemptedAt + retryDelay(attempts),
                            });
                        }
                    }
                } while (drainAgain);
            })().finally(() => { draining = null; });
            return draining;
        }

        function retryNow(id) {
            if (typeof id !== "string" || !id) throw new TypeError("id must be a non-empty string");
            return drain(true, id);
        }

        async function close() {
            closed = true;
            (await database).close();
        }

        return Object.freeze({ put, list, loadDraft, saveDraft, deleteDraft, commitDraft, exportRecord, deleteExported, drain, retryNow, close });
    }

    globalThis.posReactOfflineStore = Object.freeze({ create: createOfflineStore, loadMetadata, loadRecords, retryDelay, schemaVersion: SCHEMA_VERSION });
})();
