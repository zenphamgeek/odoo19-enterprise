/* eslint-disable no-undef */

import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { loadBundle } from "@web/core/assets";
const { DateTime } = luxon;

export class PlanningView extends Interaction {
    static selector = '#calendar_employee';

    async start() {
        if ($('.message_slug').attr('value')) {
            $("#PlanningToast").toast('show');
        }
        if ($('.no_data').attr('value')) {
            return;
        }
        await loadBundle("web.fullcalendar_lib");
        this.calendarElement = this.el.querySelector(".o_calendar_widget");
        const employeeSlotsFcData = JSON.parse($('.employee_slots_fullcalendar_data').attr('value') || '[]');
        const locale = $('.locale').attr('value');
        $('[data-bs-toggle="popover"]').popover();
        $('body').on('click', function (e) {
            var parentElsClassList = $(e.target).parents().map(function() {
                return [...this.classList];
            });
            if (!['assignee-cell', 'contact-assignee-popover'].some(el => [...parentElsClassList].includes(el))) {
                $('[data-bs-toggle="popover"]').popover('hide');
            }
        });
        $('[data-bs-toggle="popover"]').on('click', function (e) {
            $('[data-bs-toggle="popover"]').not(this).popover('hide');
        });
        const defaultStartValue = $('.default_start').attr('value');
        const defaultStart = defaultStartValue ? DateTime.fromFormat(defaultStartValue, "yyyy-MM-dd").toJSDate() : new Date();
        const defaultView = $('.default_view').attr('value') || 'dayGridMonth';
        const minTime = $('.mintime').attr('value');
        const maxTime = $('.maxtime').attr('value');
        let calendarHeaders = {
            left: 'dayGridMonth,timeGridWeek,listMonth',
            center: 'title',
            right: 'today,prev,next',
        };
        if (employeeSlotsFcData.length === 0) {
            calendarHeaders = {
                left: false,
                center: 'title',
                right: false,
            };
        }
        const titleFormat = { month: "long", year: "numeric" };
        let noEventsContent = _t("You don't have any shifts planned yet.");
        const openSlotsIds = $('.open_slots_ids').attr('value');
        if (openSlotsIds) {
            noEventsContent = _t("You don't have any shifts planned yet. You can assign yourself some of the available open shifts.");
        }
        this.calendar = new FullCalendar.Calendar(this.calendarElement || document.querySelector("#calendar_employee .o_calendar_widget"), {
            locale: locale,
            initialView: defaultView,
            navLinks: true,
            dayMaxEventRows: 3,
            titleFormat: titleFormat,
            initialDate: defaultStart,
            displayEventEnd: true,
            height: 'auto',
            eventDidMount: this.onEventDidMount.bind(this),
            eventTextColor: 'white',
            eventOverlap: true,
            eventTimeFormat: {
                hour: 'numeric',
                minute: '2-digit',
                meridiem: 'long',
                omitZeroMinute: true,
            },
            slotMinTime: minTime,
            slotMaxTime: maxTime,
            headerToolbar: calendarHeaders,
            events: employeeSlotsFcData,
            eventClick: this.eventFunction.bind(this),
            buttonText: {
                today: _t("Today"),
                dayGridMonth: _t("Month"),
                timeGridWeek: _t("Week"),
                listMonth: _t("List"),
            },
            noEventsContent: noEventsContent,
        });
        this.calendar.setOption('locale', locale);
        this.calendar.render();
    }

    onEventDidMount(calRender) {
        const calendarElement = calRender.el;
        const timeEvent = calendarElement.querySelector('.fc-event-time');
        if (calRender.view.type !== 'listMonth') {
            calendarElement.classList.add('px-2', 'py-1');
        }
        if (calRender.view.type === 'dayGridMonth') {
            const timeRow = document.createElement('div');
            timeRow.classList.add('d-flex', 'align-items-center', 'w-100', 'overflow-hidden');
            const titleEvent = calendarElement.querySelector('.fc-event-title');
            const colorElement = calendarElement.querySelector('.fc-daygrid-event-dot');
            timeEvent?.classList.add('w-100', 'text-truncate');
            if (colorElement && timeEvent) {
                timeRow.append(colorElement, timeEvent);
            }
            titleEvent?.classList.add('w-100', 'text-truncate', 'ms-4');
            calendarElement.classList.add('flex-column');
            if (titleEvent) {
                calendarElement.append(timeRow, titleEvent);
            }
        }
        calendarElement.classList.add('cursor-pointer');
        if (calendarElement.childNodes[0]?.classList) {
            calendarElement.childNodes[0].classList.add('fw-bold');
        }
        const timeElement = document.createElement('span');
        timeElement.classList.add('ps-1');
        const allocatedHours = calRender.event.extendedProps.alloc_hours;
        const hoursSpan = document.createElement('span');
        hoursSpan.textContent = `(${allocatedHours})`;
        timeElement.appendChild(hoursSpan);
        const allocatedPercent = calRender.event.extendedProps.alloc_perc;
        if (allocatedPercent != 100) {
            const percentSpan = document.createElement('span');
            percentSpan.classList.add('ps-1');
            percentSpan.textContent = `(${allocatedPercent}%)`;
            timeElement.appendChild(percentSpan);
        }
        timeEvent?.appendChild(timeElement);

        if (calRender.event.extendedProps.request_to_switch && !calRender.event.extendedProps.allow_self_unassign) {
            calendarElement.style.opacity = '0.5';
            const backgroundColor = calendarElement.style.backgroundColor;
            calendarElement.style.borderColor = backgroundColor;
            calendarElement.style.borderWidth = '5px';
            calendarElement.style.background = 'repeating-linear-gradient(40deg, #A0A0A0, #A0A0A0 5px, '+backgroundColor+' 5px, '+backgroundColor + ' 10px)';
        }
    }

    formatDateAsBackend(date) {
        return DateTime.fromJSDate(date).toLocaleString({
            ...DateTime.DATE_SHORT,
            ...DateTime.TIME_24_SIMPLE,
            weekday: "short",
        });
    }

    eventFunction(calEvent) {
        const planningToken = $('.planning_token').attr('value');
        const employeeToken = $('.employee_token').attr('value');
        let displayFooter = false;
        $(".modal-title").text(calEvent.event.title);
        $(".modal-header").css("background-color", calEvent.event.backgroundColor);
        if (calEvent.event.extendedProps.request_to_switch && !calEvent.event.extendedProps.allow_self_unassign) {
            const switchWarning = document.getElementById("switch-warning");
            if (switchWarning) switchWarning.style.display = "block";
            $(".warning-text").text("You requested to switch this shift. Other employees can now assign themselves to it.");
        } else {
            const switchWarning = document.getElementById("switch-warning");
            if (switchWarning) switchWarning.style.display = "none";
        }
        $('.o_start_date').text(this.formatDateAsBackend(calEvent.event.start));
        let textValue = this.formatDateAsBackend(calEvent.event.end);
        if (calEvent.event.extendedProps.alloc_hours) {
            textValue += ` (${calEvent.event.extendedProps.alloc_hours})`;
        }
        if (parseFloat(calEvent.event.extendedProps.alloc_perc) < 100) {
            textValue += ` (${calEvent.event.extendedProps.alloc_perc}%)`;
        }
        $('.o_end_date').text(textValue);
        if (calEvent.event.extendedProps.role) {
            $("#role").prev().css("display", "");
            $("#role").text(calEvent.event.extendedProps.role);
            $("#role").css("display", "");
        } else {
            $("#role").prev().css("display", "none");
            $("#role").css("display", "none");
        }
        if (calEvent.event.extendedProps.note) {
            $("#note").prev().css("display", "");
            $("#note").text(calEvent.event.extendedProps.note);
            $("#note").css("display", "");
        } else {
            $("#note").prev().css("display", "none");
            $("#note").css("display", "none");
        }
        $("#allow_self_unassign").text(calEvent.event.extendedProps.allow_self_unassign);
        const dismissShift = document.getElementById("dismiss_shift");
        if (
            calEvent.event.extendedProps.allow_self_unassign
            && !calEvent.event.extendedProps.is_unassign_deadline_passed
            && !calEvent.event.extendedProps.is_open_shift
        ) {
            if (dismissShift) dismissShift.style.display = "block";
            displayFooter = true;
        } else if (dismissShift) {
            dismissShift.style.display = "none";
        }
        const switchShift = document.getElementById("switch_shift");
        if (
            !calEvent.event.extendedProps.request_to_switch
            && !calEvent.event.extendedProps.is_past
            && !calEvent.event.extendedProps.allow_self_unassign
            && !calEvent.event.extendedProps.is_open_shift
        ) {
            if (switchShift) switchShift.style.display = "block";
            displayFooter = true;
        } else if (switchShift) {
            switchShift.style.display = "none";
        }
        const cancelSwitch = document.getElementById("cancel_switch");
        if (
            calEvent.event.extendedProps.request_to_switch
            && !calEvent.event.extendedProps.allow_self_unassign
            && !calEvent.event.extendedProps.is_open_shift
        ) {
            if (cancelSwitch) cancelSwitch.style.display = "block";
            displayFooter = true;
        } else if (cancelSwitch) {
            cancelSwitch.style.display = "none";
        }
        const takeOpenSwitch = document.getElementById("take_open_switch");
        if (calEvent.event.extendedProps.is_open_shift) {
            if (takeOpenSwitch) takeOpenSwitch.style.display = "block";
            displayFooter = true;
        } else if (takeOpenSwitch) {
            takeOpenSwitch.style.display = "none";
        }
        $("#modal_action_dismiss_shift").attr("action", "/planning/" + planningToken + "/" + employeeToken + "/unassign/" + calEvent.event.extendedProps.slot_id);
        $("#modal_action_switch_shift").attr("action", "/planning/" + planningToken + "/" + employeeToken + "/switch/" + calEvent.event.extendedProps.slot_id);
        $("#modal_action_cancel_switch").attr("action", "/planning/" + planningToken + "/" + employeeToken + "/cancel_switch/" + calEvent.event.extendedProps.slot_id);
        $("#modal_action_take_open_switch").attr("action", "/planning/" + planningToken + "/" + employeeToken + "/take_open_shift/" + calEvent.event.extendedProps.slot_id);
        $("#fc-slot-onclick-modal").modal("show");
        const modalFooter = document.getElementsByClassName("modal-footer")[0];
        if (modalFooter) {
            modalFooter.style.display = displayFooter ? "block" : "none";
        }
    }
}

registry.category("public.interactions").add("planning.planning_calendar_front", PlanningView);
export default PlanningView;
