import { Component } from "@odoo/owl";
import { FilterValue } from "@spreadsheet/global_filters/components/filter_value/filter_value";

export class FilterValuesList extends Component {
    static template = "spreadsheet_edition.FilterValuesList";
    static components = { FilterValue };
    static props = {
        model: Object,
        openFiltersEditor: { type: Function, optional: true },
        close: { type: Function, optional: true },
    };

    get filters() {
        return this.props.model.getters.getGlobalFilters();
    }

    setGlobalFilterValue(filterId, value) {
        this.props.model.dispatch("SET_GLOBAL_FILTER_VALUE", {
            id: filterId,
            value,
        });
    }
}
