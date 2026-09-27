"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const port = require("../static/src/tax_engine.js");

const legacyFile = path.resolve(__dirname, "../../../addons/account/static/src/helpers/account_tax.js");
let source = fs.readFileSync(legacyFile, "utf8")
    .replace(/^import .*;\n/gm, "")
    .replace("export const accountTaxHelpers", "const accountTaxHelpers")
    .concat("\nmodule.exports = accountTaxHelpers;\n");
const sandbox = {
    module: { exports: {} },
    roundPrecision: port.roundPrecision,
    floatIsZero: (value, digits) => Math.abs(value) < Number(`1e-${digits}`) / 2,
};
vm.runInNewContext(source, sandbox, { filename: legacyFile });
const legacy = sandbox.module.exports;

const tax = (id, values = {}) => ({
    id, sequence: id, amount_type: "percent", amount: 10, price_include: false,
    include_base_amount: false, is_base_affected: true, has_negative_factor: false,
    children_tax_ids: [], ...values,
});
const vectors = [
    { name: "excluded percent", taxes: [tax(1)], price: 100, quantity: 2, options: { precision_rounding: 0.01 } },
    { name: "included percent batch", taxes: [tax(1, { amount: 10, price_include: true }), tax(2, { amount: 5, price_include: true })], price: 115, quantity: 1, options: { precision_rounding: 0.01 } },
    { name: "fixed plus cascading", taxes: [tax(1, { amount_type: "fixed", amount: 3, include_base_amount: true }), tax(2, { amount: 20 })], price: 10, quantity: 2, options: { precision_rounding: 0.01 } },
    { name: "division excluded", taxes: [tax(1, { amount_type: "division", amount: 20 })], price: 80, quantity: 1, options: { precision_rounding: 0.01 } },
    { name: "division included", taxes: [tax(1, { amount_type: "division", amount: 20, price_include: true })], price: 100, quantity: 1, options: { precision_rounding: 0.01 } },
    { name: "group", taxes: [tax(9, { amount_type: "group", children_tax_ids: [tax(2, { sequence: 2, amount: 5 }), tax(1, { sequence: 1, amount: 7 })] })], price: 100, quantity: 1, options: { precision_rounding: 0.01 } },
    { name: "reverse charge", taxes: [tax(1, { amount: 10, has_negative_factor: true })], price: 100, quantity: 1, options: { precision_rounding: 0.01 } },
    { name: "negative fixed", taxes: [tax(1, { amount_type: "fixed", amount: 2 })], price: -10, quantity: 3, options: { precision_rounding: 0.01 } },
    { name: "total included mode", taxes: [tax(1, { amount: 10 }), tax(2, { amount: 5, include_base_amount: true })], price: 115, quantity: 1, options: { precision_rounding: 0.01, special_mode: "total_included" } },
    { name: "global rounding", taxes: [tax(1, { amount: 8.25 })], price: 9.99, quantity: 3, options: { precision_rounding: 0.01, rounding_method: "round_globally" } },
];
const plain = (value) => JSON.parse(JSON.stringify(value));
for (const vector of vectors) {
    const expected = plain(legacy.get_tax_details(vector.taxes, vector.price, vector.quantity, vector.options));
    const actual = plain(port.accountTaxHelpers.get_tax_details(vector.taxes, vector.price, vector.quantity, vector.options));
    assert.deepEqual(actual, expected, vector.name);
}
assert.equal(typeof port.accountTaxHelpers.get_tax_details, "function");
const sourceTax = tax(20, { amount: 10, fiscal_position_ids: [4] });
const mapped = tax(21, { amount: 5 });
const computed = port.computeLines([{ price: 100, quantity: 1, discount: 0, taxIds: [20] }], {
    taxes: [sourceTax, mapped],
    fiscalPosition: { tax_ids: [20], tax_map: { 20: [21] } },
    precision: 0.01,
});
assert.deepEqual({ subtotal: computed.subtotal, tax: computed.tax, total: computed.total }, { subtotal: 100, tax: 5, total: 105 });
const discount = port.computeLines([{ price: -10, quantity: 1, discount: 0, taxIds: [20] }], {
    taxes: [sourceTax, mapped],
    fiscalPosition: { tax_ids: [20], tax_map: { 20: [21] } },
    precision: 0.01,
});
assert.deepEqual(discount.lines[0].mappedTaxIds, [21], "source discount taxes must map once");
assert.deepEqual(port.mapTaxes([sourceTax], { tax_ids: [], tax_map: {} }, [sourceTax]), []);

const globalVectors = [
    { name: "positive residual", prices: [0.05, 0.05, 0.05], rate: 10 },
    { name: "weighted residual", prices: [0.06, 0.04, 0.03], rate: 10 },
    { name: "negative residual", prices: [-0.05, -0.05, -0.05], rate: 10 },
];
for (const vector of globalVectors) {
    const currentTax = tax(30, { amount: vector.rate });
    const lines = vector.prices.map((price) => ({ price, quantity: 1, discount: 0, taxIds: [30] }));
    const baseLines = lines.map((line) => ({
        tax_ids: [currentTax], price_unit: line.price, quantity: line.quantity, discount: line.discount,
        currency_id: { id: 1, rounding: 0.01, decimal_places: 2 }, rate: 1,
    }));
    const company = { currency_id: baseLines[0].currency_id, tax_calculation_rounding_method: "round_globally" };
    legacy.add_tax_details_in_base_lines(baseLines, company);
    legacy.round_base_lines_tax_details(baseLines, company);
    const expected = baseLines.map((line) => ({
        subtotal: port.roundPrecision(line.tax_details.raw_total_excluded_currency, 0.01) + line.tax_details.delta_total_excluded_currency,
        tax: line.tax_details.taxes_data.reduce((sum, item) => sum + item.tax_amount_currency, 0),
        total: port.roundPrecision(line.tax_details.raw_total_excluded_currency, 0.01) + line.tax_details.delta_total_excluded_currency +
            line.tax_details.taxes_data.reduce((sum, item) => sum + item.tax_amount_currency, 0),
    }));
    const actual = port.computeLines(lines, { taxes: [currentTax], precision: 0.01, roundingMethod: "round_globally" });
    assert.deepEqual(plain(actual.lines.map(({ subtotal, tax, total }) => ({ subtotal, tax, total }))), plain(expected), vector.name);
}
const cashRoundingVectors = [
    [52.54, 0.05, "HALF-UP", 52.55],
    [52.54, 1, "DOWN", 52],
    [52.54, 10, "UP", 60],
    [-52.54, 0.05, "HALF-UP", -52.55],
    [-52.54, 1, "DOWN", -52],
    [-52.54, 10, "UP", -60],
];
for (const [value, precision, method, expected] of cashRoundingVectors) {
    assert.equal(port.roundPrecision(value, precision, method), expected, `${value} ${precision} ${method}`);
}
console.log(`tax_engine.test.js: ${vectors.length} detail + ${globalVectors.length} global pipeline + ${cashRoundingVectors.length} cash rounding vectors OK`);
