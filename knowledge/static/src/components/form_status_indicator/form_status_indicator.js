import { FormStatusIndicator } from "@web/views/form/form_status_indicator/form_status_indicator";

/**
 * This extension of the FormStatusIndicator is used to add a new indicator to the ones that already
 * exists. This new icon is used in the same way as the icon in Google Docs => indicate that all changes
 * have been committed to the DB.
 */
export class KnowledgeFormStatusIndicator extends FormStatusIndicator {
    static template = 'knowledge.FormStatusIndicator';
    static props = {
        model: { type: Object, optional: true },
        record: { type: Object, optional: true },
        isDirty: { type: Boolean, optional: true },
        isValid: { type: Boolean, optional: true },
        isNew: { type: Boolean, optional: true },
        save: { type: Function, optional: true },
        discard: { type: Function, optional: true },
    };

    get isNew() {
        return Boolean(this.props.isNew || this.props.model?.root?.isNew || this.props.record?.isNew);
    }

    get isDirty() {
        return Boolean(this.props.isDirty || this.props.model?.root?.dirty || this.props.record?.dirty);
    }
}
