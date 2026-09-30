import { onWillUpdateProps, proxy, useProps, t, signal } from "@insilos/owl";
import { useDateTimePicker } from "@web/core/datetime/datetime_picker_hook";
import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";
import { formatDate } from "@web/core/l10n/dates";
import { _t } from "@web/core/l10n/translation";
import { ViewScaleSelector, viewScaleSelectorProps } from "@web/views/view_components/view_scale_selector";
import { useGanttResponsivePopover } from "./gantt_helpers";

const { DateTime } = luxon;

export class GanttScaleSelector extends ViewScaleSelector {
    static template = "web_gantt.GanttScaleSelector";
    props = useProps({
        ...viewScaleSelectorProps,
        startDate: t.any(),
        stopDate: t.any(),
        selectCustomRange: t.function(),
    });

    startPickerRef = signal.ref();
    stopPickerRef = signal.ref();
    get "start-picker"() {
        return this.startPickerRef;
    }
    get "stop-picker"() {
        return this.stopPickerRef;
    }

    setup() {
        super.setup();
        this.pickerValues = proxy({
            startDate: this.props.startDate,
            stopDate: this.props.stopDate,
        });

        onWillUpdateProps((nextProps) => {
            this.pickerValues.startDate = nextProps.startDate;
            this.pickerValues.stopDate = nextProps.stopDate;
        });

        const getPickerProps = (key) => ({ type: "date", value: this.pickerValues[key] });
        this.startPicker = useDateTimePicker({
            target: this.startPickerRef,
            onApply: (date) => {
                this.pickerValues.startDate = date;
                if (this.pickerValues.stopDate < date) {
                    this.pickerValues.stopDate = date;
                } else if (date.plus({ year: 10, day: -1 }) < this.pickerValues.stopDate) {
                    this.pickerValues.stopDate = date.plus({ year: 10, day: -1 });
                }
            },
            get pickerProps() {
                return getPickerProps("startDate");
            },
            createPopover: (...args) => useGanttResponsivePopover(_t("Gantt start date"), ...args),
            ensureVisibility: () => false,
        });
        this.stopPicker = useDateTimePicker({
            target: this.stopPickerRef,
            onApply: (date) => {
                this.pickerValues.stopDate = date;
                if (date < this.pickerValues.startDate) {
                    this.pickerValues.startDate = date;
                } else if (this.pickerValues.startDate.plus({ year: 10, day: -1 }) < date) {
                    this.pickerValues.startDate = date.minus({ year: 10, day: -1 });
                }
            },
            get pickerProps() {
                return getPickerProps("stopDate");
            },
            createPopover: (...args) => useGanttResponsivePopover(_t("Gantt stop date"), ...args),
            ensureVisibility: () => false,
        });

        this.dropdownState = useDropdownState();
    }

    getFormattedDate(date) {
        return formatDate(date);
    }

    onApply() {
        const { startDate, stopDate } = this.pickerValues;
        this.props.selectCustomRange(startDate, stopDate);
        this.dropdownState.close();
    }
}
