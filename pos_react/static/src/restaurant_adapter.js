(() => {
    "use strict";

    const { createElement: h } = React;
    const plugins = window.posReactPlugins;
    const restaurant = JSON.parse(document.getElementById("pos-react-data").textContent).restaurant;
    if (!restaurant?.enabled) return;

    function RestaurantScreen({ restaurant = {}, restaurantContext = {}, setRestaurantContext, setScreen }) {
        const tables = restaurant.tables || [];
        return h("main", null,
            h("h1", null, "Restaurant"),
            h("label", null, "Table", h("select", {
                value: restaurantContext.tableId || "", disabled: restaurantContext.locked,
                "aria-label": "Restaurant table",
                onChange: (event) => setRestaurantContext({ tableId: Number(event.target.value) || false }),
            }, h("option", { value: "" }, "No table"), tables.map((table) => h("option", { key: table.id, value: table.id }, `Table ${table.table_number}`)))),
            h("label", null, "Guests", h("input", {
                type: "number", min: 1, value: restaurantContext.customerCount || "", disabled: restaurantContext.locked, "aria-label": "Guest count",
                onChange: (event) => setRestaurantContext({ customerCount: Number(event.target.value) || false }),
            })),
            h("button", { onClick: () => setScreen(null) }, "Back")
        );
    }

    plugins.register("screen", "pos_react.restaurant.floor", { label: "Restaurant", component: RestaurantScreen });
    plugins.register("dataRequirement", "pos_react.restaurant.bootstrap", {
        transform: (data) => ({ ...data, restaurant: { tables: data.restaurant?.tables || [] } }),
    });
})();
