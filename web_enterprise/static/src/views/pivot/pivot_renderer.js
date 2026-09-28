import { patch } from "@web/core/utils/patch";
import { PivotRenderer } from "@web/views/pivot/pivot_renderer";

import { useEffect } from "@insilos/owl";

patch(PivotRenderer.prototype, {
    setup() {
        super.setup();
        if (this.uiService?.isSmall || this.env?.isSmall) {
            useEffect(() => {
                const tableEl = (typeof this.tableRef === "function" ? this.tableRef() : this.tableRef?.el) || this.root?.el;
                if (tableEl) {
                    const tooltipElems = tableEl.querySelectorAll("*[data-tooltip]");
                    for (const el of tooltipElems) {
                        el.removeAttribute("data-tooltip");
                        el.removeAttribute("data-tooltip-position");
                    }
                }
            });
        }
    },

    getPadding(cell) {
        if (this.uiService?.isSmall || this.env?.isSmall) {
            return 5 + cell.indent * 5;
        }
        return super.getPadding(...arguments);
    },
});
