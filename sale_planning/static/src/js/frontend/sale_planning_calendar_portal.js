import PlanningView from '@planning/js/planning_calendar_front';
import { patch } from '@web/core/utils/patch';

patch(PlanningView.prototype, {
    // override popup of calendar
    eventFunction(calEvent) {
        super.eventFunction(...arguments);
        const $saleLine = $("#sale_line");
        if (calEvent.event.extendedProps.sale_line) {
            $saleLine.text(calEvent.event.extendedProps.sale_line);
            $saleLine.css("display", "");
            $saleLine.prev().css("display", "");
        } else {
            $saleLine.css("display", "none");
            $saleLine.prev().css("display", "none");
        }
    },
});

