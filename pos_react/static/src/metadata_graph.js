((root, factory) => {
    const api = factory();
    if (typeof module === "object" && module.exports) module.exports = api;
    else root.posReactMetadataGraph = api;
})(globalThis, () => {
    "use strict";

    const RELATIONAL_TYPES = new Set(["many2one", "one2many", "many2many"]);
    const recordId = (value) => Array.isArray(value) ? value[0] : value?.id ?? value;
    const validId = (id) => (typeof id === "number" && Number.isFinite(id) && id !== 0) || (typeof id === "string" && id.length > 0);
    const localId = () => globalThis.crypto?.randomUUID?.() || `local-${Date.now().toString(36)}-${Math.random().toString(36).slice(2)}`;
    const or = (domains) => domains.length < 2 ? (domains[0] || []) : [...Array(domains.length - 1).fill("|"), ...domains.flat()];

    function constructOpenOrderQuery(orders, configIds, forceIds = [], forceUuids = []) {
        const forced = new Set(forceIds);
        const synced = orders.filter(({ id }) => Number.isInteger(id) && id > 0);
        const changed = synced.map((order) => {
            if (forced.has(order.id) || !order.write_date) return [["id", "=", order.id]];
            const timestamp = new Date(`${order.write_date.replace(" ", "T")}Z`);
            timestamp.setUTCSeconds(timestamp.getUTCSeconds() + 1);
            const cursor = timestamp.toISOString().slice(0, 19).replace("T", " ");
            return or([
                [["id", "=", order.id], ["write_date", ">=", cursor]],
                [["id", "=", order.id], ["state", "!=", order.state]],
            ]);
        });
        const ids = synced.map(({ id }) => id);
        return {
            domain: {
                "pos.order": or([
                    ...changed,
                    ...forceUuids.map((uuid) => [["uuid", "=", uuid]]),
                    [["id", "not in", ids], ["state", "=", "draft"], ["config_id", "in", configIds]],
                ]),
            },
            recordIds: { "pos.order": ids },
        };
    }

    function create(metadata) {
        if (!metadata || typeof metadata !== "object" || Array.isArray(metadata)) throw new TypeError("metadata must be an object");
        const models = new Map();
        const records = new Map();

        for (const [name, definition] of Object.entries(metadata)) {
            if (!definition || typeof definition !== "object" || Array.isArray(definition)) throw new TypeError(`Invalid definition: ${name}`);
            if (!Array.isArray(definition.fields)) throw new TypeError(`Invalid fields: ${name}`);
            if (!definition.relations || typeof definition.relations !== "object" || Array.isArray(definition.relations)) throw new TypeError(`Invalid relations: ${name}`);
            const fields = new Map();
            const fieldNames = definition.fields.length ? definition.fields : Object.keys(definition.relations);
            for (const fieldName of new Set(fieldNames)) {
                const source = definition.relations[fieldName];
                if (!source || typeof source !== "object" || Array.isArray(source)) throw new Error(`Unknown field definition: ${name}.${fieldName}`);
                fields.set(fieldName, Object.freeze({ ...source, relational: RELATIONAL_TYPES.has(source.type) }));
            }
            models.set(name, Object.freeze({ name, fields, external: false }));
            records.set(name, new Map());
        }

        const edges = [];
        const inverse = new Map();
        const many2manyInverse = new Map();
        const memberships = new WeakMap();
        for (const model of [...models.values()]) {
            for (const field of model.fields.values()) {
                if (!field.relational) continue;
                if (typeof field.relation !== "string" || !field.relation) throw new Error(`Invalid relation target: ${model.name}.${field.name}`);
                if (!models.has(field.relation)) {
                    models.set(field.relation, Object.freeze({ name: field.relation, fields: new Map(), external: true }));
                    records.set(field.relation, new Map());
                }
                const edge = Object.freeze({ model: model.name, field: field.name, target: field.relation, type: field.type, inverse: field.inverse_name || null });
                edges.push(edge);
                if (edge.inverse) inverse.set(`${edge.target}.${edge.inverse}`, edge);
            }
        }

        for (const edge of edges) {
            if (edge.type !== "many2many") continue;
            const field = models.get(edge.model).fields.get(edge.field);
            const matches = [...(models.get(edge.target)?.fields.values() || [])].filter((candidate) =>
                candidate.type === "many2many" && candidate.relation === edge.model && candidate.relation_table === field.relation_table &&
                !(edge.model === edge.target && candidate.name === edge.field)
            );
            if (matches.length > 1) throw new Error("Many2many relation must have only one inverse");
            const inverseField = matches[0] || Object.freeze({
                name: `<-${edge.model}.${edge.field}`,
                type: "many2many",
                relation: edge.model,
                relation_table: field.relation_table,
                relational: true,
                dummy: true,
            });
            if (!matches[0]) models.get(edge.target).fields.set(inverseField.name, inverseField);
            many2manyInverse.set(`${edge.model}.${edge.field}`, inverseField);
        }

        function descriptor(model, field) {
            const result = models.get(model)?.fields.get(field);
            if (!result) throw new Error(`Unknown field: ${model}.${field}`);
            return result;
        }

        function normalizeId(model, value) {
            const id = recordId(value);
            if (!validId(id)) throw new Error(`Record ID required: ${model}`);
            return id;
        }

        function ensure(model, value) {
            const bucket = records.get(model);
            if (!bucket) throw new Error(`Unknown model: ${model}`);
            const id = normalizeId(model, value);
            if (!bucket.has(id)) {
                const record = { id, dirtyFields: new Set() };
                Object.defineProperties(record, {
                    _persisted: { value: false, writable: true },
                    _pendingUnlink: { value: new Map() },
                    _pendingDelete: { value: new Map() },
                });
                bucket.set(id, record);
            }
            return bucket.get(id);
        }

        function inverseField(model, field) {
            return field.inverse_name
                ? models.get(field.relation)?.fields.get(field.inverse_name)
                : many2manyInverse.get(`${model}.${field.name}`);
        }

        function members(target, field) {
            let fields = memberships.get(target);
            if (!fields) memberships.set(target, fields = new Map());
            if (!fields.has(field)) fields.set(field, new Set(target[field] || []));
            return fields.get(field);
        }

        function replaceMembers(target, field, next) {
            target[field] = next;
            let fields = memberships.get(target);
            if (!fields) memberships.set(target, fields = new Map());
            fields.set(field, new Set(next));
        }

        function removeMember(target, field, record) {
            if (!members(target, field).delete(record)) return;
            target[field] = target[field].filter((item) => item !== record);
        }

        function addMember(target, field, record) {
            if (members(target, field).has(record)) return;
            members(target, field).add(record);
            target[field] ||= [];
            target[field].push(record);
        }

        function unlinkInverse(model, record, field, target) {
            if (!target) return;
            const other = inverseField(model, field);
            if (!other) return;
            if (other.type === "many2one" && target[other.name] === record) target[other.name] = false;
            else if (Array.isArray(target[other.name])) removeMember(target, other.name, record);
        }

        function linkInverse(model, record, field, target) {
            const other = inverseField(model, field);
            if (!other) return;
            if (other.type === "many2one") {
                const previous = target[other.name];
                if (previous && previous !== record) removeMember(previous, field.name, target);
                target[other.name] = record;
            } else addMember(target, other.name, record);
        }

        function x2many(model, record, field, value, dirty) {
            const current = record[field.name] || [];
            let next = value.some(Array.isArray) ? [...current] : [];
            for (const item of value) {
                if (!Array.isArray(item)) {
                    next.push(ensure(field.relation, item));
                    continue;
                }
                const command = item;
                if (command[0] === 0) next.push(merge(field.relation, command[2], { dirty: true }));
                else if (command[0] === 1) merge(field.relation, { ...command[2], id: command[1] }, { dirty: true });
                else if (command[0] === 2) {
                    const target = get(field.relation, command[1]);
                    if (target?._persisted) record._pendingDelete.set(field.name, [...(record._pendingDelete.get(field.name) || []), target.id]);
                    if (target) remove(field.relation, target, { track: false });
                    next = next.filter((target) => target.id !== command[1]);
                } else if (command[0] === 4) next.push(ensure(field.relation, command[1]));
                else if (command[0] === 3) {
                    const target = get(field.relation, command[1]);
                    if (target?._persisted) record._pendingUnlink.set(field.name, [...(record._pendingUnlink.get(field.name) || []), target.id]);
                    next = next.filter((target) => target.id !== command[1]);
                }
                else if (command[0] === 5) next = [];
                else if (command[0] === 6) next = command[2].map((id) => ensure(field.relation, id));
            }
            next = [...new Map(next.map((item) => [item.id, item])).values()];
            const nextMembers = new Set(next);
            for (const old of current) if (!nextMembers.has(old)) unlinkInverse(model, record, field, old);
            for (const item of next) linkInverse(model, record, field, item);
            replaceMembers(record, field.name, next);
            if (!dirty) for (const target of next) target._persisted = true;
            if (dirty) record.dirtyFields.add(field.name);
        }

        function merge(model, values, { dirty = false, authoritative = false } = {}) {
            if (!values || typeof values !== "object" || Array.isArray(values)) throw new TypeError(`Invalid record: ${model}`);
            const id = normalizeId(model, values.id);
            const definition = models.get(model);
            if (!definition) throw new Error(`Unknown model: ${model}`);
            const prepared = [];
            for (const [name, value] of Object.entries(values)) {
                if (name === "id") continue;
                const field = definition.fields.get(name);
                if (!field) throw new Error(`Unknown field: ${model}.${name}`);
                if (field.type === "many2one" && value) normalizeId(field.relation, value);
                let preparedValue = value;
                if (field.relational && field.type !== "many2one") {
                    if (!Array.isArray(value)) throw new TypeError(`Invalid relation value: ${model}.${name}`);
                    preparedValue = value.map((item) => {
                        if (!Array.isArray(item)) {
                            normalizeId(field.relation, item);
                            return item;
                        }
                        const command = item;
                        if (![0, 1, 2, 3, 4, 5, 6].includes(command[0])) throw new Error(`Unsupported relation command: ${command[0]}`);
                        if ([1, 2, 3, 4].includes(command[0])) normalizeId(field.relation, command[1]);
                        if ([0, 1].includes(command[0])) {
                            if (!command[2] || typeof command[2] !== "object" || Array.isArray(command[2])) throw new TypeError(`Invalid record: ${field.relation}`);
                            const childValues = command[0] === 0 ? { ...command[2], id: command[2].id || localId() } : { ...command[2], id: command[1] };
                            for (const childName of Object.keys(childValues)) if (childName !== "id" && !models.get(field.relation).fields.has(childName)) throw new Error(`Unknown field: ${field.relation}.${childName}`);
                            return [command[0], command[1], childValues];
                        }
                        if (command[0] === 6) {
                            if (!Array.isArray(command[2])) throw new TypeError(`Invalid relation value: ${model}.${name}`);
                            for (const id of command[2]) normalizeId(field.relation, id);
                        }
                        return command;
                    });
                }
                prepared.push([name, preparedValue, field]);
            }
            const current = ensure(model, id);
            current._deleted = false;
            if (!dirty) current._persisted = true;
            for (const [name, value, field] of prepared) {
                if (!dirty && !authoritative && current.dirtyFields.has(name)) continue;
                if (!field.relational) current[name] = value && typeof value === "object" && !Array.isArray(value) && current[name] && typeof current[name] === "object" && !Array.isArray(current[name]) ? { ...current[name], ...value } : value;
                else if (field.type === "many2one") {
                    const next = value
                        ? value && typeof value === "object" && !Array.isArray(value) && !models.get(field.relation).external
                            ? merge(field.relation, value, { dirty, authoritative })
                            : ensure(field.relation, value)
                        : false;
                    const owner = inverse.get(`${model}.${name}`);
                    if (owner && current[name] !== next) {
                        const previous = current[name];
                        if (previous) removeMember(previous, owner.field, current);
                        if (next) addMember(next, owner.field, current);
                    }
                    current[name] = next;
                } else x2many(model, current, field, value || [], dirty);
                if (dirty) current.dirtyFields.add(name);
                else if (authoritative) current.dirtyFields.delete(name);
            }
            return current;
        }

        function mergeMany(model, values, options) {
            if (!Array.isArray(values)) throw new TypeError("values must be an array");
            for (const value of values) normalizeId(model, value?.id);
            return values.map((value) => merge(model, value, options));
        }

        function get(model, id) {
            return records.get(model)?.get(recordId(id));
        }

        function all(model) {
            if (!models.has(model)) throw new Error(`Unknown model: ${model}`);
            return [...records.get(model).values()];
        }

        async function completeRelations(deltaRecords, read) {
            const requested = new Map();
            while (true) {
                const missing = new Map();
                const included = new Map(Object.entries(deltaRecords).map(([model, values]) => [model, new Set(values.map(({ id }) => String(id)))]));
                for (const [model, values] of Object.entries(deltaRecords)) {
                    const definition = models.get(model);
                    if (!definition) continue;
                    for (const value of values) for (const field of definition.fields.values()) {
                        if (!field.relational || models.get(field.relation)?.external) continue;
                        const raw = value[field.name];
                        const ids = field.type === "many2one" ? (raw ? [Array.isArray(raw) ? raw[0] : raw.id || raw] : []) : (Array.isArray(raw) ? raw.filter((item) => !Array.isArray(item)) : []);
                        for (const id of ids) {
                            const key = String(id);
                            if (!included.get(field.relation)?.has(key) && !get(field.relation, id)?._persisted && !requested.get(field.relation)?.has(key)) {
                                if (!missing.has(field.relation)) missing.set(field.relation, new Set());
                                missing.get(field.relation).add(id);
                            }
                        }
                    }
                }
                if (!missing.size) return deltaRecords;
                for (const [model, ids] of missing) {
                    if (!requested.has(model)) requested.set(model, new Set());
                    ids.forEach((id) => requested.get(model).add(String(id)));
                    const fields = [...models.get(model).fields.keys()].filter((field) => field !== "id");
                    deltaRecords[model] = [...(deltaRecords[model] || []), ...await read(model, [...ids], fields)];
                }
            }
        }

        function mergeDelta({ records: deltaRecords = {}, deleted = {} }, { authoritative = true } = {}) {
            const changed = {};
            for (const [model, values] of Object.entries(deltaRecords)) {
                changed[model] = mergeMany(model, values, { authoritative });
            }
            for (const [model, ids] of Object.entries(deleted)) {
                if (!Array.isArray(ids)) throw new TypeError(`Invalid deleted IDs: ${model}`);
                changed[model] ||= [];
                changed[model].push(...ids.map((id) => remove(model, id, { track: false })));
            }
            return changed;
        }

        function remove(model, value, { track = true, delete: deleteRecord = false } = {}) {
            const record = ensure(model, value);
            const definition = models.get(model);
            for (const field of definition.fields.values()) {
                if (!field.relational) continue;
                if (field.type === "many2one") {
                    const owner = inverse.get(`${model}.${field.name}`);
                    const target = record[field.name];
                    if (owner && target) {
                        removeMember(target, owner.field, record);
                        if (track && record._persisted) {
                            const pending = deleteRecord ? target._pendingDelete : target._pendingUnlink;
                            pending.set(owner.field, [...(pending.get(owner.field) || []), record.id]);
                        }
                    }
                } else for (const target of record[field.name] || []) unlinkInverse(model, record, field, target);
            }
            record._deleted = true;
            record.dirtyFields.clear();
            return record;
        }

        function serializeCache(model, record) {
            if (!models.has(model)) throw new Error(`Unknown model: ${model}`);
            const output = {};
            for (const [name, value] of Object.entries(record)) {
                if (name === "dirtyFields" || (name === "_deleted" && !value)) continue;
                const field = models.get(model).fields.get(name);
                if (!field?.relational) output[name] = value;
                else if (field.type === "many2one") output[name] = value ? recordId(value) : false;
                else output[name] = (value || []).map(recordId);
            }
            return output;
        }

        function serializeOrm(model, record, { keepCommands = false, allFields = false } = {}) {
            if (record._deleted) return record._persisted ? { id: record.id, _delete: true } : {};
            const output = {};
            const names = allFields ? models.get(model).fields.keys() : record.dirtyFields;
            for (const name of names) {
                if (name === "id") continue;
                const field = descriptor(model, name);
                const value = record[name];
                if (allFields && value === undefined) continue;
                let retainDirty = false;
                if (!field.relational) output[name] = value;
                else if (field.type === "many2one") output[name] = value ? recordId(value) : false;
                else {
                    const local = (value || []).filter((item) => !item._persisted);
                    const commands = [
                        ...(record._pendingUnlink.get(name) || []).map((id) => [3, id]),
                        ...(record._pendingDelete.get(name) || []).map((id) => [2, id]),
                        ...(value || []).filter((item) => item._persisted && item.dirtyFields.size).map((item) => [1, item.id, serializeOrm(field.relation, item, { keepCommands })]),
                        ...local.map((item) => [0, 0, serializeOrm(field.relation, item, { keepCommands: true, allFields: true })]),
                    ];
                    output[name] = commands;
                    retainDirty ||= local.length > 0;
                    if (!keepCommands) {
                        record._pendingUnlink.delete(name);
                        record._pendingDelete.delete(name);
                    }
                }
                if (!keepCommands && !retainDirty) record.dirtyFields.delete(name);
            }
            return output;
        }

        return Object.freeze({ models, edges: Object.freeze(edges), inverse, descriptor, merge, mergeMany, completeRelations, mergeDelta, get, all, remove, serializeCache, serializeOrm, serialize: serializeCache });
    }

    return Object.freeze({ create, constructOpenOrderQuery });
});
