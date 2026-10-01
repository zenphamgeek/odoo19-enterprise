import { NavBar } from "@web/webclient/navbar/navbar";
import { useService, useBus } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { useEffect, signal, onMounted } from "@insilos/owl";

export class EnterpriseNavBar extends NavBar {
    static template = "web_enterprise.EnterpriseNavBar";
    nav = signal.ref();

    setup() {
        super.setup();
        this.hm = useService("home_menu");
        this.pwa = useService("pwa");
        this._busToggledCallback = () => this._updateMenuAppsIcon();
        useBus(this.env.bus, "HOME-MENU:TOGGLED", this._busToggledCallback);
        onMounted(() => this._updateMenuAppsIcon());
        useEffect(() => this._updateMenuAppsIcon());
    }
    get hasBackgroundAction() {
        return this.hm.hasBackgroundAction;
    }
    get isInApp() {
        return !this.hm.hasHomeMenu;
    }

    _openAppMenuSidebar() {
        if (this.hm.hasHomeMenu) {
            this.hm.toggle(false);
        } else {
            this.state.isAppMenuSidebarOpened = true;
        }
    }
    _updateMenuAppsIcon() {
        const isInApp = this.isInApp;
        const hasBackgroundAction = this.hasBackgroundAction;
        const menuAppsEl = this.menuApps();
        if (!menuAppsEl) {
            return;
        }
        menuAppsEl.classList.toggle("o_hidden", !isInApp && !hasBackgroundAction);
        menuAppsEl.classList.toggle(
            "o_menu_toggle_back",
            !isInApp && hasBackgroundAction
        );
        if (!this.isScopedApp) {
            const title =
                !isInApp && hasBackgroundAction ? _t("Previous view") : _t("Home menu");
            menuAppsEl.title = title;
            menuAppsEl.ariaLabel = title;
        }

        const navEl = this.nav() || this.root();
        const menuBrand = navEl?.querySelector(".o_menu_brand");
        if (menuBrand) {
            menuBrand.classList.toggle("o_hidden", !isInApp);
        }

        const menuBrandIcon = navEl?.querySelector(".o_menu_brand_icon");
        if (menuBrandIcon) {
            menuBrandIcon.classList.toggle("o_hidden", !isInApp);
        }

        const menuBrandSeparator = navEl?.querySelector(".o_menu_brand_separator");
        if (menuBrandSeparator) {
            menuBrandSeparator.classList.toggle("o_hidden", !isInApp);
        }

        const appSubMenus =
            (typeof this.appSubMenus === "function" ? this.appSubMenus() : this.appSubMenus?.el) ||
            navEl?.querySelector(".o_menu_sections");
        if (appSubMenus) {
            appSubMenus.classList.toggle("o_hidden", !isInApp);
        }

        const breadcrumb = navEl?.querySelector(".o_breadcrumb");
        if (breadcrumb) {
            breadcrumb.classList.toggle("o_hidden", !isInApp);
        }
    }

    /**
     * @override
     */
    onAllAppsBtnClick() {
        super.onAllAppsBtnClick();
        this.hm.toggle(true);
        this._closeAppMenuSidebar();
    }
}
