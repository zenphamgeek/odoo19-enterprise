import { hasTouch, isIosApp, isMacOS } from "@web/core/browser/feature_detection";
import { useHotkey } from "@web/core/hotkeys/hotkey_hook";
import { rpc } from "@web/core/network/rpc";
import { user } from "@web/core/user";
import { useService } from "@web/core/utils/hooks";
import { ExpirationPanel } from "./expiration_panel";
import { useSortable } from "@web/core/utils/sortable_owl";

import {
    Component,
    useExternalListener,
    onMounted,
    onPatched,
    onWillUpdateProps,
    proxy,
    signal,
} from "@insilos/owl";

class FooterComponent extends Component {
    static template = "web_enterprise.HomeMenu.CommandPalette.Footer";
    static props = {
        //prop added by the command palette
        switchNamespace: { type: Function, optional: true },
    };

    setup() {
        this.controlKey = isMacOS() ? "COMMAND" : "CONTROL";
    }
}
/**
 * Home menu
 *
 * This component handles the display and navigation between the different
 * available applications and menus.
 * @extends Component
 */
export class HomeMenu extends Component {
    static template = "web_enterprise.HomeMenu";
    static components = { ExpirationPanel };
    input = signal.ref();
    root = signal.ref();
    static props = {
        apps: {
            type: Array,
            element: {
                type: Object,
                shape: {
                    actionID: Number,
                    href: String,
                    appID: Number,
                    id: Number,
                    label: String,
                    parents: String,
                    webIcon: {
                        type: [
                            Boolean,
                            String,
                            {
                                type: Object,
                                optional: 1,
                                shape: {
                                    iconClass: String,
                                    color: String,
                                    backgroundColor: String,
                                },
                            },
                        ],
                        optional: true,
                    },
                    webIconData: { type: String, optional: 1 },
                    xmlid: String,
                },
            },
        },
        reorderApps: { type: Function },
    };

    /**
     * @param {Object} props
     * @param {Object[]} props.apps application icons
     * @param {number} props.apps[].actionID
     * @param {number} props.apps[].id
     * @param {string} props.apps[].label
     * @param {string} props.apps[].parents
     * @param {(boolean|string|Object)} props.apps[].webIcon either:
     *      - boolean: false (no webIcon)
     *      - string: path to Insilos icon file
     *      - Object: customized icon (background, class and color)
     * @param {string} [props.apps[].webIconData]
     * @param {string} props.apps[].xmlid
     * @param {function} props.reorderApps
     */
    setup() {
        this.command = useService("command");
        this.menus = useService("menu");
        this.homeMenuService = useService("home_menu");
        this.subscription = useService("enterprise_subscription");
        this.ui = useService("ui");
        this.action = useService("action");
        this.state = proxy({
            focusedIndex: null,
            isIosApp: isIosApp(),
            empDashboard: {
                loading: true,
                expanded: true,
                activeTab: "overview",
                data: null,
                leavingForm: {
                    notice_date: "2026-10-15",
                    expected_last_day: "2026-11-15",
                    handover_assignee: "Nguyễn Hoài Ân (CTO)",
                    reason: "Chuyển giao công tác / Kế hoạch cá nhân",
                },
            },
        });
        this.pressTimer;

        if (!this.ui.isSmall) {
            this._registerHotkeys();
        }

        useSortable({
            enable: this._enableAppsSorting,
            // Params
            ref: this.root,
            elements: ".o_draggable",
            cursor: "move",
            delay: 500,
            tolerance: 10,
            // Hooks
            onWillStartDrag: (params) => this._sortStart(params),
            onDrop: (params) => this._sortAppDrop(params),
        });

        onWillUpdateProps(() => {
            // State is reset on each remount
            this.state.focusedIndex = null;
        });

        onMounted(() => {
            if (!hasTouch()) {
                this._focusInput();
            }
            this._loadEmployeeDashboard();
        });

        onPatched(() => {
            if (this.state.focusedIndex !== null && !this.ui.isSmall) {
                const selectedItem = document.querySelector(".o_home_menu .o_menuitem.o_focused");
                // When TAB is managed externally the class o_focused disappears.
                if (selectedItem) {
                    // Center window on the focused item
                    selectedItem.scrollIntoView({ block: "center" });
                }
            }
        });
    }

    //--------------------------------------------------------------------------
    // Getters
    //--------------------------------------------------------------------------

    /**
     * @returns {Object[]}
     */
    get displayedApps() {
        return this.props.apps;
    }

    /**
     * @returns {number}
     */
    get maxIconNumber() {
        const w = window.innerWidth;
        if (w < 576) {
            return 3;
        } else if (w < 768) {
            return 4;
        } else {
            return 6;
        }
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Object} menu
     * @returns {Promise}
     */
    _openMenu(menu) {
        return this.menus.selectMenu(menu);
    }

    /**
     * Update this.state.focusedIndex if not null.
     * @private
     * @param {string} cmd
     */
    _updateFocusedIndex(cmd) {
        const nbrApps = this.displayedApps.length;
        const lastIndex = nbrApps - 1;
        const focusedIndex = this.state.focusedIndex;
        if (lastIndex < 0) {
            return;
        }
        if (focusedIndex === null) {
            this.state.focusedIndex = 0;
            return;
        }
        const lineNumber = Math.ceil(nbrApps / this.maxIconNumber);
        const currentLine = Math.ceil((focusedIndex + 1) / this.maxIconNumber);
        let newIndex;
        switch (cmd) {
            case "previousElem":
                newIndex = focusedIndex - 1;
                break;
            case "nextElem":
                newIndex = focusedIndex + 1;
                break;
            case "previousColumn":
                if (focusedIndex % this.maxIconNumber) {
                    // app is not the first one on its line
                    newIndex = focusedIndex - 1;
                } else {
                    newIndex =
                        focusedIndex + Math.min(lastIndex - focusedIndex, this.maxIconNumber - 1);
                }
                break;
            case "nextColumn":
                if (focusedIndex === lastIndex || (focusedIndex + 1) % this.maxIconNumber === 0) {
                    // app is the last one on its line
                    newIndex = (currentLine - 1) * this.maxIconNumber;
                } else {
                    newIndex = focusedIndex + 1;
                }
                break;
            case "previousLine":
                if (currentLine === 1) {
                    newIndex = focusedIndex + (lineNumber - 1) * this.maxIconNumber;
                    if (newIndex > lastIndex) {
                        newIndex = lastIndex;
                    }
                } else {
                    // we go to the previous line on same column
                    newIndex = focusedIndex - this.maxIconNumber;
                }
                break;
            case "nextLine":
                if (currentLine === lineNumber) {
                    newIndex = focusedIndex % this.maxIconNumber;
                } else {
                    // we go to the next line on the closest column
                    newIndex =
                        focusedIndex + Math.min(this.maxIconNumber, lastIndex - focusedIndex);
                }
                break;
        }
        // if newIndex is out of bounds -> normalize it
        if (newIndex < 0) {
            newIndex = lastIndex;
        } else if (newIndex > lastIndex) {
            newIndex = 0;
        }
        this.state.focusedIndex = newIndex;
    }

    _focusInput() {
        const inputEl = this.input();
        if (!this.ui.isSmall && inputEl) {
            inputEl.focus({ preventScroll: true });
        }
    }

    _enableAppsSorting() {
        return true;
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @param {Object} params
     * @param {HTMLElement} params.element
     * @param {HTMLElement} params.previous
     */
    _sortAppDrop({ element, previous }) {
        const order = this.props.apps.map((app) => app.xmlid);
        const elementId = element.children[0].dataset.menuXmlid;
        const elementIndex = order.indexOf(elementId);
        // first remove dragged element
        order.splice(elementIndex, 1);
        if (previous) {
            const prevIndex = order.indexOf(previous.children[0].dataset.menuXmlid);
            // insert dragged element after previous element
            order.splice(prevIndex + 1, 0, elementId);
        } else {
            // insert dragged element at beginning if no previous element
            order.splice(0, 0, elementId);
        }
        // apply new order
        this.props.reorderApps(order);
        user.setUserSettings("homemenu_config", JSON.stringify(order));
    }

    /**
     * @param {Object} params
     * @param {HTMLElement} params.element
     */
    _sortStart({ element, addClass }) {
        addClass(element.children[0], "o_dragged_app");
    }

    /**
     * @private
     * @param {Object} app
     */
    _onAppClick(app) {
        this._openMenu(app);
    }

    /**
     * @private
     */
    _registerHotkeys() {
        const hotkeys = [
            ["ArrowDown", () => this._updateFocusedIndex("nextLine")],
            ["ArrowRight", () => this._updateFocusedIndex("nextColumn")],
            ["ArrowUp", () => this._updateFocusedIndex("previousLine")],
            ["ArrowLeft", () => this._updateFocusedIndex("previousColumn")],
            ["Tab", () => this._updateFocusedIndex("nextElem")],
            ["shift+Tab", () => this._updateFocusedIndex("previousElem")],
            [
                "Enter",
                () => {
                    const menu = this.displayedApps[this.state.focusedIndex];
                    if (menu) {
                        this._openMenu(menu);
                    }
                },
            ],
            ["Escape", () => this.homeMenuService.toggle(false)],
        ];
        hotkeys.forEach((hotkey) => {
            useHotkey(...hotkey, {
                allowRepeat: true,
            });
        });
        useExternalListener(window, "keydown", this._onKeydownFocusInput);
    }

    _onKeydownFocusInput() {
        const inputEl = this.input();
        if (
            document.activeElement !== inputEl &&
            this.ui.activeElement === document &&
            !["TEXTAREA", "INPUT", "SELECT"].includes(document.activeElement.tagName)
        ) {
            this._focusInput();
        }
    }

    _onInputSearch() {
        const onClose = () => {
            this._focusInput();
            const inputEl = this.input();
            if (inputEl) {
                inputEl.value = "";
            }
        };
        const inputVal = (this.input()?.value || "").trim();
        const searchValue = this.compositionStart ? "/" : `/${inputVal}`;
        this.compositionStart = false;
        this.command.openMainPalette({ searchValue, FooterComponent }, onClose);
    }

    _onInputBlur() {
        if (hasTouch()) {
            return;
        }
        // if we blur search input to focus on body (eg. click on any
        // non-interactive element) restore focus to avoid IME input issue
        setTimeout(() => {
            if (document.activeElement === document.body && this.ui.activeElement === document) {
                this._focusInput();
            }
        }, 0);
    }

    _onCompositionStart() {
        this.compositionStart = true;
    }

    //--------------------------------------------------------------------------
    // Employee Self-Service, Payroll, Onboarding & Leaving Hub
    //--------------------------------------------------------------------------

    formatVnd(amount) {
        return new Intl.NumberFormat("vi-VN").format(Math.round(Number(amount) || 0)) + " ₫";
    }

    getInitials(name) {
        if (!name) {
            return "NV";
        }
        const parts = String(name).trim().split(/\s+/);
        if (parts.length === 1) {
            return parts[0].slice(0, 2).toUpperCase();
        }
        return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
    }

    async _loadEmployeeDashboard(employeeId = null) {
        try {
            this.state.empDashboard.loading = true;
            const res = await rpc("/insilos/employee_dashboard/data", {
                employee_id: employeeId,
            });
            if (res && res.current_employee) {
                this.state.empDashboard.data = res;
                if (res.leaving) {
                    this.state.empDashboard.leavingForm.notice_date =
                        res.leaving.notice_date || "2026-10-15";
                    this.state.empDashboard.leavingForm.expected_last_day =
                        res.leaving.expected_last_day || "2026-11-15";
                    this.state.empDashboard.leavingForm.handover_assignee =
                        res.leaving.handover_assignee || "Nguyễn Hoài Ân (CTO)";
                    this.state.empDashboard.leavingForm.reason =
                        res.leaving.reason || "Chuyển giao công tác / Kế hoạch cá nhân";
                }
            }
        } catch {
            // Non-blocking fallback if offline
        } finally {
            this.state.empDashboard.loading = false;
        }
    }

    selectDashboardTab(tab) {
        this.state.empDashboard.activeTab = tab;
        this.state.empDashboard.expanded = true;
    }

    toggleDashboardExpanded() {
        this.state.empDashboard.expanded = !this.state.empDashboard.expanded;
    }

    async onChangeDashboardEmployee(ev) {
        const empId = parseInt(ev.target.value, 10);
        if (empId) {
            await this._loadEmployeeDashboard(empId);
        }
    }

    async onToggleLifecycleStep(workflow, stepId, currentDone) {
        const empId = this.state.empDashboard.data?.current_employee?.id;
        if (!empId) {
            return;
        }
        try {
            const res = await rpc("/insilos/employee_dashboard/toggle_step", {
                employee_id: empId,
                workflow,
                step_id: stepId,
                done: !currentDone,
            });
            if (res && res.current_employee) {
                this.state.empDashboard.data = res;
            }
        } catch {
            // Fail-soft
        }
    }

    async onSubmitLeavingRequest() {
        const empId = this.state.empDashboard.data?.current_employee?.id;
        if (!empId) {
            return;
        }
        const form = this.state.empDashboard.leavingForm;
        try {
            const res = await rpc("/insilos/employee_dashboard/toggle_step", {
                employee_id: empId,
                action: "initiate_leaving",
                notice_date: form.notice_date,
                expected_last_day: form.expected_last_day,
                handover_assignee: form.handover_assignee,
                reason: form.reason,
            });
            if (res && res.current_employee) {
                this.state.empDashboard.data = res;
            }
        } catch {
            // Fail-soft
        }
    }

    openHrApp() {
        const hrApp = this.props.apps.find(
            (a) => a.xmlid && (a.xmlid.startsWith("hr.") || a.xmlid === "hr.menu_hr_root")
        );
        if (hrApp) {
            return this._openMenu(hrApp);
        }
        const empId = this.state.empDashboard.data?.current_employee?.id;
        return this.action.doAction({
            type: "ir.actions.act_window",
            name: "Hồ sơ Nhân sự DGM",
            res_model: "hr.employee",
            res_id: empId || false,
            views: [
                [false, "kanban"],
                [false, "list"],
                [false, "form"],
            ],
            target: "current",
        });
    }

    openPayrollApp() {
        const payrollApp = this.props.apps.find(
            (a) => a.xmlid && a.xmlid.startsWith("hr_payroll")
        );
        if (payrollApp) {
            return this._openMenu(payrollApp);
        }
        return this.action.doAction({
            type: "ir.actions.act_window",
            name: "Bảng lương & Phiếu lương DGM",
            res_model: "hr.payslip",
            views: [
                [false, "list"],
                [false, "form"],
            ],
            target: "current",
        });
    }

    openDocumentsApp() {
        const docsApp = this.props.apps.find(
            (a) => a.xmlid && a.xmlid.startsWith("documents")
        );
        if (docsApp) {
            return this._openMenu(docsApp);
        }
        return this.action.doAction({
            type: "ir.actions.act_window",
            name: "Kho Tài liệu Số DGM",
            res_model: "documents.document",
            views: [
                [false, "kanban"],
                [false, "list"],
            ],
            target: "current",
        });
    }
}

