import { describe, expect, test } from "@insilos/hoot";
import { click } from "@insilos/hoot-dom";
import { animationFrame } from "@insilos/hoot-mock";
import { mockService, mountWithCleanup } from "@web/../tests/web_test_helpers";
import { HomeMenu } from "@web_enterprise/webclient/home_menu/home_menu";

describe.current.tags("desktop");

const getAppDrawerRoutesProps = () => {
    const apps = [
        {
            actionID: 123,
            href: "/insilos/contacts",
            appID: 10,
            id: 10,
            label: "BP Contacts",
            parents: "",
            webIcon: false,
            xmlid: "contacts.menu_contacts",
        },
        {
            actionID: 960,
            href: "/insilos/knowledge",
            appID: 8,
            id: 8,
            label: "Knowledge",
            parents: "",
            webIcon: false,
            xmlid: "knowledge.knowledge_menu_root",
        },
        {
            actionID: 800,
            href: "/insilos/esg",
            appID: 25,
            id: 25,
            label: "ESG",
            parents: "",
            webIcon: false,
            xmlid: "esg.esg_menu_root",
        },
        {
            actionID: 500,
            href: "/insilos/manufacturing",
            appID: 51,
            id: 51,
            label: "PP Manufacturing",
            parents: "",
            webIcon: false,
            xmlid: "mrp.menu_mrp_root",
        },
        {
            actionID: 300,
            href: "/insilos/dashboards?dashboard_id=3",
            appID: 15,
            id: 15,
            label: "BI Dashboards",
            parents: "",
            webIcon: false,
            xmlid: "spreadsheet_dashboard.spreadsheet_dashboard_menu_root",
        },
    ];
    return { apps, reorderApps: () => {} };
};

test("@web_enterprise/app_drawer/renders contacts route /insilos/contacts and dispatches selectMenu", async () => {
    mockService("menu", {
        async selectMenu(menu) {
            expect.step(`selectMenu:${menu.id}:${menu.href}`);
        },
    });
    await mountWithCleanup(HomeMenu, {
        props: getAppDrawerRoutesProps(),
    });
    expect(".o_menuitem").toHaveCount(5);
    expect(".o_menuitem[href='/insilos/contacts']").toHaveCount(1);
    await click(".o_menuitem[href='/insilos/contacts']");
    await animationFrame();
    expect.verifySteps(["selectMenu:10:/insilos/contacts"]);
});

test("@web_enterprise/app_drawer/renders knowledge route /insilos/knowledge", async () => {
    mockService("menu", {
        async selectMenu(menu) {
            expect.step(`selectMenu:${menu.id}:${menu.href}`);
        },
    });
    await mountWithCleanup(HomeMenu, {
        props: getAppDrawerRoutesProps(),
    });
    expect(".o_menuitem[href='/insilos/knowledge']").toHaveCount(1);
    await click(".o_menuitem[href='/insilos/knowledge']");
    await animationFrame();
    expect.verifySteps(["selectMenu:8:/insilos/knowledge"]);
});

test("@web_enterprise/app_drawer/renders esg dashboard route /insilos/esg", async () => {
    mockService("menu", {
        async selectMenu(menu) {
            expect.step(`selectMenu:${menu.id}:${menu.href}`);
        },
    });
    await mountWithCleanup(HomeMenu, {
        props: getAppDrawerRoutesProps(),
    });
    expect(".o_menuitem[href='/insilos/esg']").toHaveCount(1);
    await click(".o_menuitem[href='/insilos/esg']");
    await animationFrame();
    expect.verifySteps(["selectMenu:25:/insilos/esg"]);
});

test("@web_enterprise/app_drawer/renders pp manufacturing route /insilos/manufacturing", async () => {
    mockService("menu", {
        async selectMenu(menu) {
            expect.step(`selectMenu:${menu.id}:${menu.href}`);
        },
    });
    await mountWithCleanup(HomeMenu, {
        props: getAppDrawerRoutesProps(),
    });
    expect(".o_menuitem[href='/insilos/manufacturing']").toHaveCount(1);
    await click(".o_menuitem[href='/insilos/manufacturing']");
    await animationFrame();
    expect.verifySteps(["selectMenu:51:/insilos/manufacturing"]);
});

test("@web_enterprise/app_drawer/renders bi dashboards route /insilos/dashboards", async () => {
    mockService("menu", {
        async selectMenu(menu) {
            expect.step(`selectMenu:${menu.id}:${menu.href}`);
        },
    });
    await mountWithCleanup(HomeMenu, {
        props: getAppDrawerRoutesProps(),
    });
    expect(".o_menuitem[href='/insilos/dashboards?dashboard_id=3']").toHaveCount(1);
    await click(".o_menuitem[href='/insilos/dashboards?dashboard_id=3']");
    await animationFrame();
    expect.verifySteps(["selectMenu:15:/insilos/dashboards?dashboard_id=3"]);
});
