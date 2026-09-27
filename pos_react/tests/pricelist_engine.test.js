"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const port = require("../static/src/pricelist_engine.js");

const modelPath = path.resolve(__dirname, "../../../addons/point_of_sale/static/src/app/models/accounting/product_template_accounting.js");
let source = fs.readFileSync(modelPath, "utf8")
    .replace(/^import .*;\n/gm, "")
    .replace("export class ProductTemplateAccounting", "class ProductTemplateAccounting")
    .concat("\nmodule.exports = ProductTemplateAccounting;\n");
const sandbox = {
    module: { exports: {} }, Base: class {}, alert() {}, _t: (value) => value,
    roundPrecision: (value, precision) => Math.round((value / precision) + Math.sign(value) * Number.EPSILON) * precision,
};
vm.runInNewContext(source, sandbox, { filename: modelPath });
const LegacyProduct = sandbox.module.exports;

const now = Date.now();
let activeRules = [];
const makePricelist = (item_ids) => {
    item_ids.forEach((rule, index) => rule.id ??= index + 1);
    return {
    item_ids, currency_id: { id: 1, rate: 1 },
    getRulesByProductId: (value) => item_ids.filter((rule) => rule.product_id?.id === value),
    getRulesByTmplId: (value) => item_ids.filter((rule) => rule.product_tmpl_id?.id === value),
    getCategoryRulesIds: (values) => item_ids.filter((rule) => rule.categ_id && values.includes(rule.categ_id.id)).map((rule) => rule.id),
    getGlobalRulesIds: () => item_ids.filter((rule) => !rule.product_id && !rule.product_tmpl_id && !rule.categ_id).map((rule) => rule.id),
    findBestRule(rules, quantity) {
        return rules.filter((rule) => (!rule.date_start || rule.date_start <= now) && (!rule.date_end || rule.date_end >= now) && (!rule.min_quantity || rule.min_quantity <= quantity))
            .reduce((best, rule) => !best || (rule.min_quantity || 0) > (best.min_quantity || 0) ? rule : best, null);
    },
};
};
const product = { id: 7, lst_price: 100, standard_price: 60, parentCategories: [3], product_tmpl_id: null };
const template = new LegacyProduct();
Object.assign(template, { id: 4, list_price: 100, standard_price: 60, parentCategories: [3], models: {
    "pos.config": { getFirst: () => ({ currency_id: { id: 1, rate: 1 } }) },
    "product.pricelist.item": { readMany: (ids) => activeRules.filter((rule) => ids.includes(rule.id)) },
} });
product.product_tmpl_id = template;

const vectors = [
    ["fixed", [{ product_id: { id: 7 }, compute_price: "fixed", fixed_price: 42 }], 1],
    ["percentage", [{ product_tmpl_id: { id: 4 }, compute_price: "percentage", percent_price: 15 }], 1],
    ["formula standard base", [{ categ_id: { id: 3 }, compute_price: "formula", base: "standard_price", price_discount: 10, price_round: 5, price_surcharge: 2, price_min_margin: -20, price_max_margin: 10 }], 1],
    ["quantity", [{ compute_price: "fixed", fixed_price: 90 }, { compute_price: "fixed", fixed_price: 70, min_quantity: 10 }], 12],
    ["date", [{ compute_price: "fixed", fixed_price: 10, date_end: now - 1 }, { compute_price: "fixed", fixed_price: 80, date_start: now - 1, date_end: now + 1 }], 1],
];
for (const [name, rules, quantity] of vectors) {
    activeRules = rules;
    const pricelist = makePricelist(rules);
    const expected = template.getPrice(pricelist, quantity, 0, false, product);
    assert.equal(port.computePrice(product, pricelist, quantity, now), expected, name);
}
const base = makePricelist([{ id: 100, compute_price: "percentage", percent_price: 10 }]);
const nested = makePricelist([{ id: 101, compute_price: "formula", base: "pricelist", base_pricelist_id: base, price_surcharge: 5 }]);
activeRules = [...base.item_ids, ...nested.item_ids];
assert.equal(port.computePrice(product, nested, 1, now), template.getPrice(nested, 1, 0, false, product), "formula pricelist base");
console.log(`pricelist_engine.test.js: ${vectors.length + 1} differential vectors OK`);
