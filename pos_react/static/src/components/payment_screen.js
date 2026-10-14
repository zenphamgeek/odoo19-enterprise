(() => {
    "use strict";

    const { createElement: h, useState, useMemo } = window.React;

    /**
     * Dedicated Fullscreen Payment Screen Component
     * Multi-tender split payments, quick cash bills, change calculation & invoice toggle.
     */
    function PosReactPaymentScreen({ context, onValidate, onBack, onCustomerClick }) {
        const totalDue = Number(context.total.toFixed(context.currency?.decimalPlaces || 2));
        const formatMoney = context.formatMoney || ((val) => "$" + Number(val).toFixed(2));
        const cashMethodId = context.cashMethodId;
        const electronicMethods = context.electronicPaymentMethods || [];
        const customer = context.customer;

        const [paymentLines, setPaymentLines] = useState(() => {
            // Default to full cash payment if cashMethodId exists
            if (cashMethodId && totalDue > 0) {
                return [{
                    id: crypto.randomUUID(),
                    methodId: cashMethodId,
                    name: "Cash",
                    amount: totalDue,
                    isCash: true,
                }];
            }
            return [];
        });

        const [tenderInput, setTenderInput] = useState("");
        const [toInvoice, setToInvoice] = useState(false);
        const [isSubmitting, setIsSubmitting] = useState(false);
        const [error, setError] = useState("");

        const totalPaid = useMemo(() => {
            const sum = paymentLines.reduce((acc, line) => acc + Number(line.amount || 0), 0);
            return Number(sum.toFixed(context.currency?.decimalPlaces || 2));
        }, [paymentLines, context.currency]);

        const remaining = Math.max(0, Number((totalDue - totalPaid).toFixed(context.currency?.decimalPlaces || 2)));
        const change = Math.max(0, Number((totalPaid - totalDue).toFixed(context.currency?.decimalPlaces || 2)));

        const addPayment = (methodId, name, isCash = false, amountToAdd = null) => {
            setError("");
            const amt = amountToAdd !== null
                ? amountToAdd
                : (tenderInput ? Number(tenderInput) : (remaining > 0 ? remaining : 0));

            if (amt <= 0) return;

            setPaymentLines((prev) => [
                ...prev,
                {
                    id: crypto.randomUUID(),
                    methodId,
                    name,
                    amount: amt,
                    isCash,
                }
            ]);
            setTenderInput("");
        };

        const removePayment = (id) => {
            setPaymentLines((prev) => prev.filter((line) => line.id !== id));
        };

        const handleQuickCash = (addition) => {
            if (!cashMethodId) return;
            const newAmount = addition === "exact" ? totalDue : (totalPaid + addition);
            // Replace cash line or add new cash line
            const existingCash = paymentLines.find((line) => line.isCash);
            if (existingCash) {
                setPaymentLines((prev) =>
                    prev.map((line) => line.id === existingCash.id ? { ...line, amount: newAmount } : line)
                );
            } else {
                addPayment(cashMethodId, "Cash", true, newAmount);
            }
        };

        const handleKeypad = (char) => {
            if (char === "C") {
                setTenderInput("");
            } else if (char === "⌫") {
                setTenderInput((prev) => prev.slice(0, -1));
            } else {
                setTenderInput((prev) => prev + char);
            }
        };

        const handleValidate = async () => {
            if (totalDue > 0 && totalPaid < totalDue) {
                setError("Payment incomplete. Outstanding amount remains.");
                return;
            }
            if (toInvoice && !customer) {
                setError("Please select a customer before requesting an invoice.");
                return;
            }

            setIsSubmitting(true);
            setError("");
            try {
                await onValidate({ paymentLines, toInvoice, change });
            } catch (err) {
                setError(err?.message || "Failed to validate order payment");
                setIsSubmitting(false);
            }
        };

        return h("div", { className: "pos-payment-screen" },
            // Header
            h("div", { className: "pos-payment-header" },
                h("button", {
                    type: "button",
                    className: "pos-header-btn",
                    onClick: onBack,
                    disabled: isSubmitting,
                }, "← Back to Products"),
                h("div", { style: { display: "flex", alignItems: "center", gap: "12px" } },
                    h("button", {
                        type: "button",
                        className: "pos-cashier-pill",
                        onClick: onCustomerClick,
                    },
                        h("span", null, "👤"),
                        h("span", null, customer ? customer.name : "Select Customer")
                    ),
                    h("label", { style: { display: "flex", alignItems: "center", gap: "6px", cursor: "pointer", fontSize: "14px", fontWeight: "600" } },
                        h("input", {
                            type: "checkbox",
                            checked: toInvoice,
                            onChange: (e) => setToInvoice(e.target.checked),
                        }),
                        "Invoice"
                    )
                )
            ),
            // Body 3-column Grid
            h("div", { className: "pos-payment-body" },
                // Column 1: Summary Tiles & Applied Payment Lines
                h("div", { className: "pos-payment-card" },
                    h("h3", { style: { margin: "0 0 12px", fontSize: "16px", color: "var(--pos-text-primary)" } }, "Payment Summary"),
                    h("div", { className: "pos-payment-summary-tile due-tile" },
                        h("span", { style: { color: "var(--pos-text-secondary)" } }, "Total Due"),
                        h("strong", { style: { fontSize: "18px", color: "var(--pos-primary)" } }, formatMoney(totalDue))
                    ),
                    h("div", { className: "pos-payment-summary-tile paid-tile" },
                        h("span", { style: { color: "var(--pos-text-secondary)" } }, "Total Paid"),
                        h("strong", { style: { fontSize: "18px", color: "var(--pos-success)" } }, formatMoney(totalPaid))
                    ),
                    remaining > 0 ? h("div", { className: "pos-payment-summary-tile change-tile", style: { borderLeftColor: "var(--pos-warning)" } },
                        h("span", { style: { color: "var(--pos-text-secondary)" } }, "Remaining"),
                        h("strong", { style: { fontSize: "18px", color: "var(--pos-warning)" } }, formatMoney(remaining))
                    ) : null,
                    change > 0 ? h("div", { className: "pos-payment-summary-tile change-tile" },
                        h("span", { style: { color: "var(--pos-text-secondary)" } }, "Change"),
                        h("strong", { style: { fontSize: "18px", color: "var(--pos-accent)" } }, formatMoney(change))
                    ) : null,
                    h("div", { style: { marginTop: "16px", borderTop: "1px solid var(--pos-border)", paddingTop: "12px" } },
                        h("h4", { style: { margin: "0 0 8px", fontSize: "13px", color: "var(--pos-text-secondary)" } }, "Applied Tenders"),
                        paymentLines.length === 0
                            ? h("p", { style: { color: "var(--pos-text-muted)", fontSize: "13px" } }, "No tenders applied yet")
                            : paymentLines.map((line) =>
                                h("div", {
                                    key: line.id,
                                    style: {
                                        display: "flex",
                                        justifyContent: "space-between",
                                        alignItems: "center",
                                        padding: "8px 10px",
                                        background: "var(--pos-bg-card)",
                                        borderRadius: "var(--pos-radius-sm)",
                                        marginBottom: "6px",
                                        border: "1px solid var(--pos-border)",
                                    }
                                },
                                    h("span", { style: { fontWeight: "600" } }, line.name),
                                    h("div", { style: { display: "flex", alignItems: "center", gap: "8px" } },
                                        h("strong", { style: { color: "var(--pos-accent)" } }, formatMoney(line.amount)),
                                        h("button", {
                                            type: "button",
                                            onClick: () => removePayment(line.id),
                                            style: {
                                                background: "transparent",
                                                border: "none",
                                                color: "var(--pos-danger)",
                                                cursor: "pointer",
                                                fontSize: "16px",
                                                padding: "0 4px",
                                            }
                                        }, "×")
                                    )
                                )
                            )
                    ),
                    error ? h("p", { style: { color: "var(--pos-danger)", fontSize: "13px", marginTop: "10px" }, role: "alert" }, error) : null
                ),

                // Column 2: Keypad & Quick Cash Bills
                h("div", { className: "pos-payment-card" },
                    h("h3", { style: { margin: "0 0 12px", fontSize: "16px", color: "var(--pos-text-primary)" } }, "Tender Amount"),
                    h("input", {
                        type: "text",
                        readOnly: true,
                        value: tenderInput ? formatMoney(Number(tenderInput)) : (remaining > 0 ? formatMoney(remaining) : "$0.00"),
                        style: {
                            height: "48px",
                            background: "var(--pos-bg-card)",
                            border: "1px solid var(--pos-border)",
                            borderRadius: "var(--pos-radius-sm)",
                            fontSize: "22px",
                            fontWeight: "700",
                            color: "var(--pos-text-primary)",
                            textAlign: "center",
                            fontFamily: "var(--pos-font-mono)",
                        }
                    }),
                    // Quick Cash Chips
                    cashMethodId ? h("div", { className: "pos-quick-bills" },
                        h("button", { type: "button", className: "pos-bill-chip", onClick: () => handleQuickCash("exact") }, "Exact"),
                        h("button", { type: "button", className: "pos-bill-chip", onClick: () => handleQuickCash(10) }, "+$10"),
                        h("button", { type: "button", className: "pos-bill-chip", onClick: () => handleQuickCash(20) }, "+$20"),
                        h("button", { type: "button", className: "pos-bill-chip", onClick: () => handleQuickCash(50) }, "+$50"),
                        h("button", { type: "button", className: "pos-bill-chip", onClick: () => handleQuickCash(100) }, "+$100")
                    ) : null,
                    // Keypad
                    h("div", {
                        style: {
                            display: "grid",
                            gridTemplateColumns: "repeat(3, 1fr)",
                            gap: "6px",
                            marginTop: "8px",
                        }
                    },
                        ["1", "2", "3", "4", "5", "6", "7", "8", "9", "C", "0", "⌫"].map((btn) =>
                            h("button", {
                                key: btn,
                                type: "button",
                                className: "pos-num-btn",
                                style: { height: "48px" },
                                onClick: () => handleKeypad(btn),
                            }, btn)
                        )
                    )
                ),

                // Column 3: Payment Methods & Validate
                h("div", { className: "pos-payment-card", style: { justifyContent: "space-between" } },
                    h("div", null,
                        h("h3", { style: { margin: "0 0 16px", fontSize: "16px", color: "var(--pos-text-primary)" } }, "Select Payment Method"),
                        h("div", { style: { display: "flex", flexDirection: "column", gap: "10px" } },
                            cashMethodId ? h("button", {
                                type: "button",
                                className: "pos-payment-method-btn",
                                onClick: () => addPayment(cashMethodId, "Cash", true),
                            },
                                h("span", null, "💵 Cash"),
                                h("span", { style: { fontSize: "12px", color: "var(--pos-text-muted)" } }, "Instant")
                            ) : null,
                            electronicMethods.map((m) =>
                                h("button", {
                                    key: m.id,
                                    type: "button",
                                    className: "pos-payment-method-btn",
                                    onClick: () => addPayment(m.id, m.name, false),
                                },
                                    h("span", null, "💳 " + m.name),
                                    h("span", { style: { fontSize: "12px", color: "var(--pos-text-muted)" } }, m.terminal || "Terminal")
                                )
                            )
                        )
                    ),
                    h("button", {
                        type: "button",
                        className: "pos-action-btn pay-btn pos-validate-btn",
                        style: {
                            height: "56px",
                            fontSize: "17px",
                            fontWeight: "700",
                            borderRadius: "var(--pos-radius-md)",
                        },
                        disabled: (totalDue > 0 && totalPaid < totalDue) || isSubmitting,
                        onClick: handleValidate,
                    }, isSubmitting ? "Validating Payment…" : `Validate (${formatMoney(totalDue)})`)
                )
            )
        );
    }

    window.PosReactPaymentScreen = PosReactPaymentScreen;
})();
