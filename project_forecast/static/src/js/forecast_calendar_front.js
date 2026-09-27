import PlanningView from '@planning/js/planning_calendar_front';
import { patch } from '@web/core/utils/patch';

patch(PlanningView.prototype, {
    // override popup of calendar
    eventFunction(calEvent) {
        super.eventFunction(...arguments);
        const $project = $("#project");
        if (calEvent.event.extendedProps.project) {
            $project.text(calEvent.event.extendedProps.project);
            $project.css("display", "");
            $project.prev().css("display", "");
        } else {
            $project.css("display", "none");
            $project.prev().css("display", "none");
        }
        const $task = $("#task");
        if (calEvent.event.extendedProps.task) {
            $task.text(calEvent.event.extendedProps.task);
            $task.prev().css("display", "");
            $task.css("display", "");
        } else {
            $task.css("display", "none");
            $task.prev().css("display", "none");
        }
    },
});
