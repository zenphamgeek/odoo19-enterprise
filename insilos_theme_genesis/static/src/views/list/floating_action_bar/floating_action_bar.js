import { Component } from "@insilos/owl";

export class FloatingBatchActionBar extends Component {
    static template = "insilos_theme_genesis.FloatingBatchActionBar";
    static props = {
        selectedCount: { type: Number, optional: true },
        isDomainSelected: { type: Boolean, optional: true },
        totalCount: { type: Number, optional: true },
        onApprove: { type: Function, optional: true },
        onExport: { type: Function, optional: true },
        onArchive: { type: Function, optional: true },
        onDelete: { type: Function, optional: true },
        onDiscard: { type: Function, optional: true },
        onSelectDomain: { type: Function, optional: true },
        headerButtons: { type: Array, optional: true },
        canArchive: { type: Boolean, optional: true },
        canDelete: { type: Boolean, optional: true },
        canExport: { type: Boolean, optional: true },
    };
    static defaultProps = {
        selectedCount: 0,
        isDomainSelected: false,
        totalCount: 0,
        canArchive: true,
        canDelete: true,
        canExport: true,
    };
}
