export class NotificationRequestPopup {
    constructor(parent, options = {}) {
        this.parent = parent;
        this.notificationTitle = options.title;
        this.notificationBody = options.body;
        this.notificationDelay = options.delay || 3;
        this.notificationIcon = options.icon;
        this.callbacks = {};
    }

    on(event, unused, handler) {
        const cb = typeof unused === 'function' ? unused : handler;
        if (!this.callbacks[event]) this.callbacks[event] = [];
        this.callbacks[event].push(cb);
        return this;
    }

    trigger(event, data) {
        if (this.callbacks[event]) {
            for (const cb of this.callbacks[event]) cb(data);
        }
    }

    appendTo(target) {
        const targetEl = target.el || (target instanceof HTMLElement ? target : document.body);
        const div = document.createElement("div");
        div.className = "o_social_push_notifications_permission_request dropdown position-fixed";
        div.innerHTML = `
            <div class="dropdown-menu show p-3 shadow">
                <div class="d-flex align-items-center mb-2">
                    ${this.notificationIcon ? `<img src="${this.notificationIcon}" class="me-2" style="width: 24px; height: 24px;"/>` : ''}
                    <strong>${this.notificationTitle || ''}</strong>
                </div>
                <p class="mb-3">${this.notificationBody || ''}</p>
                <div class="d-flex justify-content-end gap-2">
                    <button class="btn btn-sm btn-secondary o_social_push_notifications_permission_deny">Deny</button>
                    <button class="btn btn-sm btn-primary o_social_push_notifications_permission_allow">Allow</button>
                </div>
            </div>
        `;
        if (document.getElementById('oe_main_menu_navbar')) {
            div.classList.add('o_social_push_notifications_permission_with_menubar');
        }
        this.el = div;
        targetEl.appendChild(div);

        div.querySelector('.o_social_push_notifications_permission_allow')?.addEventListener('click', () => this.trigger('allow'));
        div.querySelector('.o_social_push_notifications_permission_deny')?.addEventListener('click', () => {
            this.trigger('deny');
            this.destroy();
        });
        return this;
    }

    destroy() {
        if (this.timer) clearTimeout(this.timer);
        this.el?.remove();
    }
}

export default NotificationRequestPopup;
