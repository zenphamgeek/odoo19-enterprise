(function (root, factory) {
    const engine = factory();
    if (typeof module === "object" && module.exports) module.exports = engine;
    else root.PosReactPricelistEngine = engine;
})(typeof globalThis === "object" ? globalThis : this, function () {
    "use strict";

    const id = (value) => value && typeof value === "object" ? value.id : value;
    const roundPrecision = (value, precision) => Math.round((value / precision) + Math.sign(value) * Number.EPSILON) * precision;
    const eligible = (rule, quantity, now) => (!rule.date_start || rule.date_start <= now) &&
        (!rule.date_end || rule.date_end >= now) && (!rule.min_quantity || rule.min_quantity <= quantity);

    function best(rules, quantity, now) {
        return rules.filter((rule) => eligible(rule, quantity, now)).reduce(
            (winner, rule) => !winner || (rule.min_quantity || 0) > (winner.min_quantity || 0) ? rule : winner,
            null
        );
    }

    function computePrice(product, pricelist, quantity = 1, now = Date.now(), priceExtra = 0) {
        let price = (product.lst_price ?? product.list_price) + (priceExtra || 0);
        if (!pricelist) return price;
        const rules = pricelist.item_ids || [];
        const templateId = id(product.product_tmpl_id) || product.product_tmpl_id_id;
        const categoryIds = new Set(product.parent_category_ids || product.parentCategories || []);
        if (product.categ_id) categoryIds.add(id(product.categ_id));
        const groups = [
            rules.filter((rule) => id(rule.product_id) === product.id),
            rules.filter((rule) => id(rule.product_tmpl_id) === templateId),
            rules.filter((rule) => rule.categ_id && categoryIds.has(id(rule.categ_id))),
            rules.filter((rule) => !rule.product_id && !rule.product_tmpl_id && !rule.categ_id),
        ];
        const rule = groups.map((group) => best(group, quantity, now)).find(Boolean);
        if (!rule) return price;
        if (rule.base === "pricelist" && rule.base_pricelist_id) {
            price = computePrice(product, rule.base_pricelist_id, quantity, now, 0);
        } else if (rule.base === "standard_price") {
            price = product.standard_price;
        }
        if (rule.compute_price === "fixed") return rule.fixed_price;
        if (rule.compute_price === "percentage") return price * (1 - (rule.percent_price || 0) / 100);
        const limit = price;
        price *= 1 - (rule.price_discount || 0) / 100;
        if (rule.price_round) price = roundPrecision(price, rule.price_round);
        price += rule.price_surcharge || 0;
        if (rule.price_min_margin) price = Math.max(price, limit + rule.price_min_margin);
        if (rule.price_max_margin) price = Math.min(price, limit + rule.price_max_margin);
        return price;
    }

    return { computePrice };
});
