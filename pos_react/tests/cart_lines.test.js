"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const source = fs.readFileSync(path.resolve(__dirname, "../static/src/app.js"), "utf8");
const match = source.match(/    function effectiveLines\(cart, products\) \{[\s\S]*?\n    \}/);
assert.ok(match, "effectiveLines missing");
const effectiveLines = Function(`${match[0]}\nreturn effectiveLines;`)();
const products = [
    { id: 1, price: 80, taxIds: [2] },
    { id: 9, price: 10, taxIds: [3] },
];
const lines = effectiveLines([
    { productId: 1, price: 100, taxIds: [1], quantity: 1 },
    { productId: 9, price: -10, taxIds: [1], quantity: 1, extraTaxData: { discount_percentage: 10 } },
    { productId: 9, price: 5, taxIds: [1], quantity: 1, isCustom: true },
], products);
assert.deepEqual(lines.map(({ price, taxIds }) => ({ price, taxIds })), [
    { price: 80, taxIds: [2] },
    { price: -10, taxIds: [1] },
    { price: 5, taxIds: [1] },
]);
assert.equal(effectiveLines([{ productId: 2, price: 17, quantity: 1 }], [{ id: 2, lst_price: 25 }])[0].price, undefined, "array cart semantics changed");
assert.deepEqual(
    effectiveLines({ 2: 1, 3: 1 }, [
        { id: 2, price: 0, lst_price: 25 },
        { id: 3, price: 35, list_price: 40 },
    ]).map(({ price }) => price),
    [0, 35],
    "object cart must use normalized product prices"
);
console.log("cart_lines.test.js: normalized prices preserve cart semantics");
