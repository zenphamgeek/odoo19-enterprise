"use strict";

const assert = require("node:assert/strict");
const { create, constructOpenOrderQuery } = require("../static/src/metadata_graph.js");

const scalar = (name, type = "integer") => ({ name, type, compute: false, related: false });
const metadata = {
    parent: {
        fields: ["id", "name", "settings", "child_ids"],
        relations: {
            id: scalar("id"),
            name: scalar("name", "char"),
            settings: scalar("settings", "json"),
            child_ids: { ...scalar("child_ids", "one2many"), relation: "child", inverse_name: "parent_id" },
        },
    },
    child: {
        fields: ["id", "parent_id", "tag_ids"],
        relations: {
            id: scalar("id"),
            parent_id: { ...scalar("parent_id", "many2one"), relation: "parent" },
            tag_ids: { ...scalar("tag_ids", "many2many"), relation: "tag" },
        },
    },
    tag: { fields: ["id"], relations: { id: scalar("id") } },
};

const openOrderQuery = constructOpenOrderQuery([
    { id: 7, write_date: "2026-08-24 12:34:59", state: "draft" },
    { id: "local", write_date: false, state: "draft" },
], [3, 4]);
assert.deepEqual(openOrderQuery.recordIds, { "pos.order": [7] });
assert.deepEqual(constructOpenOrderQuery([{ id: 8, state: "draft" }], [3]).domain["pos.order"], [
    "|", ["id", "=", 8], ["id", "not in", [8]], ["state", "=", "draft"], ["config_id", "in", [3]],
]);
assert.deepEqual(constructOpenOrderQuery([{ id: 8, write_date: "2026-08-24 12:34:59", state: "draft" }], [3], [8]).domain["pos.order"], [
    "|", ["id", "=", 8], ["id", "not in", [8]], ["state", "=", "draft"], ["config_id", "in", [3]],
]);
assert.deepEqual(constructOpenOrderQuery([], [3], [], ["draft-uuid"]).domain["pos.order"], [
    "|", ["uuid", "=", "draft-uuid"], ["id", "not in", []], ["state", "=", "draft"], ["config_id", "in", [3]],
]);
assert.deepEqual(openOrderQuery.domain["pos.order"], [
    "|", "|",
    ["id", "=", 7], ["write_date", ">=", "2026-08-24 12:35:00"],
    ["id", "=", 7], ["state", "!=", "draft"],
    ["id", "not in", [7]], ["state", "=", "draft"], ["config_id", "in", [3, 4]],
]);

const graph = create(metadata);
assert.equal(graph.descriptor("child", "parent_id").relational, true);
assert.deepEqual(graph.edges.map(({ model, field, target }) => [model, field, target]), [
    ["parent", "child_ids", "child"],
    ["child", "parent_id", "parent"],
    ["child", "tag_ids", "tag"],
]);
assert.equal(graph.inverse.get("child.parent_id").field, "child_ids");
assert.equal(graph.descriptor("tag", "<-child.tag_ids").dummy, true);
assert.strictEqual(graph.descriptor("child", "parent_id"), graph.descriptor("child", "parent_id"));

const wildcard = create({ item: { fields: [], relations: { z: scalar("z"), a: scalar("a"), z_again: scalar("z_again") } } });
assert.deepEqual([...wildcard.models.get("item").fields.keys()], ["z", "a", "z_again"]);
const deduplicated = create({ item: { fields: ["id", "id"], relations: { id: scalar("id") } } });
assert.deepEqual([...deduplicated.models.get("item").fields.keys()], ["id"]);
assert.throws(() => create({ broken: { fields: ["missing"], relations: {} } }), /Unknown field definition: broken\.missing/);
for (const relation of ["", null, 7]) assert.throws(() => create({ broken: { fields: [], relations: { peer_id: { ...scalar("peer_id", "many2one"), relation } } } }), /Invalid relation target/);

const externalGraph = create({
    entry: { fields: ["id", "journal_id"], relations: { id: scalar("id"), journal_id: { ...scalar("journal_id", "many2one"), relation: "account.journal" } } },
});
assert.equal(externalGraph.models.get("account.journal").external, true);
const externalFirst = externalGraph.merge("entry", { id: 1, journal_id: [12, "Bank"] });
const externalSecond = externalGraph.merge("entry", { id: 2, journal_id: 12 });
assert.strictEqual(externalFirst.journal_id, externalSecond.journal_id);
assert.deepEqual(externalGraph.serialize("entry", externalFirst), { id: 1, journal_id: 12 });
assert.deepEqual(externalGraph.serializeCache("entry", externalFirst), externalGraph.serialize("entry", externalFirst));

const first = graph.merge("child", { id: 7, parent_id: [2, "Parent"], tag_ids: [3] });
assert.strictEqual(first.parent_id, graph.get("parent", 2));
assert.strictEqual(first.tag_ids[0], graph.get("tag", 3));
graph.merge("child", { id: 7, parent_id: 2 }, { dirty: true });
graph.merge("child", { id: 7, parent_id: 9, tag_ids: [5] });
assert.equal(first.parent_id.id, 2);
assert.equal(first.tag_ids[0].id, 5);
assert.deepEqual(graph.serializeOrm("child", first), { parent_id: 2 });

const commands = create(metadata);
const parent1 = commands.merge("parent", { id: 1, child_ids: [] });
const parent2 = commands.merge("parent", { id: 2, child_ids: [] });
commands.merge("parent", { id: 1, child_ids: [[4, 10], [4, 11]] }, { dirty: true });
assert.deepEqual(parent1.child_ids.map(({ id }) => id), [10, 11]);
assert.strictEqual(commands.get("child", 10).parent_id, parent1);
commands.merge("parent", { id: 1, child_ids: [[3, 10]] }, { dirty: true });
assert.equal(commands.get("child", 10).parent_id, false);
commands.merge("parent", { id: 1, child_ids: [[6, 0, [10, 12]]] }, { dirty: true });
assert.deepEqual(parent1.child_ids.map(({ id }) => id), [10, 12]);
commands.merge("child", { id: 10, parent_id: 2 }, { dirty: true });
assert.deepEqual(parent1.child_ids.map(({ id }) => id), [12]);
assert.deepEqual(parent2.child_ids.map(({ id }) => id), [10]);
commands.merge("parent", { id: 2, child_ids: [[5]] }, { dirty: true });
assert.equal(commands.get("child", 10).parent_id, false);
commands.merge("parent", { id: 2, child_ids: [[0, 0, { id: "new-1", tag_ids: [] }]] }, { dirty: true });
assert.equal(commands.get("child", "new-1").parent_id.id, 2);
assert.deepEqual(commands.serializeOrm("parent", parent2), { child_ids: [[0, 0, { parent_id: 2, tag_ids: [] }]] });

const atomic = create(metadata);
atomic.merge("parent", { id: 1, name: "before", child_ids: [] });
assert.throws(() => atomic.merge("parent", { id: 1, name: "after", child_ids: [false] }), /Record ID required/);
assert.equal(atomic.get("parent", 1).name, "before");
for (const id of [null, false, 0, NaN, {}, []]) assert.throws(() => atomic.merge("tag", { id }), /Record ID required/);
assert.throws(() => atomic.merge("parent", { id: 1, child_ids: [[7, 3]] }), /Unsupported relation command: 7/);
assert.throws(() => atomic.merge("parent", { id: 1, unknown: true }), /Unknown field: parent\.unknown/);
assert.equal(atomic.get("parent", 1).name, "before");

const extended = create(metadata);
const extendedParent = extended.merge("parent", { id: 1, settings: { a: 1, b: 2 }, child_ids: [[4, 10], 20] });
assert.deepEqual(extendedParent.child_ids.map(({ id }) => id), [10, 20]);
extended.merge("parent", { id: 1, settings: { b: 3 }, child_ids: [[0, 0, { tag_ids: [] }], [1, 10, { tag_ids: [3] }], [2, 20]] }, { dirty: true });
assert.deepEqual(extendedParent.settings, { a: 1, b: 3 });
assert.equal(extendedParent.child_ids.length, 2);
const generated = extendedParent.child_ids.find(({ id }) => typeof id === "string");
assert.ok(generated.id.length > 0);
assert.deepEqual(extended.get("child", 10).tag_ids.map(({ id }) => id), [3]);
assert.equal(extended.get("child", 20)._deleted, true);
extended.merge("child", { id: 30, parent_id: { id: 2, name: "Nested", child_ids: [] }, tag_ids: [] });
assert.equal(extended.get("parent", 2).name, "Nested");
assert.throws(() => extended.merge("parent", { id: 1, name: "changed", child_ids: [[1, 10, { missing: true }]] }), /Unknown field: child\.missing/);
assert.equal(extendedParent.name, undefined);

const removed = commands.remove("child", "new-1");
assert.equal(removed._deleted, true);
assert.deepEqual(parent2.child_ids, []);
assert.deepEqual(commands.serializeCache("child", removed), { id: "new-1", parent_id: 2, tag_ids: [], _deleted: true });
assert.deepEqual(commands.serializeOrm("child", removed), {});

const lifecycle = create(metadata);
const owner = lifecycle.merge("parent", { id: 1, child_ids: [10, 11] });
lifecycle.merge("parent", { id: 1, child_ids: [[3, 10], [2, 11], [0, 0, { id: "local", tag_ids: [] }]] }, { dirty: true });
assert.deepEqual(lifecycle.serializeOrm("parent", owner, { keepCommands: true }).child_ids.map((command) => command[0]), [3, 2, 0]);
assert.deepEqual(lifecycle.serializeOrm("parent", owner).child_ids.map((command) => command[0]), [3, 2, 0]);
assert.deepEqual(lifecycle.serializeOrm("parent", owner).child_ids.map((command) => command[0]), [0]);
assert.equal(lifecycle.serializeOrm("parent", owner).child_ids[0][2].id, undefined);
const persisted = lifecycle.merge("child", { id: 20, parent_id: 1, tag_ids: [] });
lifecycle.merge("tag", { id: 3 });
lifecycle.merge("child", { id: 20, tag_ids: [3] }, { dirty: true });
assert.deepEqual(lifecycle.serializeOrm("parent", owner).child_ids[0].slice(0, 2), [1, 20]);
assert.deepEqual(lifecycle.serializeOrm("parent", owner).child_ids.map((command) => command[0]), [0]);
lifecycle.remove("child", persisted);
assert.deepEqual(lifecycle.serializeOrm("parent", owner).child_ids[0], [3, 20]);

const fanIn = create(metadata);
const fanInParent = fanIn.merge("parent", { id: 1, child_ids: [] });
for (const id of [10, 11, 12]) fanIn.merge("child", { id, parent_id: 1, tag_ids: [] });
assert.deepEqual(fanInParent.child_ids.map(({ id }) => id), [10, 11, 12]);
fanIn.merge("child", { id: 11, parent_id: false }, { dirty: true });
assert.deepEqual(fanInParent.child_ids.map(({ id }) => id), [10, 12]);
assert.strictEqual(fanIn.get("child", 10).parent_id, fanInParent);
assert.strictEqual(fanIn.get("child", 12).parent_id, fanInParent);

const m2mMetadata = {
    left: { fields: ["id", "right_ids"], relations: { id: scalar("id"), right_ids: { ...scalar("right_ids", "many2many"), relation: "right", relation_table: "left_right_rel" } } },
    right: { fields: ["id", "left_ids"], relations: { id: scalar("id"), left_ids: { ...scalar("left_ids", "many2many"), relation: "left", relation_table: "left_right_rel" } } },
};
const m2m = create(m2mMetadata);
const left = m2m.merge("left", { id: 1, right_ids: [2] });
const right = m2m.get("right", 2);
assert.deepEqual(right.left_ids, [left]);
m2m.merge("right", { id: 2, left_ids: [] }, { dirty: true });
assert.deepEqual(left.right_ids, []);
assert.equal([...m2m.models.get("right").fields.values()].some(({ dummy }) => dummy), false);
const dummyM2m = create({
    left: m2mMetadata.left,
    right: { fields: ["id"], relations: { id: scalar("id") } },
});
const dummyDescriptor = dummyM2m.descriptor("right", "<-left.right_ids");
assert.equal(dummyDescriptor.dummy, true);
const dummyLeft = dummyM2m.merge("left", { id: 1, right_ids: [2] });
const dummyRight = dummyM2m.get("right", 2);
assert.deepEqual(dummyRight[dummyDescriptor.name], [dummyLeft]);
dummyM2m.merge("left", { id: 1, right_ids: [] }, { dirty: true });
assert.deepEqual(dummyRight[dummyDescriptor.name], []);
assert.throws(() => create({
    ...m2mMetadata,
    right: { fields: ["id", "left_ids", "other_left_ids"], relations: { ...m2mMetadata.right.relations, other_left_ids: { ...scalar("other_left_ids", "many2many"), relation: "left", relation_table: "left_right_rel" } } },
}), /Many2many relation must have only one inverse/);

const delta = create(metadata);
const deltaParent = delta.merge("parent", { id: 1, name: "local", child_ids: [10] });
const deltaChild = delta.get("child", 10);
delta.merge("parent", { id: 1, name: "edited" }, { dirty: true });
delta.mergeDelta({ records: { parent: [{ id: 1, name: "ignored" }] } }, { authoritative: false });
assert.equal(deltaParent.name, "edited");
const changed = delta.mergeDelta({
    records: {
        child: [{ id: 10, parent_id: 1, tag_ids: [] }],
        parent: [{ id: 1, name: "remote", child_ids: [10] }],
    },
});
assert.strictEqual(changed.parent[0], deltaParent);
assert.strictEqual(changed.child[0], deltaChild);
assert.equal(deltaParent.name, "remote");
assert.equal(deltaParent.dirtyFields.has("name"), false);
assert.strictEqual(deltaChild.parent_id, deltaParent);
delta.mergeDelta({ deleted: { child: [10] } });
assert.equal(deltaChild._deleted, true);
assert.deepEqual(deltaParent.child_ids, []);

(async () => {
    const closure = create(metadata);
    const reads = [];
    const records = { parent: [{ id: 1, name: "remote", child_ids: [10] }] };
    await closure.completeRelations(records, async (model, ids, fields) => {
        reads.push([model, ids, fields]);
        if (model === "child") return [{ id: 10, parent_id: 1, tag_ids: [3] }];
        if (model === "tag") return [{ id: 3 }];
        throw new Error(`unexpected relation read: ${model}`);
    });
    assert.deepEqual(reads.map(([model, ids]) => [model, ids]), [["child", [10]], ["tag", [3]]]);
    closure.mergeDelta({ records });
    assert.strictEqual(closure.get("parent", 1).child_ids[0], closure.get("child", 10));
    assert.strictEqual(closure.get("child", 10).tag_ids[0], closure.get("tag", 3));
    await closure.completeRelations(records, async () => { throw new Error("hydrated relation fetched twice"); });
    console.log("metadata_graph.test.js: OK");
})().catch((error) => {
    console.error(error);
    process.exitCode = 1;
});
