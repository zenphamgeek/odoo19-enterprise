(() => {
    "use strict";

    const { createElement: h, useState, useEffect, useMemo } = window.React;
    const plugins = window.posReactPlugins;
    if (!plugins) return;

    // Default Initial Demo Tickets for Kitchen Prep Display
    const INITIAL_TICKETS = [
        {
            id: "ticket-101",
            orderNumber: "#001",
            tableNumber: "Table 4",
            createdAt: Date.now() - 4 * 60 * 1000, // 4 mins ago
            stage: "in_progress", // to_prep, in_progress, ready, completed
            note: "Gluten conscious, extra hot coffee",
            lines: [
                { name: "Croissant", qty: 2, done: true },
                { name: "Espresso", qty: 2, done: false },
                { name: "Avocado Toast", qty: 1, done: false }
            ]
        },
        {
            id: "ticket-102",
            orderNumber: "#002",
            tableNumber: "Table 7 (Patio)",
            createdAt: Date.now() - 11 * 60 * 1000, // 11 mins ago (urgent)
            stage: "to_prep",
            note: "Dine-in, deliver together",
            lines: [
                { name: "Latte Macchiato", qty: 2, done: false },
                { name: "Blueberry Muffin", qty: 1, done: false }
            ]
        },
        {
            id: "ticket-103",
            orderNumber: "#003",
            tableNumber: "Takeout",
            createdAt: Date.now() - 2 * 60 * 1000, // 2 mins ago
            stage: "ready",
            note: "Bag for takeaway with napkins",
            lines: [
                { name: "Cold Brew Nitro", qty: 1, done: true },
                { name: "Chocolate Cookie", qty: 2, done: true }
            ]
        }
    ];

    // Reactive Kitchen Service Singleton
    const listeners = new Set();
    let currentTickets = [...INITIAL_TICKETS];

    // Try restoring tickets from localStorage
    try {
        const stored = localStorage.getItem("pos_react_kitchen_tickets");
        if (stored) {
            currentTickets = JSON.parse(stored);
        }
    } catch (_) {}

    function persistTickets() {
        try {
            localStorage.setItem("pos_react_kitchen_tickets", JSON.stringify(currentTickets));
        } catch (_) {}
    }

    const KitchenService = {
        getTickets() {
            return currentTickets;
        },
        dispatchOrder({ orderNumber, tableNumber, lines, note }) {
            const newTicket = {
                id: `ticket-${Date.now()}`,
                orderNumber: orderNumber || `#${String(currentTickets.length + 1).padStart(3, "0")}`,
                tableNumber: tableNumber ? (typeof tableNumber === "string" ? tableNumber : `Table ${tableNumber}`) : "Takeout",
                createdAt: Date.now(),
                stage: "to_prep",
                note: note || "",
                lines: (lines || []).map((l) => ({
                    name: l.product?.name || l.name || "Custom Item",
                    qty: l.quantity || l.qty || 1,
                    done: false,
                    note: l.note || ""
                }))
            };
            currentTickets = [newTicket, ...currentTickets];
            persistTickets();
            this.notify();
            return newTicket;
        },
        updateStage(ticketId, nextStage) {
            currentTickets = currentTickets.map((t) => {
                if (t.id === ticketId) {
                    return { ...t, stage: nextStage };
                }
                return t;
            });
            persistTickets();
            this.notify();
        },
        toggleLineDone(ticketId, lineIdx) {
            currentTickets = currentTickets.map((t) => {
                if (t.id === ticketId) {
                    const newLines = [...t.lines];
                    if (newLines[lineIdx]) {
                        newLines[lineIdx] = { ...newLines[lineIdx], done: !newLines[lineIdx].done };
                    }
                    return { ...t, lines: newLines };
                }
                return t;
            });
            persistTickets();
            this.notify();
        },
        clearCompleted() {
            currentTickets = currentTickets.filter((t) => t.stage !== "completed");
            persistTickets();
            this.notify();
        },
        subscribe(listener) {
            listeners.add(listener);
            return () => listeners.delete(listener);
        },
        notify() {
            for (const fn of listeners) {
                try { fn(currentTickets); } catch (_) {}
            }
        }
    };

    window.posReactKitchenService = KitchenService;

    // Helper: format elapsed minutes
    function getElapsedInfo(createdAt) {
        const diffMs = Math.max(0, Date.now() - createdAt);
        const mins = Math.floor(diffMs / 60000);
        const secs = Math.floor((diffMs % 60000) / 1000);
        return {
            text: mins > 0 ? `${mins}m ${secs}s` : `${secs}s`,
            urgent: mins >= 10
        };
    }

    function KitchenPrepDisplayScreen({ setScreen }) {
        const [tickets, setTickets] = useState(() => KitchenService.getTickets());
        const [activeFilter, setActiveFilter] = useState("all");
        const [now, setNow] = useState(Date.now());

        useEffect(() => {
            const unsub = KitchenService.subscribe((updated) => setTickets([...updated]));
            const timer = setInterval(() => setNow(Date.now()), 1000);
            return () => {
                unsub();
                clearInterval(timer);
            };
        }, []);

        const counts = useMemo(() => {
            return {
                all: tickets.length,
                to_prep: tickets.filter((t) => t.stage === "to_prep").length,
                in_progress: tickets.filter((t) => t.stage === "in_progress").length,
                ready: tickets.filter((t) => t.stage === "ready").length,
                completed: tickets.filter((t) => t.stage === "completed").length
            };
        }, [tickets]);

        const filteredTickets = useMemo(() => {
            if (activeFilter === "all") return tickets;
            return tickets.filter((t) => t.stage === activeFilter);
        }, [tickets, activeFilter]);

        return h("div", { className: "pos-kitchen-screen" },
            // Top Header
            h("div", { className: "pos-kitchen-header" },
                h("div", { className: "pos-kitchen-header-left" },
                    h("button", {
                        type: "button",
                        className: "pos-btn pos-btn-back",
                        onClick: () => setScreen(null),
                        title: "Back to Register"
                    }, "← Back to Register"),
                    h("h2", { className: "pos-kitchen-title" },
                        h("span", null, "👨‍🍳"),
                        h("span", null, "Kitchen & Bar Preparation Display")
                    )
                ),
                h("div", { className: "pos-kitchen-header-right" },
                    h("span", { className: "pos-floor-stats-badge" },
                        `${counts.to_prep + counts.in_progress} Active Tickets`
                    ),
                    counts.completed > 0 ? h("button", {
                        type: "button",
                        className: "pos-btn pos-btn-takeout",
                        onClick: () => KitchenService.clearCompleted(),
                        title: "Archive completed tickets"
                    }, "Clear Completed") : null
                )
            ),

            // Subbar: Stage Filters
            h("div", { className: "pos-kitchen-subbar" },
                h("div", { className: "pos-kitchen-filters", role: "tablist" },
                    [
                        { id: "all", label: "All Orders", count: counts.all },
                        { id: "to_prep", label: "To Prepare", count: counts.to_prep },
                        { id: "in_progress", label: "In Progress", count: counts.in_progress },
                        { id: "ready", label: "Ready to Serve", count: counts.ready },
                        { id: "completed", label: "Done", count: counts.completed },
                    ].map((f) =>
                        h("button", {
                            key: f.id,
                            type: "button",
                            role: "tab",
                            "aria-selected": activeFilter === f.id,
                            className: `pos-kitchen-filter-btn ${activeFilter === f.id ? "active" : ""}`,
                            onClick: () => setActiveFilter(f.id)
                        },
                            h("span", null, f.label),
                            h("span", { style: { opacity: 0.75, fontSize: "11px" } }, `(${f.count})`)
                        )
                    )
                ),
                h("div", { style: { fontSize: "12px", color: "var(--pos-text-secondary)", fontFamily: "var(--pos-font-mono)" } },
                    new Date(now).toLocaleTimeString()
                )
            ),

            // Grid of Tickets
            h("div", { className: "pos-kitchen-grid-container" },
                filteredTickets.length === 0
                    ? h("div", { className: "pos-floor-empty", style: { padding: "40px", textAlign: "center", color: "var(--pos-text-secondary)" } },
                        h("span", { style: { fontSize: "36px", display: "block", marginBottom: "8px" } }, "☕"),
                        "No orders in this stage right now."
                    )
                    : h("div", { className: "pos-kitchen-grid" },
                        filteredTickets.map((ticket) => {
                            const elapsed = getElapsedInfo(ticket.createdAt);
                            return h("div", {
                                key: ticket.id,
                                className: `pos-kitchen-ticket stage-${ticket.stage}`
                            },
                                // Ticket Header
                                h("div", { className: "pos-ticket-header" },
                                    h("span", { className: "pos-ticket-order-num" }, ticket.orderNumber),
                                    h("span", { className: "pos-ticket-table-badge" }, ticket.tableNumber)
                                ),

                                // Meta (Time & Stage)
                                h("div", { className: "pos-ticket-meta" },
                                    h("span", { className: `pos-ticket-timer ${elapsed.urgent ? "urgent" : ""}` },
                                        h("span", null, "⏱️"),
                                        h("span", null, elapsed.text)
                                    ),
                                    h("span", { style: { textTransform: "capitalize", fontWeight: 600 } },
                                        ticket.stage.replace("_", " ")
                                    )
                                ),

                                // Order Lines
                                h("div", { className: "pos-ticket-lines" },
                                    ticket.note ? h("div", { className: "pos-ticket-note", style: { marginBottom: "4px" } }, `📌 ${ticket.note}`) : null,
                                    ticket.lines.map((line, idx) =>
                                        h("div", {
                                            key: idx,
                                            className: `pos-ticket-line ${line.done ? "done" : ""}`,
                                            onClick: () => KitchenService.toggleLineDone(ticket.id, idx),
                                            title: "Click to toggle ready status"
                                        },
                                            h("span", { className: "pos-ticket-qty" }, `${line.qty}×`),
                                            h("div", { className: "pos-ticket-product" },
                                                h("div", null, line.name),
                                                line.note ? h("div", { className: "pos-ticket-note" }, line.note) : null
                                            ),
                                            h("span", { style: { opacity: line.done ? 1 : 0.2 } }, line.done ? "✅" : "⭕")
                                        )
                                    )
                                ),

                                // Ticket Action Controls
                                h("div", { className: "pos-ticket-actions" },
                                    ticket.stage === "to_prep" ? h("button", {
                                        type: "button",
                                        className: "pos-ticket-btn start-btn",
                                        onClick: () => KitchenService.updateStage(ticket.id, "in_progress")
                                    }, "🔥 Start Prep") : null,

                                    ticket.stage === "in_progress" ? h("button", {
                                        type: "button",
                                        className: "pos-ticket-btn ready-btn",
                                        onClick: () => KitchenService.updateStage(ticket.id, "ready")
                                    }, "✅ Mark Ready") : null,

                                    ticket.stage === "ready" ? h("button", {
                                        type: "button",
                                        className: "pos-ticket-btn complete-btn",
                                        onClick: () => KitchenService.updateStage(ticket.id, "completed")
                                    }, "🍽️ Serve / Done") : null,

                                    ticket.stage === "completed" ? h("span", {
                                        style: { fontSize: "12px", color: "var(--pos-text-muted)", alignSelf: "center", margin: "auto" }
                                    }, "Completed") : null
                                )
                            );
                        })
                    )
            )
        );
    }

    plugins.register("screen", "pos_react.kitchen.display", {
        label: "Kitchen Display",
        component: KitchenPrepDisplayScreen
    });
})();
