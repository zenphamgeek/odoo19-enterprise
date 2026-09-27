/** @insilos-module **/

import { patch } from '@web/core/utils/patch';
import { HomeMenu } from "@web_enterprise/webclient/home_menu/home_menu";
import { onWillStart, useState } from '@odoo/owl';

patch(HomeMenu.prototype, {
    setup() {
        super.setup(...arguments);
        this.fsmState = useState({
            todayTasks: 0,
            unassignedOrders: 0,
            isFsmActive: true,
        });

        onWillStart(async () => {
            await this.fetchFsmQuickStats();
        });
    },

    async fetchFsmQuickStats() {
        try {
            if (this.orm) {
                const todayCount = await this.orm.call("project.task", "search_count", [
                    [["is_fsm", "=", true], ["user_ids", "in", [this.user.userId]]]
                ]).catch(() => 0);
                
                const unassignedCount = await this.orm.call("project.task", "search_count", [
                    [["is_fsm", "=", true], ["user_ids", "=", false]]
                ]).catch(() => 0);

                this.fsmState.todayTasks = todayCount || 0;
                this.fsmState.unassignedOrders = unassignedCount || 0;
            }
        } catch (e) {
            // Safe fallback
        }
    },

    openFsmTasks(filter = 'my') {
        if (this.actionService) {
            if (filter === 'unassigned') {
                this.actionService.doAction({
                    name: "Unassigned Field Orders",
                    type: "is.actions.act_window",
                    res_model: "project.task",
                    views: [[false, "list"], [false, "kanban"], [false, "form"]],
                    domain: [["is_fsm", "=", true], ["user_ids", "=", false]],
                });
            } else {
                this.actionService.doAction("industry_fsm.project_task_action_fsm");
            }
        }
    }
});
