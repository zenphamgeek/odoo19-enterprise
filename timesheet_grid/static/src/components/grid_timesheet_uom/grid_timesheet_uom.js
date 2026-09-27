import { Component, useProps } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

import { GridCell, standardGridCellProps } from "@web_grid/components/grid_cell";
import { FloatFactorGridCell } from "@web_grid/components/float_factor_grid_cell";
import { FloatToggleGridCell } from "@web_grid/components/float_toggle_grid_cell";
import { FloatTimeGridCell } from "@web_grid/components/float_time_grid_cell";

export class GridTimesheetUOM extends Component {
    static template = "timesheet_grid.GridTimesheetUOM";
    static props = standardGridCellProps;
    props = useProps(standardGridCellProps);

    static defaultProps = {
        readonly: true,
        editMode: false,
    };

    static components = { GridCell, FloatFactorGridCell, FloatToggleGridCell, FloatTimeGridCell };

    setup() {
        this.timesheetUOMService = useService("timesheet_uom");
    }

    get timesheetComponent() {
        return registry.category("grid_components").get(this.timesheetUOMService.timesheetWidget, {
            component: GridCell,
            formatter: this.timesheetUOMService.formatter,
        }).component;
    }
}
