(function (root, factory) {
    const engine = factory();
    if (typeof module === "object" && module.exports) module.exports = engine;
    else root.PosReactTaxEngine = engine;
})(typeof globalThis === "object" ? globalThis : this, function () {
    "use strict";

    const reversed = (items) => [...items].reverse();
    const sorted = (items, compare) => [...items].sort(compare);
    function roundPrecision(value, precision, method = "HALF-UP") {
        if (!value) return 0;
        if (!precision || precision < 0) precision = 1;
        let factor = precision;
        let normalized = value / factor;
        const inverted = factor < 1;
        if (inverted) normalized = value * (factor = Math.round(1 / factor));
        const sign = Math.sign(normalized);
        const epsilon = Math.pow(2, Math.log2(Math.abs(normalized)) - 50);
        let result;
        if (method === "DOWN") result = Math.trunc(normalized + sign * epsilon);
        else if (method === "UP") result = Math.trunc(normalized + sign * (1 - epsilon));
        else if (method === "HALF-UP") result = Math.round(normalized + sign * epsilon);
        else throw new Error(`Unknown rounding method: ${method}`);
        return inverted ? result / factor : result * factor;
    }

    const accountTaxHelpers = {
        flatten_taxes_and_sort_them(taxes) {
            const order = (values) => sorted(values, (a, b) => a.sequence - b.sequence || a.id - b.id);
            const group_per_tax = {};
            const sorted_taxes = [];
            for (const tax of order(taxes)) {
                if (tax.amount_type === "group") {
                    for (const child of order(tax.children_tax_ids)) {
                        group_per_tax[child.id] = tax;
                        sorted_taxes.push(child);
                    }
                } else sorted_taxes.push(tax);
            }
            return { sorted_taxes, group_per_tax };
        },

        batch_for_taxes_computation(taxes, { special_mode = null, filter_tax_function = null } = {}) {
            let { sorted_taxes, group_per_tax } = this.flatten_taxes_and_sort_them(taxes);
            if (filter_tax_function) sorted_taxes = sorted_taxes.filter(filter_tax_function);
            const result = { batch_per_tax: {}, group_per_tax, sorted_taxes };
            let batch = [];
            let is_base_affected = false;
            for (const tax of reversed(sorted_taxes)) {
                if (batch.length) {
                    const same = tax.amount_type === batch[0].amount_type &&
                        (special_mode || tax.price_include === batch[0].price_include) &&
                        tax.include_base_amount === batch[0].include_base_amount &&
                        ((tax.include_base_amount && !is_base_affected) || !tax.include_base_amount);
                    if (!same) {
                        for (const item of batch) result.batch_per_tax[item.id] = batch;
                        batch = [];
                    }
                }
                is_base_affected = tax.is_base_affected;
                batch.push(tax);
            }
            for (const item of batch) result.batch_per_tax[item.id] = batch;
            return result;
        },

        propagate_extra_taxes_base(taxes, tax, data, { special_mode = null } = {}) {
            const before = [];
            for (const item of taxes) {
                if (data[tax.id].batch.includes(item)) break;
                before.push(item);
            }
            const after = [];
            for (const item of reversed(taxes)) {
                if (data[tax.id].batch.includes(item)) break;
                after.push(item);
            }
            const add = (other, sign) => {
                const amount = data[tax.id].tax_amount;
                if (!("tax_amount" in data[other.id])) data[other.id].extra_base_for_tax += sign * amount;
                data[other.id].extra_base_for_base += sign * amount;
            };
            if (tax.price_include) {
                if (!special_mode || special_mode === "total_included") {
                    for (const other of after) {
                        if (!tax.include_base_amount || !other.is_base_affected) add(other, -1);
                    }
                    for (const other of before) add(other, -1);
                } else if (tax.include_base_amount) {
                    for (const other of after) if (other.is_base_affected) add(other, 1);
                }
            } else if (!special_mode || special_mode === "total_excluded") {
                if (tax.include_base_amount) for (const other of after) if (other.is_base_affected) add(other, 1);
            } else {
                if (!tax.include_base_amount) for (const other of after) add(other, -1);
                for (const other of before) add(other, -1);
            }
        },

        eval_tax_amount_fixed_amount(tax, batch, raw_base, context) {
            return tax.amount_type === "fixed" ? (context.price_unit < 0 ? -1 : 1) * context.quantity * tax.amount : null;
        },
        eval_tax_amount_price_included(tax, batch, raw_base) {
            if (tax.amount_type === "percent") {
                const percentage = batch.reduce((sum, item) => sum + item.amount, 0) / 100;
                return raw_base * (percentage !== -1 ? 1 / (1 + percentage) : 0) * tax.amount / 100;
            }
            return tax.amount_type === "division" ? raw_base * tax.amount / 100 : null;
        },
        eval_tax_amount_price_excluded(tax, batch, raw_base) {
            if (tax.amount_type === "percent") return raw_base * tax.amount / 100;
            if (tax.amount_type === "division") {
                const percentage = batch.reduce((sum, item) => sum + item.amount, 0) / 100;
                return raw_base * tax.amount / 100 / (percentage === 1 ? 1 : 1 - percentage);
            }
            return null;
        },

        normalize_target_factors(target_factors) {
            const factors = target_factors.map((item, index) => [index, Math.abs(item.factor)]);
            factors.sort((a, b) => b[1] - a[1]);
            const total = factors.reduce((sum, item) => sum + item[1], 0);
            return factors.map((item) => [item[0], total ? item[1] / total : 1 / factors.length]);
        },

        distribute_delta_amount_smoothly(precision_digits, delta_amount, target_factors) {
            const precision = Number(`1e-${precision_digits}`);
            const distributed = target_factors.map(() => 0);
            if (Math.abs(delta_amount) < precision / 2) return distributed;
            const sign = delta_amount < 0 ? -1 : 1;
            const errors = Math.round(Math.abs(delta_amount / precision));
            let remaining = errors;
            const factors = this.normalize_target_factors(target_factors);
            for (const [index, factor] of factors) {
                if (!remaining) break;
                const amount = Math.min(Math.round(factor * errors), remaining);
                remaining -= amount;
                distributed[index] += sign * amount * precision;
            }
            for (let index = 0; index < remaining; index++) distributed[factors[index][0]] += sign * precision;
            return distributed;
        },

        get_tax_details(taxes, price_unit, quantity, {
            precision_rounding = null, rounding_method = "round_per_line", product = null,
            product_uom = null, special_mode = null, filter_tax_function = null,
        } = {}) {
            const batching = this.batch_for_taxes_computation(taxes, { special_mode, filter_tax_function });
            const sorted_taxes = batching.sorted_taxes;
            const data = {};
            const reverse_data = {};
            for (const tax of sorted_taxes) {
                const price_include = tax.has_negative_factor ? false : special_mode === "total_included" ? true : special_mode === "total_excluded" ? false : tax.price_include;
                data[tax.id] = { tax, price_include, extra_base_for_tax: 0, extra_base_for_base: 0, group: batching.group_per_tax[tax.id], batch: batching.batch_per_tax[tax.id] };
                if (tax.has_negative_factor) reverse_data[tax.id] = { ...data[tax.id], is_reverse_charge: true };
            }
            let raw_base = quantity * price_unit;
            if (rounding_method === "round_per_line") raw_base = roundPrecision(raw_base, precision_rounding);
            const context = { product: product || {}, uom: product_uom || {}, price_unit, quantity, raw_base, special_mode };
            const evaluate = (method, tax) => {
                if ("tax_amount" in data[tax.id]) return;
                let amount = method.call(this, tax, data[tax.id].batch, raw_base + data[tax.id].extra_base_for_tax, context);
                if (amount === null) return;
                if (rounding_method === "round_per_line") amount = roundPrecision(amount, precision_rounding);
                data[tax.id].tax_amount = amount;
                if (tax.has_negative_factor) reverse_data[tax.id].tax_amount = -amount;
                this.propagate_extra_taxes_base(sorted_taxes, tax, data, { special_mode });
            };
            for (const tax of reversed(sorted_taxes)) evaluate(this.eval_tax_amount_fixed_amount, tax);
            for (const tax of reversed(sorted_taxes)) if (data[tax.id].price_include) evaluate(this.eval_tax_amount_price_included, tax);
            for (const tax of sorted_taxes) if (!data[tax.id].price_include) evaluate(this.eval_tax_amount_price_excluded, tax);
            const subsequent = [];
            for (const tax of reversed(sorted_taxes)) {
                const item = data[tax.id];
                if (!("tax_amount" in item)) continue;
                const batch_amount = item.batch.reduce((sum, other) => sum + data[other.id].tax_amount, 0) +
                    item.batch.filter((other) => other.has_negative_factor).reduce((sum, other) => sum + reverse_data[other.id].tax_amount, 0);
                let base = raw_base + item.extra_base_for_base;
                if (item.price_include && (!special_mode || special_mode === "total_included")) base -= batch_amount;
                item.base = base;
                item.taxes = tax.include_base_amount ? [...subsequent] : [];
                if (tax.has_negative_factor) Object.assign(reverse_data[tax.id], { base, taxes: item.taxes });
                if (tax.is_base_affected) subsequent.push(tax);
            }
            const list = [];
            for (const tax of sorted_taxes) if ("tax_amount" in data[tax.id]) {
                list.push(data[tax.id]);
                if (tax.has_negative_factor) list.push(reverse_data[tax.id]);
            }
            const total_excluded = list.length ? list[0].base : raw_base;
            return {
                total_excluded,
                total_included: total_excluded + list.reduce((sum, item) => sum + item.tax_amount, 0),
                taxes_data: list.map((item) => ({ tax: item.tax, taxes: item.taxes, group: batching.group_per_tax[item.tax.id], batch: batching.batch_per_tax[item.tax.id], tax_amount: item.tax_amount, price_include: item.price_include, base_amount: item.base, is_reverse_charge: item.is_reverse_charge || false })),
            };
        },
    };

    function mapTaxes(taxes, fiscalPosition, allTaxes) {
        if (!fiscalPosition) return taxes;
        if (!fiscalPosition.tax_ids?.length) return taxes.some((tax) => tax.fiscal_position_ids?.length) ? [] : taxes;
        const ids = taxes.flatMap((tax) => fiscalPosition.tax_map?.[tax.id] || [tax.id]);
        return allTaxes.filter((tax) => ids.includes(tax.id));
    }

    function computeLines(lines, { taxes, fiscalPosition = null, precision, roundingMethod = "round_per_line" }) {
        const byId = new Map(taxes.map((tax) => [tax.id, tax]));
        const computed = lines.map((line) => {
            const sourceTaxes = line.taxIds.map((id) => byId.get(id)).filter(Boolean);
            const mappedTaxes = mapTaxes(sourceTaxes, fiscalPosition, taxes);
            const details = accountTaxHelpers.get_tax_details(mappedTaxes, line.price * (1 - (line.discount || 0) / 100), line.quantity, {
                precision_rounding: precision,
                rounding_method: roundingMethod,
            });
            return { ...line, subtotal: details.total_excluded, total: details.total_included, tax: details.total_included - details.total_excluded, taxDetails: details, mappedTaxIds: mappedTaxes.map((tax) => tax.id) };
        });
        if (roundingMethod === "round_globally") {
            const rawTaxTotal = computed.reduce((sum, line) => sum + line.tax, 0);
            for (const line of computed) {
                line.subtotal = roundPrecision(line.subtotal, precision);
                line.tax = roundPrecision(line.tax, precision);
            }
            const taxDelta = roundPrecision(rawTaxTotal, precision) - computed.reduce((sum, line) => sum + line.tax, 0);
            const precisionDigits = Math.max(0, Math.round(-Math.log10(precision)));
            const distributed = accountTaxHelpers.distribute_delta_amount_smoothly(
                precisionDigits,
                taxDelta,
                computed.map((line) => ({ factor: line.tax }))
            );
            for (let index = 0; index < computed.length; index++) {
                computed[index].tax += distributed[index];
                computed[index].total = computed[index].subtotal + computed[index].tax;
            }
        }
        return {
            lines: computed,
            subtotal: roundPrecision(computed.reduce((sum, line) => sum + line.subtotal, 0), precision),
            tax: roundPrecision(computed.reduce((sum, line) => sum + line.tax, 0), precision),
            total: roundPrecision(computed.reduce((sum, line) => sum + line.total, 0), precision),
        };
    }

    return { accountTaxHelpers, roundPrecision, mapTaxes, computeLines };
});
