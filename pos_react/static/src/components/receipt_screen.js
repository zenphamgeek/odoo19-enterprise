(() => {
    "use strict";

    const { createElement: h, useState } = window.React;

    /**
     * Thermal Receipt & E-Receipt Presentation Screen
     * 80mm thermal paper preview, direct browser print styles & new order lifecycle.
     */
    function PosReactReceiptScreen({ order, context, onNewOrder }) {
        const [email, setEmail] = useState("");
        const [emailSent, setEmailSent] = useState(false);
        const [isPrinting, setIsPrinting] = useState(false);

        const formatMoney = context.formatMoney || ((val) => "$" + Number(val).toFixed(2));
        const companyName = context.company?.name || "Insilos Enterprise Retail";
        const cashierName = context.pluginData?.employee?.name || context.role || "Cashier";
        const customerName = context.customer?.name || "Walk-in Customer";
        const dateStr = new Date().toLocaleString();

        const handlePrint = () => {
            setIsPrinting(true);
            setTimeout(() => {
                window.print();
                setIsPrinting(false);
            }, 100);
        };

        const handleEmailSend = (e) => {
            e.preventDefault();
            if (!email.trim() || !email.includes("@")) return;
            // Simulated / RPC email dispatch
            setEmailSent(true);
            setTimeout(() => setEmailSent(false), 5000);
        };

        const lines = (order?.lines || []).map((cmd) => {
            // cmd format is [0, 0, values] from buildCashOrder
            const values = Array.isArray(cmd) ? cmd[2] : cmd;
            const pId = Array.isArray(values.product_id) ? values.product_id[0] : values.product_id;
            const foundProduct = (context.products || []).find((p) => p.id === pId);
            const name = values.product_name || (foundProduct ? foundProduct.name : (values.product_id?.display_name || `Item #${pId}`));
            return {
                id: values.uuid || Math.random(),
                name,
                qty: values.qty || 1,
                priceUnit: values.price_unit || 0,
                discount: values.discount || 0,
                total: values.price_subtotal_incl || (values.price_unit * values.qty),
            };
        });

        const totalAmount = order?.amount_total || 0;
        const totalPaid = order?.amount_paid || totalAmount;
        const changeAmount = order?.amount_return || 0;

        return h("div", { className: "pos-receipt-screen" },
            // Receipt Paper Container
            h("div", { className: "pos-receipt-paper", role: "region", "aria-label": "Receipt Document" },
                // Header
                h("div", { className: "pos-receipt-header" },
                    h("div", { className: "pos-receipt-shop" }, companyName),
                    h("div", null, context.configName),
                    h("div", { style: { fontSize: "11px", color: "#6b7280", marginTop: "4px" } }, dateStr),
                    h("div", { style: { fontSize: "11px", marginTop: "4px", fontWeight: "600" } },
                        `Order: ${order?.name || order?.pos_reference || "DRAFT"}`
                    )
                ),

                // Cashier & Customer Info
                h("div", { style: { fontSize: "11px", marginBottom: "12px", borderBottom: "1px dashed #d1d5db", paddingBottom: "8px" } },
                    h("div", { style: { display: "flex", justifyContent: "space-between" } },
                        h("span", null, "Cashier:"),
                        h("strong", null, cashierName)
                    ),
                    h("div", { style: { display: "flex", justifyContent: "space-between", marginTop: "2px" } },
                        h("span", null, "Customer:"),
                        h("strong", null, customerName)
                    ),
                    order?.general_customer_note ? h("div", { style: { display: "flex", justifyContent: "space-between", marginTop: "2px", color: "var(--pos-accent, #0f62fe)" } },
                        h("span", null, "Note / Table:"),
                        h("strong", null, order.general_customer_note)
                    ) : null
                ),

                // Line Items Table
                h("table", { className: "pos-receipt-table" },
                    h("thead", null,
                        h("tr", null,
                            h("th", null, "Description"),
                            h("th", { style: { textAlign: "center", width: "40px" } }, "Qty"),
                            h("th", { style: { textAlign: "right", width: "65px" } }, "Total")
                        )
                    ),
                    h("tbody", null,
                        lines.map((line) =>
                            h("tr", { key: line.id },
                                h("td", null,
                                    line.name,
                                    line.discount ? h("div", { style: { fontSize: "10px", color: "#b45309" } }, `Disc: ${line.discount}%`) : null
                                ),
                                h("td", { style: { textAlign: "center" } }, line.qty),
                                h("td", { style: { textAlign: "right" } }, formatMoney(line.total))
                            )
                        )
                    )
                ),

                // Totals
                h("div", { className: "pos-receipt-total-row" },
                    h("span", null, "TOTAL"),
                    h("span", null, formatMoney(totalAmount))
                ),

                // Payments & Change
                h("div", { style: { fontSize: "11px", margin: "10px 0", lineHeight: "1.6" } },
                    h("div", { style: { display: "flex", justifyContent: "space-between" } },
                        h("span", null, "Tendered Paid:"),
                        h("span", null, formatMoney(totalPaid))
                    ),
                    changeAmount > 0 ? h("div", { style: { display: "flex", justifyContent: "space-between", fontWeight: "600" } },
                        h("span", null, "Change:"),
                        h("span", null, formatMoney(changeAmount))
                    ) : null
                ),

                // Barcode / QR Graphic Simulation
                h("div", { style: { textAlign: "center", margin: "16px 0 8px 0" } },
                    h("svg", { width: "160", height: "36", viewBox: "0 0 160 36", style: { display: "inline-block" } },
                        [...Array(30)].map((_, i) =>
                            h("rect", {
                                key: i,
                                x: i * 5 + (i % 3 === 0 ? 1 : 2),
                                y: 0,
                                width: (i % 2 === 0 ? 2 : 1) + (i % 5 === 0 ? 1 : 0),
                                height: 36,
                                fill: "#000000",
                            })
                        )
                    ),
                    h("div", { style: { fontSize: "10px", letterSpacing: "1px", color: "#6b7280", marginTop: "2px" } },
                        order?.uuid ? order.uuid.slice(0, 18) : "POS-ORDER-ACK"
                    )
                ),

                // Footer Note
                h("div", { style: { textAlign: "center", fontSize: "11px", color: "#6b7280", marginTop: "12px", borderTop: "1px dashed #d1d5db", paddingTop: "8px" } },
                    h("p", { style: { margin: "0 0 4px" } }, "Thank you for your business!"),
                    h("p", { style: { margin: 0 } }, "Please visit us again.")
                )
            ),

            // Post-Order Action Buttons
            h("div", { className: "pos-receipt-actions" },
                h("button", {
                    type: "button",
                    className: "pos-action-btn",
                    style: { flex: 1, height: "48px", fontSize: "14px" },
                    onClick: handlePrint,
                    disabled: isPrinting,
                }, "🖨️ Print Receipt"),
                h("button", {
                    type: "button",
                    className: "pos-action-btn pay-btn pos-next-order-btn",
                    style: { flex: 1.5, height: "48px", fontSize: "15px" },
                    onClick: onNewOrder,
                }, "Next Order →")
            ),

            // Email receipt form
            h("form", {
                onSubmit: handleEmailSend,
                style: { display: "flex", gap: "8px", marginTop: "12px", width: "380px" }
            },
                h("input", {
                    type: "email",
                    placeholder: "Enter customer email…",
                    value: email,
                    onChange: (e) => setEmail(e.target.value),
                    style: {
                        flex: 1,
                        height: "38px",
                        background: "var(--pos-bg-card)",
                        border: "1px solid var(--pos-border)",
                        borderRadius: "var(--pos-radius-sm)",
                        padding: "0 12px",
                        color: "var(--pos-text-primary)",
                        fontSize: "13px",
                    }
                }),
                h("button", {
                    type: "submit",
                    className: "pos-action-btn",
                    style: { height: "38px", padding: "0 14px" }
                }, emailSent ? "✓ Sent!" : "Send")
            )
        );
    }

    window.PosReactReceiptScreen = PosReactReceiptScreen;
})();
