import { Component } from "@insilos/owl";
import { registry } from "@web/core/registry";

import { GridCell } from "../grid_cell";
import { GridRow } from "../grid_row/grid_row";

const gridComponentRegistry = registry.category("grid_components");

export class GridComponent extends Component {
    static props = ["name", "type", "isMeasure?", "component?", "*"];
    static template = "web_grid.GridComponent"

    get gridComponent() {
        let comp = GridRow;
        if (this.props.component) {
            comp = this.props.component;
        } else if (gridComponentRegistry.contains(this.props.type)) {
            comp = gridComponentRegistry.get(this.props.type).component;
        } else if (this.props.isMeasure) {
            console.warn(`Missing widget: ${this.props.type} for grid component`);
            comp = GridCell;
        }
        console.log("DEBUG GRID COMPONENT:", this.props.type, comp?.name, comp?.template);
        return comp;
    }

    get gridComponentProps() {
        const gridComponentProps = Object.fromEntries(
            Object.entries(this.props).filter(
                ([key,]) => key in this.gridComponent.props
            )
        );
        gridComponentProps.classNames = `o_grid_component o_grid_component_${this.props.type} ${gridComponentProps.classNames || ""}`;
        return gridComponentProps;
    }
}
