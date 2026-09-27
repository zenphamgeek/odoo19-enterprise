import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { PhoneField, phoneField, formPhoneField } from "@web/views/fields/phone/phone_field";
import { SendWhatsAppButton } from "../whatsapp_button/whatsapp_button.js";

patch(PhoneField, {
    components: {
        ...PhoneField.components,
        SendWhatsAppButton,
    },
});

const patchDescr = {
    extractProps({ options }) {
        const props = super.extractProps(...arguments);
        props.enableWhatsAppButton = options.enable_whatsapp;
        return props;
    },
    supportedOptions: [
        ...(phoneField.supportedOptions ? phoneField.supportedOptions : []),
        {
            label: _t("Enable WhatsApp"),
            name: "enable_whatsapp",
            type: "boolean",
            default: true,
        },
    ],
};

patch(phoneField, patchDescr);
if (formPhoneField && formPhoneField !== phoneField) {
    patch(formPhoneField, patchDescr);
}
