import { MessagingMenu } from "@mail/core/public_web/messaging_menu";
import { MessagingMenuInDropdown } from "@mail/core/web/messaging_menu_in_dropdown";

import { patch } from "@web/core/utils/patch";

import { useBackButton } from "@web_mobile/js/core/hooks";

if (MessagingMenuInDropdown) {
    patch(MessagingMenuInDropdown.prototype, {
        setup() {
            super.setup();
            useBackButton(
                () => this.dropdown?.close(),
                () => Boolean(this.dropdown?.isOpen)
            );
        },
    });
}

patch(MessagingMenu.prototype, {
    setup() {
        super.setup();
        if (this.dropdown) {
            useBackButton(
                () => this.dropdown.close(),
                () => Boolean(this.dropdown.isOpen)
            );
        } else if (this.props?.close) {
            useBackButton(
                () => this.props.close(),
                () => Boolean(this.props.isOpen ?? true)
            );
        } else if (this.close) {
            useBackButton(
                () => this.close(),
                () => Boolean(this.props?.isOpen)
            );
        }
    },
});
