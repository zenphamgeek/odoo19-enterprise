(() => {
    "use strict";

    const { createElement: h, useState, useMemo } = React;
    const plugins = window.posReactPlugins;
    if (!plugins) return;

    const DEFAULT_TABLES = [
        { id: 1, table_number: 1, seats: 2, floor_name: "Main Dining", active: true, is_virtual: true },
        { id: 2, table_number: 2, seats: 4, floor_name: "Main Dining", active: true, is_virtual: true },
        { id: 3, table_number: 3, seats: 4, floor_name: "Main Dining", active: true, is_virtual: true },
        { id: 4, table_number: 4, seats: 6, floor_name: "Main Dining", active: true, is_virtual: true },
        { id: 5, table_number: 5, seats: 8, floor_name: "VIP Lounge", active: true, is_virtual: true },
        { id: 6, table_number: 6, seats: 4, floor_name: "VIP Lounge", active: true, is_virtual: true },
        { id: 7, table_number: 7, seats: 2, floor_name: "Outdoor Patio", active: true, is_virtual: true },
        { id: 8, table_number: 8, seats: 4, floor_name: "Outdoor Patio", active: true, is_virtual: true },
        { id: 9, table_number: 9, seats: 4, floor_name: "Outdoor Patio", active: true, is_virtual: true },
        { id: 10, table_number: 10, seats: 2, floor_name: "Bar Counter", active: true, is_virtual: true },
        { id: 11, table_number: 11, seats: 2, floor_name: "Bar Counter", active: true, is_virtual: true },
        { id: 12, table_number: 12, seats: 2, floor_name: "Bar Counter", active: true, is_virtual: true },
    ];

    function RestaurantFloorScreen({ restaurant = {}, restaurantContext = {}, setRestaurantContext, setScreen, formatMoney, cart = [] }) {
        const rawTables = (restaurant.tables && restaurant.tables.length > 0) ? restaurant.tables : DEFAULT_TABLES;
        const [activeFloor, setActiveFloor] = useState("all");
        const [searchQuery, setSearchQuery] = useState("");
        const [guestCount, setGuestCount] = useState(restaurantContext.customerCount || 2);

        // Extract distinct floors from tables
        const floors = useMemo(() => {
            const set = new Set();
            for (const table of rawTables) {
                const floorName = Array.isArray(table.floor_id) ? table.floor_id[1] : (table.floor_name || "Main Dining");
                if (floorName) set.add(floorName);
            }
            return Array.from(set);
        }, [rawTables]);

        const filteredTables = useMemo(() => {
            return rawTables.filter((table) => {
                const floorName = Array.isArray(table.floor_id) ? table.floor_id[1] : (table.floor_name || "Main Dining");
                if (activeFloor !== "all" && floorName !== activeFloor) return false;
                if (searchQuery) {
                    const q = searchQuery.toLowerCase();
                    const numStr = String(table.table_number || table.id).toLowerCase();
                    return numStr.includes(q) || floorName.toLowerCase().includes(q);
                }
                return true;
            });
        }, [rawTables, activeFloor, searchQuery]);

        const handleSelectTable = (table) => {
            setRestaurantContext({
                tableId: table.id,
                tableNumber: table.table_number || table.id,
                customerCount: guestCount || table.seats || 2,
                isVirtual: Boolean(table.is_virtual)
            });
            setScreen(null);
        };

        const handleClearTable = () => {
            setRestaurantContext({
                tableId: false,
                tableNumber: null,
                customerCount: false
            });
            setScreen(null);
        };

        return h("div", { className: "pos-floor-screen" },
            // Top Header Bar
            h("div", { className: "pos-floor-header" },
                h("div", { className: "pos-floor-header-left" },
                    h("button", {
                        type: "button",
                        className: "pos-btn pos-btn-back",
                        onClick: () => setScreen(null),
                        title: "Back to Register"
                    }, "← Back to Register"),
                    h("h2", { className: "pos-floor-title" }, "Restaurant Floor Plan"),
                    h("span", { className: "pos-floor-stats-badge" }, `${rawTables.length} Tables · ${rawTables.reduce((acc, t) => acc + (t.seats || 0), 0)} Seats`)
                ),
                h("div", { className: "pos-floor-header-right" },
                    h("input", {
                        type: "search",
                        className: "pos-floor-search-input",
                        placeholder: "Search table number...",
                        value: searchQuery,
                        onChange: (e) => setSearchQuery(e.target.value)
                    }),
                    h("button", {
                        type: "button",
                        className: "pos-btn pos-btn-takeout",
                        onClick: handleClearTable,
                        title: "Takeout / No Table order"
                    }, "🛍️ Takeout (No Table)")
                )
            ),

            // Subbar: Floor Switcher Tabs & Guest Count Bar
            h("div", { className: "pos-floor-subbar" },
                h("div", { className: "pos-floor-tabs", role: "tablist" },
                    h("button", {
                        key: "all",
                        type: "button",
                        role: "tab",
                        "aria-selected": activeFloor === "all",
                        className: `pos-floor-tab ${activeFloor === "all" ? "active" : ""}`,
                        onClick: () => setActiveFloor("all")
                    }, "All Floors"),
                    floors.map((floor) =>
                        h("button", {
                            key: floor,
                            type: "button",
                            role: "tab",
                            "aria-selected": activeFloor === floor,
                            className: `pos-floor-tab ${activeFloor === floor ? "active" : ""}`,
                            onClick: () => setActiveFloor(floor)
                        }, floor)
                    )
                ),

                h("div", { className: "pos-guests-bar" },
                    h("span", { className: "pos-guests-label" }, "Guests:"),
                    [1, 2, 3, 4, 5, 6, 8].map((count) =>
                        h("button", {
                            key: count,
                            type: "button",
                            className: `pos-guest-chip ${guestCount === count ? "active" : ""}`,
                            onClick: () => setGuestCount(count)
                        }, `${count}`)
                    )
                )
            ),

            // Interactive Table Grid
            h("div", { className: "pos-floor-grid-container" },
                filteredTables.length === 0
                    ? h("div", { className: "pos-floor-empty" }, "No tables found matching criteria.")
                    : h("div", { className: "pos-floor-grid" },
                        filteredTables.map((table) => {
                            const isCurrent = restaurantContext.tableId === table.id;
                            const floorName = Array.isArray(table.floor_id) ? table.floor_id[1] : (table.floor_name || "Main Dining");
                            return h("div", {
                                key: table.id,
                                className: `pos-table-card ${isCurrent ? "current" : "available"}`,
                                onClick: () => handleSelectTable(table),
                                role: "button",
                                tabIndex: 0,
                                "aria-label": `Table ${table.table_number || table.id}, ${table.seats || 2} seats`
                            },
                                h("div", { className: "pos-table-card-header" },
                                    h("span", { className: "pos-table-number" }, `Table ${table.table_number || table.id}`),
                                    h("span", { className: `pos-table-status-pill ${isCurrent ? "occupied" : "available"}` },
                                        isCurrent ? "Selected" : "Available"
                                    )
                                ),
                                h("div", { className: "pos-table-card-body" },
                                    h("span", { className: "pos-table-icon" }, "🪑"),
                                    h("span", { className: "pos-table-seats" }, `${table.seats || 2} Seats`)
                                ),
                                h("div", { className: "pos-table-card-footer" },
                                    h("span", { className: "pos-table-floor-tag" }, floorName),
                                    isCurrent && cart.length > 0
                                        ? h("span", { className: "pos-table-order-info" }, `${cart.reduce((a, c) => a + c.quantity, 0)} items`)
                                        : null
                                )
                            );
                        })
                    )
            )
        );
    }

    plugins.register("screen", "pos_react.restaurant.floor", {
        label: "Restaurant Floor",
        component: RestaurantFloorScreen
    });

    plugins.register("dataRequirement", "pos_react.restaurant.bootstrap", {
        transform: (data) => ({
            ...data,
            restaurant: {
                enabled: data.restaurant?.enabled !== undefined ? data.restaurant.enabled : true,
                tables: (data.restaurant?.tables && data.restaurant.tables.length > 0) ? data.restaurant.tables : DEFAULT_TABLES
            }
        }),
    });
})();
