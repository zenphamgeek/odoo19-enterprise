import { Component } from "@odoo/owl";
import { components } from "@odoo/o-spreadsheet";

const { NumberInput } = components;

export class NumericFilterValue extends Component {
    static template = "spreadsheet_edition.NumericFilterValue";
    static components = { NumberInput };
    static props = {
        value: { optional: true },
        onValueChanged: Function,
    };
}
