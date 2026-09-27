import { Chatter } from "@mail/chatter/web_portal_project/chatter";

export class BankRecChatter extends Chatter {
    static props = {
        ...(Array.isArray(Chatter.props)
            ? Object.fromEntries(Chatter.props.map((p) => [p.replace("?", ""), { optional: p.endsWith("?") }]))
            : (Chatter.props || {})),
        "*": true,
    };

    async reloadParentView() {
        await this.props.statementLine?.load();
    }
}
