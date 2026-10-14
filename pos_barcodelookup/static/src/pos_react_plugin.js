(() => {
    "use strict";

    const plugins = window.posReactPlugins;
    if (!plugins) return;
    plugins.register("action", "pos_barcodelookup.create", {
        label: "Create product by barcode",
        async run({ pluginData = {}, rpc, doAction, allowProductCreation }) {
            if (!allowProductCreation || !(await allowProductCreation())) return false;
            const barcode = pluginData.barcode || window.prompt("Barcode");
            if (!barcode) return false;
            let result;
            if (rpc) {
                result = await rpc("product.template", "barcode_lookup", []);
            } else {
                const response = await fetch("/api/model/call", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        jsonrpc: "2.0",
                        method: "call",
                        params: { model: "product.template", method: "barcode_lookup", args: [], kwargs: {} },
                    }),
                });
                if (!response.ok || !response.headers.get("content-type")?.toLowerCase().includes("application/json")) return false;
                const payload = await response.json();
                if (payload.error) return false;
                result = payload.result;
            }
            if (!result?.authenticated) return false;
            if (doAction) {
                await doAction("point_of_sale.product_template_action_add_pos", {
                    additionalContext: { default_barcode: barcode },
                });
            } else {
                window.location.assign(`/insilos/action-point_of_sale.product_template_action_add_pos?default_barcode=${encodeURIComponent(barcode)}`);
            }
            return true;
        },
    });
})();
