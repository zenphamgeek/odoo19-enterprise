(() => {
    "use strict";

    const plugins = window.posReactPlugins;
    if (!plugins) return;
    const _t = (message) => window.posReactTranslate?.("pos_discount_react", message) || message;
    const taxKey = (taxIds) => [...taxIds].sort((a, b) => a - b).join("_");
    const parsePercentage = (value) => {
        const percentage = Number(value.trim());
        return value.trim() && Number.isFinite(percentage) && percentage >= 0 && percentage <= 100
            ? percentage
            : null;
    };

    const action = {
        label: _t("Global discount"),
        isVisible({ pluginData }) {
            return pluginData.role !== "minimal" && Boolean(pluginData.discount?.enabled && pluginData.discount.product);
        },
        canMutateLine(line, { pluginData }) {
            return line.productId !== pluginData.discount?.product?.id;
        },
        transformCart({ cart, lines, pluginData, taxContext }, requestedPercentage) {
            const config = pluginData.discount;
            if (pluginData.role === "minimal" || !config?.enabled || !config.product) return cart;
            const existingDiscounts = cart.filter((line) => line.productId === config.product.id);
            const percentage = requestedPercentage ?? existingDiscounts[0]?.extraTaxData?.discount_percentage;
            if (!Number.isFinite(percentage)) return cart;
            const regularLines = cart.filter((line) => line.productId !== config.product.id);
            const discountableLines = regularLines.filter((line) =>
                !config.tipProductId || line.productId !== config.tipProductId
            );
            if (!percentage) return regularLines;
            const effectiveByUuid = new Map((lines || cart).map((line) => [line.uuid, line]));
            const computedLines = window.PosReactTaxEngine.computeLines(discountableLines.map((line) => {
                const effectiveLine = effectiveByUuid.get(line.uuid) || line;
                return { ...effectiveLine, price: effectiveLine.price || 0, quantity: effectiveLine.quantity || 0, discount: effectiveLine.discount || 0 };
            }), taxContext).lines;
            const grouped = new Map();
            for (const line of computedLines) {
                const taxIds = line.taxIds || [];
                const key = taxKey(taxIds);
                const group = grouped.get(key) || { taxIds, amount: 0 };
                group.amount += (line.taxDetails.taxes_data.some((tax) => tax.price_include) ? line.total : line.subtotal) * percentage / 100;
                grouped.set(key, group);
            }
            const existingByTax = new Map(existingDiscounts.map((line) => [taxKey(line.taxIds || []), line]));
            const discountLines = [...grouped.entries()]
                .filter(([, group]) => group.amount)
                .map(([key, group]) => ({
                    uuid: existingByTax.get(key)?.uuid || crypto.randomUUID(), productId: config.product.id, quantity: 1,
                    price: -group.amount, taxIds: group.taxIds,
                    discount: 0, extraTaxData: { discount_percentage: percentage },
                }));
            return [...regularLines, ...discountLines];
        },
        async run(context, value) {
            if (!action.isVisible(context)) return false;
            const percentage = parsePercentage(value);
            if (percentage === null) {
                context.reportError?.(_t("Discount percentage must be between 0 and 100."));
                return false;
            }
            return context.replaceCart(action.transformCart(context, percentage));
        },
        component(context) {
            const { createElement: h, useEffect, useRef, useState } = window.React;
            const inputRef = useRef(null);
            const [value, setValue] = useState(String(context.pluginData.discount.percentage));
            const [error, setError] = useState("");
            const errorId = "pos-discount-percentage-error";
            const inputId = "pos-discount-percentage";

            useEffect(() => {
                inputRef.current?.focus();
                const closeOnEscape = (event) => {
                    if (event.key === "Escape") context.closeAction();
                };
                document.addEventListener("keydown", closeOnEscape);
                return () => document.removeEventListener("keydown", closeOnEscape);
            }, []);

            const submit = async (event) => {
                event.preventDefault();
                if (parsePercentage(value) === null) {
                    setError(_t("Discount percentage must be between 0 and 100."));
                    return;
                }
                if (await action.run(context, value)) context.closeAction();
            };

            return h("div", { role: "dialog", "aria-modal": "true", "aria-labelledby": "pos-discount-title" },
                h("form", { onSubmit: submit },
                    h("h2", { id: "pos-discount-title" }, _t("Global discount")),
                    h("label", { htmlFor: inputId }, _t("Discount Percentage")),
                    h("input", {
                        ref: inputRef, id: inputId, type: "number", min: "0", max: "100", step: "any",
                        value, "aria-invalid": Boolean(error), "aria-describedby": error ? errorId : undefined,
                        onChange: (event) => { setValue(event.target.value); setError(""); },
                    }),
                    error ? h("p", { id: errorId, role: "alert" }, error) : null,
                    h("button", { type: "submit" }, _t("Apply")),
                    h("button", { type: "button", onClick: context.closeAction }, _t("Cancel"))
                )
            );
        },
    };
    plugins.register("action", "pos_discount_react.global_discount", action);
})();
