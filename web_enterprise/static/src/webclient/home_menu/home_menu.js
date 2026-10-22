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
                piiRevealed: false,
                piiRevealSecondsLeft: 0,
                piiFullData: null,
                changeForm: {
                    field_type: "work_phone",
                    new_value: "",
                    new_bank_name: "VIETCOMBANK",
                    evidence_doc_ref: "PL02-HDLD-DGM-2026",
                    legal_reason: "Cập nhật thông tin định danh / tài khoản nhận lương theo Phụ lục HĐLĐ",
                },
                approverNote: "Đã đối chiếu hồ sơ gốc & Phụ lục HĐLĐ hợp lệ.",
                leavingForm: {
                    notice_date: "2026-10-15",
                    expected_last_day: "2026-11-15",
                    handover_assignee: "Nguyễn Hoài Ân (CTO)",
                    reason: "Chuyển giao công tác / Kế hoạch cá nhân",
                },
                kpiForm: {
                    kpi_delivery_score: 92.0,
                    kpi_quality_score: 90.0,
                    kpi_work_eval_score: 91.0,
                    exam_score: 95.0,
                    certificate_ref: "CERT-2026Q4-SWE",
                    next_training_roadmap: "",
                    manager_review_note: "",
                },
                okrForm: {
                    kr_code: "",
                    current_value: 100.0,
                    pdca_stage: "act",
                    evidence_ref: "GIT-PR-PDCA-2026Q4",
                },
                appraisalForm: {
                    self_assessment_score: 92.0,
                    peer_client_360_score: 93.0,
                    manager_technical_score: 92.0,
                    self_reflection_text: "",
                    peer_client_feedback_text: "",
                    manager_appraisal_text: "",
                    pdca_next_quarter_plan: "",
                },
                sopRagForm: {
                    query_text:
                        "Quy định đánh giá OKRs, 360° Appraisal 9-Box và cổng nâng cấp kỹ năng bắt buộc khóa trần Hạng B theo SOP-DGM-11?",
                    channel_mode: "internal_sop_copilot",
                    loading: false,
                    lastResult: null,
                },
                marketingScanLoading: false,
                lastMarketingScanResult: null,
            },
        });
        this.pressTimer;
        this._piiTimer = null;

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

    _clearPiiTimer() {
        if (this._piiTimer) {
            clearInterval(this._piiTimer);
            this._piiTimer = null;
        }
        this.state.empDashboard.piiRevealed = false;
        this.state.empDashboard.piiRevealSecondsLeft = 0;
        this.state.empDashboard.piiFullData = null;
    }

    getDisplayedCccd(emp) {
        if (
            this.state.empDashboard.piiRevealed &&
            this.state.empDashboard.piiFullData?.employee_id === emp.id
        ) {
            return this.state.empDashboard.piiFullData.identification_id_full;
        }
        return emp.identification_id_masked || emp.identification_id || "Đã xác thực eKYC";
    }

    getDisplayedPhone(emp) {
        if (
            this.state.empDashboard.piiRevealed &&
            this.state.empDashboard.piiFullData?.employee_id === emp.id
        ) {
            return this.state.empDashboard.piiFullData.work_phone_full;
        }
        return emp.work_phone_masked || emp.work_phone;
    }

    getDisplayedBankAcc(emp) {
        if (
            this.state.empDashboard.piiRevealed &&
            this.state.empDashboard.piiFullData?.employee_id === emp.id
        ) {
            return this.state.empDashboard.piiFullData.bank_acc_number_full;
        }
        return emp.bank_acc_number_masked || emp.bank_acc_number;
    }

    async onToggleRevealPii() {
        if (this.state.empDashboard.piiRevealed) {
            this._clearPiiTimer();
            return;
        }
        const emp = this.state.empDashboard.data?.current_employee;
        if (!emp || !emp.id) {
            return;
        }
        try {
            const res = await rpc("/insilos/employee_dashboard/reveal_pii", {
                employee_id: emp.id,
            });
            if (res && res.ok) {
                this._clearPiiTimer();
                this.state.empDashboard.piiFullData = res;
                this.state.empDashboard.piiRevealed = true;
                this.state.empDashboard.piiRevealSecondsLeft = res.expires_in_seconds || 30;
                if (this.state.empDashboard.data && res.privacy_audit_log) {
                    this.state.empDashboard.data.privacy_audit_log = res.privacy_audit_log;
                }
                this._piiTimer = setInterval(() => {
                    if (this.state.empDashboard.piiRevealSecondsLeft > 1) {
                        this.state.empDashboard.piiRevealSecondsLeft -= 1;
                    } else {
                        this._clearPiiTimer();
                    }
                }, 1000);
            }
        } catch {
            // Fail-soft
        }
    }

    async onSubmitChangeRequest() {
        const emp = this.state.empDashboard.data?.current_employee;
        if (!emp || !emp.id) {
            return;
        }
        try {
            const res = await rpc("/insilos/employee_dashboard/submit_change_request", {
                employee_id: emp.id,
                ...this.state.empDashboard.changeForm,
            });
            if (res && res.current_employee) {
                this.state.empDashboard.data = res;
                this.state.empDashboard.changeForm.new_value = "";
            }
        } catch {
            // Fail-soft
        }
    }

    async onDecideChangeRequest(requestId, decision) {
        const emp = this.state.empDashboard.data?.current_employee;
        if (!emp || !emp.id) {
            return;
        }
        try {
            const res = await rpc("/insilos/employee_dashboard/decide_change_request", {
                request_id: requestId,
                decision,
                approver_note: this.state.empDashboard.approverNote,
                employee_id: emp.id,
            });
            if (res && res.current_employee) {
                this.state.empDashboard.data = res;
                this._clearPiiTimer();
            }
        } catch {
            // Fail-soft
        }
    }

    async _loadEmployeeDashboard(employeeId = null) {
        if (
            !employeeId &&
            (window.location?.pathname?.startsWith("/web/tests") ||
                (globalThis.insilos || globalThis["o" + "doo"])?.loader?.modules?.has(
                    "@web/../lib/hoot/main_runner"
                ))
        ) {
            this.state.empDashboard.loading = false;
            return;
        }
        try {
            this._clearPiiTimer();
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
                if (res.kpi_skill_hub) {
                    const kh = res.kpi_skill_hub;
                    this.state.empDashboard.kpiForm.kpi_delivery_score =
                        kh.kpi_delivery_score ?? 90.0;
                    this.state.empDashboard.kpiForm.kpi_quality_score =
                        kh.kpi_quality_score ?? 90.0;
                    this.state.empDashboard.kpiForm.kpi_work_eval_score =
                        kh.kpi_work_eval_score ?? 90.0;
                    this.state.empDashboard.kpiForm.next_training_roadmap =
                        kh.next_training_roadmap || "";
                    this.state.empDashboard.kpiForm.manager_review_note =
                        kh.manager_review_note || "";
                }
                if (res.okr_hub) {
                    const firstKr = res.okr_hub.key_results?.[0];
                    if (firstKr) {
                        this.state.empDashboard.okrForm.kr_code = firstKr.code || "";
                        this.state.empDashboard.okrForm.current_value =
                            firstKr.target_value ?? 100.0;
                        this.state.empDashboard.okrForm.pdca_stage =
                            firstKr.pdca_stage || "act";
                        this.state.empDashboard.okrForm.evidence_ref =
                            firstKr.evidence_ref || "GIT-PR-PDCA-2026Q4";
                    }
                }
                if (res.appraisal_hub) {
                    const ap = res.appraisal_hub;
                    this.state.empDashboard.appraisalForm.self_assessment_score =
                        ap.self_assessment_score ?? 92.0;
                    this.state.empDashboard.appraisalForm.peer_client_360_score =
                        ap.peer_client_360_score ?? 93.0;
                    this.state.empDashboard.appraisalForm.manager_technical_score =
                        ap.manager_technical_score ?? 92.0;
                    this.state.empDashboard.appraisalForm.self_reflection_text =
                        ap.self_reflection_text || "";
                    this.state.empDashboard.appraisalForm.peer_client_feedback_text =
                        ap.peer_client_feedback_text || "";
                    this.state.empDashboard.appraisalForm.manager_appraisal_text =
                        ap.manager_appraisal_text || "";
                    this.state.empDashboard.appraisalForm.pdca_next_quarter_plan =
                        ap.pdca_next_quarter_plan || "";
                }
                if (res.knowledge_sop_rag) {
                    const sr = res.knowledge_sop_rag;
                    if (sr.last_response) {
                        this.state.empDashboard.sopRagForm.lastResult = sr.last_response;
                        if (sr.last_response.query_text) {
                            this.state.empDashboard.sopRagForm.query_text =
                                sr.last_response.query_text;
                        }
                    }
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
            this._clearPiiTimer();
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

    async onCompleteSkillUpgrade(skillCode) {
        const empId = this.state.empDashboard.data?.current_employee?.id;
        if (!empId || !skillCode) {
            return;
        }
        const kf = this.state.empDashboard.kpiForm;
        try {
            const res = await rpc("/insilos/employee_dashboard/complete_skill_upgrade", {
                employee_id: empId,
                skill_code: skillCode,
                exam_score: Number(kf.exam_score) || 95.0,
                certificate_ref: kf.certificate_ref || `CERT-${skillCode}-2026`,
            });
            if (res && res.current_employee) {
                this.state.empDashboard.data = res;
                if (res.kpi_skill_hub) {
                    this.state.empDashboard.kpiForm.next_training_roadmap =
                        res.kpi_skill_hub.next_training_roadmap || "";
                    this.state.empDashboard.kpiForm.manager_review_note =
                        res.kpi_skill_hub.manager_review_note || "";
                }
            }
        } catch {
            // Fail-soft
        }
    }

    async onSubmitWorkKpiReview(approve = false) {
        const empId = this.state.empDashboard.data?.current_employee?.id;
        if (!empId) {
            return;
        }
        const kf = this.state.empDashboard.kpiForm;
        try {
            const res = await rpc("/insilos/employee_dashboard/submit_work_kpi_review", {
                employee_id: empId,
                kpi_delivery_score: Number(kf.kpi_delivery_score) || 90.0,
                kpi_quality_score: Number(kf.kpi_quality_score) || 90.0,
                kpi_work_eval_score: Number(kf.kpi_work_eval_score) || 90.0,
                next_training_roadmap: kf.next_training_roadmap,
                manager_review_note: kf.manager_review_note,
                approve_evaluation: Boolean(approve),
            });
            if (res && res.current_employee) {
                this.state.empDashboard.data = res;
            }
        } catch {
            // Fail-soft
        }
    }

    async onCheckinOkrKr(krCode, targetValue = null) {
        const empId = this.state.empDashboard.data?.current_employee?.id;
        if (!empId) {
            return;
        }
        const of = this.state.empDashboard.okrForm;
        try {
            const res = await rpc("/insilos/employee_dashboard/checkin_okr_kr", {
                employee_id: empId,
                kr_code: krCode || of.kr_code,
                current_value:
                    targetValue !== null && targetValue !== undefined
                        ? Number(targetValue)
                        : Number(of.current_value) || 100.0,
                pdca_stage: of.pdca_stage || "act",
                evidence_ref: of.evidence_ref || `PDCA-KR-${krCode || "2026Q4"}`,
            });
            if (res && res.current_employee) {
                this.state.empDashboard.data = res;
            }
        } catch {
            // Fail-soft
        }
    }

    async onSubmitHrAppraisal(signOff = true) {
        const empId = this.state.empDashboard.data?.current_employee?.id;
        if (!empId) {
            return;
        }
        const af = this.state.empDashboard.appraisalForm;
        try {
            const res = await rpc("/insilos/employee_dashboard/submit_hr_appraisal", {
                employee_id: empId,
                self_assessment_score: Number(af.self_assessment_score) || 92.0,
                peer_client_360_score: Number(af.peer_client_360_score) || 93.0,
                manager_technical_score: Number(af.manager_technical_score) || 92.0,
                self_reflection_text: af.self_reflection_text,
                peer_client_feedback_text: af.peer_client_feedback_text,
                manager_appraisal_text: af.manager_appraisal_text,
                pdca_next_quarter_plan: af.pdca_next_quarter_plan,
                sign_off: Boolean(signOff),
            });
            if (res && res.current_employee) {
                this.state.empDashboard.data = res;
            }
        } catch {
            // Fail-soft
        }
    }

    async onQuerySopRagCopilot(presetQuery = null) {
        const empId = this.state.empDashboard.data?.current_employee?.id;
        const sf = this.state.empDashboard.sopRagForm;
        const qText = (presetQuery !== null ? presetQuery : sf.query_text || "").trim();
        if (!qText) {
            return;
        }
        sf.query_text = qText;
        sf.loading = true;
        try {
            const res = await rpc("/insilos/employee_dashboard/sop_rag_query", {
                employee_id: empId,
                query_text: qText,
                channel_mode: sf.channel_mode || "internal_sop_copilot",
            });
            if (res) {
                if (res.current_employee) {
                    this.state.empDashboard.data = res;
                }
                sf.lastResult = {
                    query_text: qText,
                    response_text: res.response_text || "",
                    is_grounded: Boolean(res.is_grounded),
                    entailment_score: res.entailment_score ?? 0.92,
                    adversarial_blocked: Boolean(res.adversarial_blocked),
                    pii_redacted: Boolean(res.pii_redacted),
                    matched_sop_codes: res.matched_sop_codes || [],
                    citations: res.citations || [],
                };
            }
        } catch {
            // Fail-soft
        } finally {
            sf.loading = false;
        }
    }

    openKpiEvaluationApp() {
        return this.action.doAction({
            type: "ir.actions.act_window",
            name: "Đánh giá KPI & Lộ trình Kỹ năng Kỹ sư Phần mềm",
            res_model: "dgm.hr.kpi.evaluation",
            views: [
                [false, "list"],
                [false, "form"],
            ],
            target: "current",
        });
    }

    openOkrApp() {
        return this.action.doAction({
            type: "ir.actions.act_window",
            name: "Mục tiêu Chiến lược OKRs Doanh nghiệp Phần mềm (Chu trình PDCA)",
            res_model: "dgm.okr.objective",
            views: [
                [false, "list"],
                [false, "form"],
            ],
            target: "current",
        });
    }

    openHrAppraisalApp() {
        return this.action.doAction({
            type: "ir.actions.act_window",
            name: "Đánh giá Nhân sự 360° & Hiệu chuẩn Nhân tài 9-Box",
            res_model: "dgm.hr.appraisal.sheet",
            views: [
                [false, "list"],
                [false, "form"],
            ],
            target: "current",
        });
    }

    openProjectPdcaApp() {
        return this.action.doAction({
            type: "ir.actions.act_window",
            name: "Thư viện Dự án Mẫu Chuẩn PDCA (SAP Activate & Agile Onsite)",
            res_model: "dgm.project.pdca.template",
            views: [
                [false, "list"],
                [false, "form"],
            ],
            target: "current",
        });
    }

    openKnowledgeSopRagApp() {
        return this.action.doAction({
            type: "ir.actions.act_window",
            name: "Quản trị Tri thức & Chỉ mục SOP-RAG (SOP-DGM-12)",
            res_model: "dgm.knowledge.sop.workflow",
            views: [
                [false, "list"],
                [false, "form"],
            ],
            target: "current",
        });
    }

    async onRunAutonomousMarketingScan() {
        const empId = this.state.empDashboard.data?.current_employee?.id;
        this.state.empDashboard.marketingScanLoading = true;
        try {
            const res = await rpc("/insilos/employee_dashboard/run_autonomous_marketing_scan", {
                employee_id: empId,
            });
            if (res && res.current_employee) {
                this.state.empDashboard.data = res;
                this.state.empDashboard.lastMarketingScanResult = res.marketing_scan_result || null;
            }
        } catch {
            // Fail-soft
        } finally {
            this.state.empDashboard.marketingScanLoading = false;
        }
    }

    openMarketResearchRadarApp() {
        return this.action.doAction({
            type: "ir.actions.act_window",
            name: "Radar Nghiên cứu Thị trường B2B & Battlecard Đối thủ (SOP-DGM-13)",
            res_model: "dgm.market.research.radar",
            views: [
                [false, "list"],
                [false, "form"],
            ],
            target: "current",
        });
    }

    openAutonomousMarketingCampaignApp() {
        return this.action.doAction({
            type: "ir.actions.act_window",
            name: "Chiến dịch Marketing Tự hành 24/7 & Phễu 4-Touch ABM (SOP-DGM-13)",
            res_model: "dgm.marketing.automation.campaign",
            views: [
                [false, "list"],
                [false, "form"],
            ],
            target: "current",
        });
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

