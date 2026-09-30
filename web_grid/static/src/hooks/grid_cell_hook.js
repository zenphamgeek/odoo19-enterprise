import { useComponent, useLayoutEffect } from "@insilos/owl";

export function useMagnifierGlass() {
    const component = useComponent();
    return {
        onMagnifierGlassClick() {
            const { context, domain, title } = component.state.cell;
            component.props.openRecords(title, domain.toList(), context);
        },
    };
}

export function useGridCell() {
    const component = useComponent();
    useLayoutEffect(
        /** @param {HTMLElement | null} cellEl */
        (cellEl) => {
            if (!cellEl) {
                component.state.cell = null;
                return;
            }
            component.state.cell = component.props.getCell(
                cellEl.dataset.row,
                cellEl.dataset.column
            );
            if (component.rootRef?.el) {
                Object.assign(component.rootRef.el.style, {
                    "grid-row": cellEl.style["grid-row"],
                    "grid-column": cellEl.style["grid-column"],
                    "z-index": 1,
                });
                component.rootRef.el.dataset.gridRow = cellEl.dataset.gridRow;
                component.rootRef.el.dataset.gridColumn = cellEl.dataset.gridColumn;
                component.rootRef.el.classList.toggle(
                    "o_field_cursor_disabled",
                    !component.state.cell.row.isSection && !component.isEditable()
                );
                component.rootRef.el.classList.toggle("fw-bold", Boolean(component.state.cell.row.isSection));
            }
            const readonlyEl = cellEl.querySelector(".o_grid_cell_readonly");
            if (readonlyEl) {
                readonlyEl.classList.add("d-none");
                return () => {
                    readonlyEl.classList.remove("d-none");
                };
            }
        },
        () => [component.props.reactive.cell]
    );
}
