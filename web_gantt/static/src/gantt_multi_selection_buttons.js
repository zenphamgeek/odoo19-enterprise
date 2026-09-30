import { t, useProps } from "@insilos/owl";
import { MultiSelectionButtons, multiSelectionButtonsProps } from "@web/views/view_components/multi_selection_buttons";

export class GanttMultiSelectionButtons extends MultiSelectionButtons {
    static template = "web_gantt.GanttMultiSelectionButtons";
    props = useProps({
        ...multiSelectionButtonsProps,
        reactive: t.object(),
    });
}
