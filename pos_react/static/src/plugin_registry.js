(() => {
    "use strict";

    const POINTS = Object.freeze([
        "screen",
        "slot",
        "action",
        "dataRequirement",
        "paymentAdapter",
        "receiptFragment",
    ]);
    const entries = new Map(POINTS.map((point) => [point, new Map()]));

    function bucket(point) {
        const result = entries.get(point);
        if (!result) throw new Error(`Unknown POS React plugin point: ${point}`);
        return result;
    }

    function register(point, id, value, options = {}) {
        if (!id || typeof id !== "string") throw new Error("POS React plugin id must be a non-empty string");
        const plugins = bucket(point);
        if (plugins.has(id)) throw new Error(`Duplicate POS React plugin: ${point}:${id}`);
        const entry = { id, value, priority: options.priority || 0, before: options.before, after: options.after };
        plugins.set(id, entry);
        let active = true;
        return () => {
            if (!active) return;
            active = false;
            plugins.delete(id);
            if (value && typeof value.cleanup === "function") value.cleanup();
        };
    }

    function resolve(point) {
        const plugins = bucket(point);
        for (const entry of plugins.values()) {
            for (const anchor of [entry.before, entry.after]) {
                if (anchor && !plugins.has(anchor)) throw new Error(`Missing POS React plugin anchor: ${point}:${anchor}`);
            }
        }
        const pending = new Map([...plugins].map(([id, entry]) => [id, { entry, dependencies: new Set() }]));
        for (const { entry, dependencies } of pending.values()) {
            if (entry.after) dependencies.add(entry.after);
            if (entry.before) pending.get(entry.before).dependencies.add(entry.id);
        }
        const ordered = [];
        while (pending.size) {
            const ready = [...pending.values()].filter(({ dependencies }) => !dependencies.size)
                .sort((a, b) => b.entry.priority - a.entry.priority || a.entry.id.localeCompare(b.entry.id));
            if (!ready.length) throw new Error(`Cyclic POS React plugin anchors: ${point}`);
            for (const { entry } of ready) {
                ordered.push(entry);
                pending.delete(entry.id);
                for (const item of pending.values()) item.dependencies.delete(entry.id);
            }
        }
        return ordered.map(({ id, value, priority }) => ({ id, value, priority }));
    }

    window.posReactPlugins = Object.freeze({ points: POINTS, register, resolve });
})();
