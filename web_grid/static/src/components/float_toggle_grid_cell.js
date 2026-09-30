import { registry } from "@web/core/registry";
import { formatFloatFactor } from "@web/views/fields/formatters";
import { useGridCell, useMagnifierGlass } from "@web_grid/hooks/grid_cell_hook";
import { standardGridCellProps } from "./grid_cell";

import { Component, useLayoutEffect, proxy, signal } from "@insilos/owl";

function formatter(value, options = {}) {
    return formatFloatFactor(value, options);
}

export class FloatToggleGridCell extends Component {
    static props = {
        ...standardGridCellProps,
        factor: { type: Number, optional: true },
    };
    static template = "web_grid.FloatToggleGridCell";

    rootRef = signal.ref();
    buttonRef = signal.ref();

    get root() {
        return this.rootRef;
    }

    get toggleButton() {
        return this.buttonRef;
    }

    setup() {
        this.magnifierGlassHook = useMagnifierGlass();
        this.state = proxy({
            edit: this.props.editMode ?? false,
            invalid: false,
            cell: null,
        });
        useGridCell();

        useLayoutEffect(
            (buttonEl) => {
                if (buttonEl) {
                    buttonEl.focus();
                }
            },
            () => [this.buttonRef.el]
        );
    }

    get factor() {
        return this.props.factor || this.props.fieldInfo.options?.factor || 1;
    }

    get range() {
        return this.props.fieldInfo.options?.range || [0.0, 0.5, 1.0];
    }

    get value() {
        return (this.state.cell.value || 0) * this.factor;
    }

    get formattedValue() {
        return formatter(this.state.cell.value || 0, {
            digits: this.props.fieldInfo.attrs?.digits || 2,
            factor: this.factor,
        });
    }

    isEditable(props = this.props) {
        const readonly = props.readonly ?? true;
        return (
            !readonly && this.state.cell?.readonly === false && !this.state.cell.row.isSection
        );
    }

    onChange() {
        let currentIndex = this.range.indexOf(this.value);
        currentIndex++;
        if (currentIndex > this.range.length - 1) {
            currentIndex = 0;
        }
        this.update(this.range[currentIndex] / this.factor);
    }

    update(value) {
        this.state.cell.update(value);
    }

    onCellClick(ev) {
        if (this.isEditable() && !this.state.edit && !ev.target.closest(".o_grid_search_btn")) {
            this.onChange();
            this.props.onEdit(true);
        }
    }

    onKeyDown(ev) {
        this.props.onKeyDown(ev, this.state.cell);
    }
}

export const floatToggleGridCell = {
    component: FloatToggleGridCell,
    formatter,
};

registry.category("grid_components").add("float_toggle", floatToggleGridCell);
