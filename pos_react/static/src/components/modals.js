(() => {
    "use strict";

    const { createElement: h, useState, useMemo, useEffect, useRef } = window.React;

    /**
     * Customer Selection & Quick Partner Creation Modal
     */
    function CustomerModal({ customers = [], customerId = false, onSelect, onClose, onQuickCreate }) {
        const [search, setSearch] = useState("");
        const [isCreating, setIsCreating] = useState(false);
        const [newName, setNewName] = useState("");
        const [newPhone, setNewPhone] = useState("");
        const [newEmail, setNewEmail] = useState("");
        const [isSubmitting, setIsSubmitting] = useState(false);
        const [error, setError] = useState("");
        const searchInputRef = useRef(null);

        useEffect(() => {
            searchInputRef.current?.focus();
            const handleEsc = (e) => { if (e.key === "Escape") onClose(); };
            window.addEventListener("keydown", handleEsc);
            return () => window.removeEventListener("keydown", handleEsc);
        }, [onClose]);

        const filtered = useMemo(() => {
            const q = search.trim().toLowerCase();
            if (!q) return customers.slice(0, 30);
            return customers.filter((c) =>
                (c.name && c.name.toLowerCase().includes(q)) ||
                (c.display_name && c.display_name.toLowerCase().includes(q)) ||
                (c.phone && c.phone.includes(q)) ||
                (c.email && c.email.toLowerCase().includes(q)) ||
                (c.vat && c.vat.toLowerCase().includes(q))
            ).slice(0, 50);
        }, [customers, search]);

        const handleCreateSubmit = async (e) => {
            e.preventDefault();
            if (!newName.trim()) {
                setError("Please enter a customer name.");
                return;
            }
            setIsSubmitting(true);
            setError("");
            try {
                const partner = await onQuickCreate({
                    name: newName.trim(),
                    phone: newPhone.trim(),
                    email: newEmail.trim(),
                });
                if (partner) {
                    onSelect(partner.id);
                    onClose();
                }
            } catch (err) {
                setError(err?.message || "Failed to create customer");
                setIsSubmitting(false);
            }
        };

        return h("div", { className: "pos-modal-overlay", role: "dialog", "aria-modal": "true" },
            h("div", { className: "pos-modal-dialog", style: { width: "560px" } },
                // Header
                h("div", { className: "pos-modal-header" },
                    h("h3", { className: "pos-modal-title" }, isCreating ? "Create New Customer" : "Select Customer"),
                    h("button", { type: "button", className: "pos-modal-close-btn", onClick: onClose }, "×")
                ),
                // Body
                h("div", { className: "pos-modal-body" },
                    !isCreating ? h("div", { style: { display: "flex", flexDirection: "column", gap: "12px" } },
                        h("div", { style: { display: "flex", gap: "8px" } },
                            h("input", {
                                ref: searchInputRef,
                                type: "search",
                                className: "pos-search-input",
                                placeholder: "Search by name, phone, email, vat…",
                                value: search,
                                onChange: (e) => setSearch(e.target.value),
                            }),
                            h("button", {
                                type: "button",
                                className: "pos-header-btn",
                                style: { background: "var(--pos-accent)", color: "#050b14", fontWeight: "700" },
                                onClick: () => setIsCreating(true),
                            }, "+ Create")
                        ),
                        h("div", { style: { maxHeight: "360px", overflowY: "auto", display: "flex", flexDirection: "column", gap: "4px" } },
                            h("div", {
                                onClick: () => { onSelect(false); onClose(); },
                                style: {
                                    padding: "10px 14px",
                                    borderRadius: "var(--pos-radius-sm)",
                                    background: !customerId ? "var(--pos-bg-card)" : "var(--pos-bg-surface)",
                                    border: !customerId ? "1px solid var(--pos-accent)" : "1px solid var(--pos-border)",
                                    cursor: "pointer",
                                    color: "var(--pos-text-muted)",
                                }
                            }, "— No Customer (Walk-in Guest) —"),
                            filtered.map((c) => {
                                const isSelected = c.id === customerId;
                                return h("div", {
                                    key: c.id,
                                    onClick: () => { onSelect(c.id); onClose(); },
                                    style: {
                                        padding: "10px 14px",
                                        borderRadius: "var(--pos-radius-sm)",
                                        background: isSelected ? "var(--pos-bg-card)" : "var(--pos-bg-surface)",
                                        border: isSelected ? "1px solid var(--pos-accent)" : "1px solid var(--pos-border)",
                                        cursor: "pointer",
                                        display: "flex",
                                        justifyContent: "space-between",
                                        alignItems: "center",
                                    }
                                },
                                    h("div", null,
                                        h("div", { style: { fontWeight: "600", color: "var(--pos-text-primary)" } }, c.display_name || c.name),
                                        h("div", { style: { fontSize: "12px", color: "var(--pos-text-secondary)" } },
                                            [c.phone, c.email, c.vat].filter(Boolean).join(" · ")
                                        )
                                    ),
                                    isSelected ? h("span", { style: { color: "var(--pos-accent)", fontWeight: "700" } }, "✓ Selected") : null
                                );
                            })
                        )
                    ) : h("form", { onSubmit: handleCreateSubmit, style: { display: "flex", flexDirection: "column", gap: "14px" } },
                        h("div", null,
                            h("label", { style: { display: "block", fontSize: "13px", marginBottom: "4px", color: "var(--pos-text-secondary)" } }, "Customer Name *"),
                            h("input", {
                                type: "text",
                                required: true,
                                value: newName,
                                onChange: (e) => setNewName(e.target.value),
                                className: "pos-search-input",
                                style: { padding: "0 12px" },
                                placeholder: "e.g. Acme Corp / Nguyen Van A",
                            })
                        ),
                        h("div", null,
                            h("label", { style: { display: "block", fontSize: "13px", marginBottom: "4px", color: "var(--pos-text-secondary)" } }, "Phone Number"),
                            h("input", {
                                type: "tel",
                                value: newPhone,
                                onChange: (e) => setNewPhone(e.target.value),
                                className: "pos-search-input",
                                style: { padding: "0 12px" },
                                placeholder: "e.g. +84 901 234 567",
                            })
                        ),
                        h("div", null,
                            h("label", { style: { display: "block", fontSize: "13px", marginBottom: "4px", color: "var(--pos-text-secondary)" } }, "Email Address"),
                            h("input", {
                                type: "email",
                                value: newEmail,
                                onChange: (e) => setNewEmail(e.target.value),
                                className: "pos-search-input",
                                style: { padding: "0 12px" },
                                placeholder: "e.g. billing@company.com",
                            })
                        ),
                        error ? h("p", { style: { color: "var(--pos-danger)", fontSize: "13px", margin: 0 }, role: "alert" }, error) : null,
                        h("div", { style: { display: "flex", justifyContent: "flex-end", gap: "10px", marginTop: "12px" } },
                            h("button", {
                                type: "button",
                                className: "pos-header-btn",
                                onClick: () => setIsCreating(false),
                            }, "Cancel"),
                            h("button", {
                                type: "submit",
                                className: "pos-action-btn pay-btn",
                                style: { height: "38px", padding: "0 16px" },
                                disabled: isSubmitting,
                            }, isSubmitting ? "Creating…" : "Save & Select")
                        )
                    )
                )
            )
        );
    }

    /**
     * Order Note / Kitchen Instruction Modal
     */
    function NoteModal({ title = "Order Note", initialNote = "", onSave, onClose }) {
        const [note, setNote] = useState(initialNote);
        const textareaRef = useRef(null);

        useEffect(() => {
            textareaRef.current?.focus();
            const handleEsc = (e) => { if (e.key === "Escape") onClose(); };
            window.addEventListener("keydown", handleEsc);
            return () => window.removeEventListener("keydown", handleEsc);
        }, [onClose]);

        const handleSubmit = (e) => {
            e.preventDefault();
            onSave(note.trim());
            onClose();
        };

        return h("div", { className: "pos-modal-overlay", role: "dialog", "aria-modal": "true" },
            h("div", { className: "pos-modal-dialog", style: { width: "450px" } },
                h("div", { className: "pos-modal-header" },
                    h("h3", { className: "pos-modal-title" }, title),
                    h("button", { type: "button", className: "pos-modal-close-btn", onClick: onClose }, "×")
                ),
                h("form", { onSubmit: handleSubmit },
                    h("div", { className: "pos-modal-body" },
                        h("textarea", {
                            ref: textareaRef,
                            rows: 4,
                            value: note,
                            onChange: (e) => setNote(e.target.value),
                            placeholder: "Type special instructions or customer notes…",
                            style: {
                                width: "100%",
                                background: "var(--pos-bg-card)",
                                border: "1px solid var(--pos-border)",
                                borderRadius: "var(--pos-radius-sm)",
                                padding: "12px",
                                color: "var(--pos-text-primary)",
                                fontSize: "14px",
                                resize: "vertical",
                                outline: "none",
                            }
                        })
                    ),
                    h("div", { className: "pos-modal-footer" },
                        h("button", { type: "button", className: "pos-header-btn", onClick: onClose }, "Cancel"),
                        h("button", {
                            type: "submit",
                            className: "pos-action-btn pay-btn",
                            style: { height: "36px", padding: "0 16px" }
                        }, "Save Note")
                    )
                )
            )
        );
    }

    window.PosReactModals = {
        CustomerModal,
        NoteModal,
    };
})();
