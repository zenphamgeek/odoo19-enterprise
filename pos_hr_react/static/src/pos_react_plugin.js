(() => {
    "use strict";

    const h = React.createElement;

    function EmployeeLogin({ context }) {
        const employees = context.pluginData.employees || [];
        const [employeeId, setEmployeeId] = React.useState(context.pluginData.employee?.id || employees[0]?.id || "");
        const [credential, setCredential] = React.useState("");
        const [credentialType, setCredentialType] = React.useState("pin");
        const [error, setError] = React.useState("");
        const inputRef = React.useRef(null);

        React.useEffect(() => inputRef.current?.focus(), []);

        const submit = async (event) => {
            event.preventDefault();
            setError("");
            try {
                const employee = await context.rpc("pos.session", "pos_react_select_employee", [
                    context.sessionId,
                    Number(employeeId) || false,
                    credential,
                    credentialType,
                ]);
                context.unlock(employee);
                context.closeAction();
            } catch (failure) {
                setError(failure?.message || "Invalid employee credential");
            }
        };

        return h("div", { role: "dialog", "aria-modal": "true", "aria-labelledby": "employee-login-title", onKeyDown: (event) => {
            if (event.key === "Escape") context.closeAction();
        } },
            h("form", { onSubmit: submit },
                h("h2", { id: "employee-login-title" }, "Select Cashier"),
                h("label", null, "Authentication method",
                    h("select", { value: credentialType, onChange: (event) => setCredentialType(event.target.value) },
                        h("option", { value: "pin" }, "PIN"),
                        h("option", { value: "barcode" }, "Barcode"))),
                credentialType === "pin" ? h("label", null, "Employee",
                    h("select", { value: employeeId, onChange: (event) => setEmployeeId(event.target.value) },
                        employees.map((employee) => h("option", { key: employee.id, value: employee.id }, employee.name)))) : null,
                h("label", null, credentialType === "pin" ? "PIN" : "Barcode",
                    h("input", { ref: inputRef, type: "password", value: credential, required: credentialType === "barcode" || employees.find((item) => item.id === Number(employeeId))?.hasPin, "aria-invalid": Boolean(error), "aria-describedby": error ? "employee-login-error" : undefined, onChange: (event) => setCredential(event.target.value) })),
                error ? h("p", { id: "employee-login-error", role: "alert" }, error) : null,
                h("button", { type: "submit" }, "Confirm"),
                h("button", { type: "button", onClick: context.closeAction }, "Cancel")));
    }

    function CashMove({ context }) {
        const [type, setType] = React.useState("in");
        const [amount, setAmount] = React.useState("");
        const [reason, setReason] = React.useState("");
        const [error, setError] = React.useState("");

        const submit = async (event) => {
            event.preventDefault();
            const value = Number(amount);
            if (context.locked || !Number.isFinite(value) || value <= 0 || !reason.trim()) return;
            setError("");
            try {
                await context.rpc("pos.session", "pos_react_try_cash_in_out", [
                    context.sessionId,
                    type,
                    value,
                    reason.trim(),
                ]);
                context.closeAction();
            } catch (failure) {
                setError(failure?.message || "Could not record cash movement");
            }
        };

        return h("div", { role: "dialog", "aria-modal": "true", "aria-labelledby": "cash-move-title" },
            h("form", { onSubmit: submit },
                h("h2", { id: "cash-move-title" }, "Cash In / Out"),
                h("label", null, "Movement",
                    h("select", { value: type, disabled: context.locked, onChange: (event) => setType(event.target.value) },
                        h("option", { value: "in" }, "Cash In"),
                        h("option", { value: "out" }, "Cash Out"))),
                h("label", null, "Amount",
                    h("input", { type: "number", min: "0.01", step: "any", required: true, value: amount, disabled: context.locked, onChange: (event) => setAmount(event.target.value) })),
                h("label", null, "Reason",
                    h("input", { required: true, value: reason, disabled: context.locked, onChange: (event) => setReason(event.target.value) })),
                error ? h("p", { role: "alert" }, error) : null,
                h("button", { type: "submit", disabled: context.locked }, "Confirm"),
                h("button", { type: "button", onClick: context.closeAction }, "Cancel")));
    }

    window.posReactPlugins.register("slot", "pos_hr_react.active_employee", {
        slot: "header",
        component: ({ pluginData }) => h("span", { "data-active-employee-id": pluginData.employee?.id }, pluginData.employee?.name || ""),
    });

    window.posReactPlugins.register("action", "pos_hr_react.select_employee", {
        label: "Select Cashier",
        isVisible: ({ pluginData }) => Boolean(pluginData.employee),
        component: (context) => h(EmployeeLogin, { context }),
        restore: ({ rpc, sessionId }, employeeId) => rpc("pos.session", "pos_react_restore_employee", [sessionId, employeeId]),
        canMutate({ locked }) {
            return !locked;
        },
        canRefund({ pluginData, locked }) {
            return !locked && pluginData.role !== "minimal";
        },
        canMutateLine(line, { pluginData, locked }) {
            return !locked && pluginData.role !== "minimal";
        },
    });

    window.posReactPlugins.register("action", "pos_hr_react.cash_move", {
        label: "Cash In / Out",
        isVisible: ({ pluginData, locked }) => Boolean(pluginData.employee) && !locked,
        component: (context) => h(CashMove, { context }),
    });

    window.posReactPlugins.register("action", "pos_hr_react.lock", {
        label: "Lock",
        isVisible: ({ pluginData, locked }) => Boolean(pluginData.employee) && !locked,
        run: ({ lock }) => lock(),
    });
})();
