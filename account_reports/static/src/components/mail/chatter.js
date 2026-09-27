import { Chatter } from "@mail/chatter/web_portal_project/chatter";
import { AccountReportComposer } from "./composer";
import { AccountReportThread } from "./thread";

export class AccountReportChatter extends Chatter {
    static template = "account_reports.Chatter";
    static props = { ...(Chatter.props || {}), reportController: { optional: true }, date_to: true, list: { optional: true } };
    static components = {
        ...Chatter.components,
        Composer: AccountReportComposer,
        Thread: AccountReportThread,
    };
}
