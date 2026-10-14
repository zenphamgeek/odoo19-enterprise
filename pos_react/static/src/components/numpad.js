(() => {
    "use strict";

    const { createElement: h, useEffect } = window.React;

    /**
     * Tactile 4x4 Numpad and POS Control Bar
     * Full parity with native enterprise POS keypad interactions and keyboard shortcuts.
     */
    function PosReactNumpad({
        activeMode = "qty",
        setMode,
        onInput,
        onDelete,
        onClear,
        onCustomerClick,
        onNoteClick,
        onRefundClick,
        onPayClick,
        disabled = false,
        total = 0,
        formatMoney,
        selectedLine = null,
        customerName = null,
    }) {
        // Global keyboard shortcut listener
        useEffect(() => {
            function handleKeyDown(event) {
                const tag = event.target.tagName;
                if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT" || event.ctrlKey || event.metaKey) {
                    return;
                }

                const key = event.key;
                if (/^[0-9]$/.test(key) || key === ".") {
                    event.preventDefault();
                    onInput?.(key);
                } else if (key === "Backspace") {
                    event.preventDefault();
                    onDelete?.();
                } else if (key === "Delete" || key === "Escape") {
                    event.preventDefault();
                    onClear?.();
                } else if (key === "q" || key === "Q") {
                    event.preventDefault();
                    setMode?.("qty");
                } else if (key === "d" || key === "D") {
                    event.preventDefault();
                    setMode?.("% Disc");
                } else if (key === "p" || key === "P") {
                    event.preventDefault();
                    setMode?.("Price");
                } else if (key === "+" || key === "-") {
                    event.preventDefault();
                    onInput?.("+/-");
                } else if (key === "Enter" || key === " ") {
                    if (total > 0 && !disabled) {
                        event.preventDefault();
                        onPayClick?.();
                    }
                }
            }

            window.addEventListener("keydown", handleKeyDown);
            return () => window.removeEventListener("keydown", handleKeyDown);
        }, [onInput, onDelete, onClear, setMode, onPayClick, total, disabled]);

        const numBtn = (label, value = label, extraClass = "") =>
            h("button", {
                type: "button",
                className: `pos-num-btn ${extraClass}`,
                disabled,
                onClick: () => onInput?.(value),
            }, label);

        const modeBtn = (label, modeKey) => {
            const isActive = activeMode === modeKey;
            return h("button", {
                type: "button",
                className: `pos-num-btn mode-btn ${isActive ? "active" : ""}`,
                disabled,
                onClick: () => setMode?.(modeKey),
            }, label);
        };

        return h("div", { className: "pos-numpad-container" },
            // 4x4 Numpad Keypad Grid
            h("div", { className: "pos-numpad-grid", role: "group", "aria-label": "Numeric keypad" },
                // Row 1
                numBtn("1"),
                numBtn("2"),
                numBtn("3"),
                modeBtn("Qty", "qty"),
                // Row 2
                numBtn("4"),
                numBtn("5"),
                numBtn("6"),
                modeBtn("% Disc", "% Disc"),
                // Row 3
                numBtn("7"),
                numBtn("8"),
                numBtn("9"),
                modeBtn("Price", "Price"),
                // Row 4
                numBtn("+/-"),
                numBtn("0"),
                numBtn("."),
                h("button", {
                    type: "button",
                    className: "pos-num-btn backspace-btn",
                    disabled,
                    "aria-label": "Backspace",
                    onClick: () => onDelete?.(),
                }, "⌫")
            ),
            // Bottom Action Bar
            h("div", { className: "pos-action-bar" },
                h("button", {
                    type: "button",
                    className: "pos-action-btn",
                    onClick: onCustomerClick,
                    title: "Select customer",
                },
                    h("span", null, "👤"),
                    h("span", null, customerName ? (customerName.length > 9 ? customerName.slice(0, 9) + "…" : customerName) : "Customer")
                ),
                h("button", {
                    type: "button",
                    className: "pos-action-btn",
                    onClick: onNoteClick,
                    title: "Add order or line note",
                },
                    h("span", null, "📝"),
                    h("span", null, "Note")
                ),
                h("button", {
                    type: "button",
                    className: "pos-action-btn",
                    onClick: onRefundClick,
                    title: "Refund previous sale",
                },
                    h("span", null, "↩"),
                    h("span", null, "Refund")
                ),
                h("button", {
                    type: "button",
                    className: "pos-action-btn pay-btn",
                    disabled: disabled || !total,
                    onClick: onPayClick,
                },
                    h("span", null, total ? `Pay ${formatMoney ? formatMoney(total) : "$" + total}` : "Pay")
                )
            )
        );
    }

    window.PosReactNumpad = PosReactNumpad;
})();
