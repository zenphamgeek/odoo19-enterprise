import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";
import { browser } from "@web/core/browser/browser";
import { rpc } from "@web/core/network/rpc";
import NotificationRequestPopup from "@social_push_notifications/js/push_notification_request_popup";
import { Component } from "@odoo/owl";

export class NotificationWidget extends Interaction {
    static selector = '#wrapwrap';

    async start() {
        this.notification = this.services?.notification;

        const loadFirebaseAssets = () => {
            return new Promise((resolve, reject) => {
                const script = document.createElement("script");
                script.addEventListener("load", () => {
                    resolve(globalThis.firebase);
                });
                script.addEventListener("error", error => {
                    reject(error);
                });
                script.type = "module";
                script.src = "/social_push_notifications/static/lib/firebase.js";
                document.head.appendChild(script);
            });
        };
        try {
            this.firebase = await loadFirebaseAssets();
        } catch {}

        if (!this._isBrowserCompatible() || !this.firebase) {
            return;
        }

        const self = this;
        if (Notification.permission === "granted") {
            const { pushConfigurationPromise, wasUpdated } = this._getNotificationRequestConfiguration();
            pushConfigurationPromise.then((pushConfiguration) => {
                if (Object.keys(pushConfiguration).length === 1) {
                    return;
                }
                const messaging = self._initializeFirebaseApp(pushConfiguration);
                if (wasUpdated) {
                    self._registerServiceWorker(pushConfiguration, messaging);
                }
                self._setForegroundNotificationHandler(pushConfiguration, messaging);
            });
        } else if (Notification.permission !== "denied") {
            this._askPermission();
        }
        Component.env?.bus?.addEventListener('open_notification_request', (ev) => this._onNotificationRequest(...ev.detail));
    }

    _setForegroundNotificationHandler(config, messaging) {
        const onMessage = (payload) => {
            if (window.Notification && Notification.permission === "granted") {
                const options = {
                    title: payload.notification.title,
                    type: 'success',
                };
                if (payload.data && payload.data.target_url) {
                    options.buttons = [{
                        name: 'Open',
                        onClick: () => window.open(payload.data.target_url, '_blank'),
                    }];
                }
                this.notification?.add?.(payload.notification.body, options);
            }
        };
        messaging = messaging || this._initializeFirebaseApp(config);
        if (!messaging) {
            return;
        }
        this.firebase.onMessage(messaging, onMessage);
    }

    _isBrowserCompatible() {
        if (!('serviceWorker' in navigator)) {
            return false;
        }
        if (!('PushManager' in window)) {
            return false;
        }
        return true;
    }

    _initializeFirebaseApp(config) {
        if (!config.firebase_push_certificate_key
            || !config.firebase_project_id
            || !config.firebase_web_api_key
            || !config.firebase_web_app_id) {
            return null;
        }

        const app = this.firebase.initializeApp({
            appId: config.firebase_web_app_id,
            apiKey: config.firebase_web_api_key,
            projectId: config.firebase_project_id,
            messagingSenderId: config.firebase_sender_id
        });

        const messaging = this.firebase.getMessaging(app);
        return messaging;
    }

    _registerServiceWorker(config, messaging) {
        const self = this;

        messaging = messaging || this._initializeFirebaseApp(config);
        if (!messaging) {
            return;
        }

        const url = new URL(window.location.origin + "/social_push_notifications/static/src/js/push_service_worker.js");
        url.searchParams.append("appId", config.firebase_web_app_id);
        url.searchParams.append("apiKey", config.firebase_web_api_key);
        url.searchParams.append("projectId", config.firebase_project_id);
        url.searchParams.append("messagingSenderId", config.firebase_sender_id);

        navigator.serviceWorker.register(url, { type: "module" })
            .then(function (registration) {
                self.firebase.getToken(messaging, {
                    vapidKey: config.firebase_push_certificate_key,
                    serviceWorkerRegistration: registration
                }).then(function (token) {
                    self._registerToken(token);
                });
        });
    }

    _isConfigurationUpToDate(pushConfiguration) {
        if (pushConfiguration) {
            if (new Date() < new Date(pushConfiguration.expirationDate)) {
                return true;
            }
        }
        return false;
    }

    _fetchPushConfiguration() {
        return rpc('/social_push_notifications/fetch_push_configuration').then(function (config) {
            const expirationDate = new Date();
            expirationDate.setDate(expirationDate.getDate() + 7);
            Object.assign(config, {'expirationDate': expirationDate});
            browser.localStorage.setItem(
                'social_push_notifications.notification_request_config',
                JSON.stringify(config)
            );
            return config;
        });
    }

    _registerToken(token) {
        var pushConfiguration = this._getPushConfiguration();
        if (pushConfiguration && pushConfiguration.token !== token) {
            rpc('/social_push_notifications/unregister', {
                token: pushConfiguration.token
            });
        }

        rpc('/social_push_notifications/register', {
            token: token
        }).then(function () {
            browser.localStorage.setItem('social_push_notifications.configuration', JSON.stringify({
                'token': token,
            }));
        });
    }

    async _askPermission(nextAskPermissionKeySuffix, forcedPopupConfig) {
        var self = this;

        var nextAskPermission = browser.localStorage.getItem('social_push_notifications.next_ask_permission' +
            (nextAskPermissionKeySuffix ? '.' + nextAskPermissionKeySuffix : ''));
        if (nextAskPermission && new Date() < new Date(nextAskPermission)) {
            return;
        }

        const { pushConfigurationPromise } = this._getNotificationRequestConfiguration();
        const pushConfiguration = await pushConfigurationPromise;
        if (!pushConfiguration || Object.keys(pushConfiguration).length <= 1) {
            return;
        }
        let popupConfig = {
            title: pushConfiguration.notification_request_title,
            body: pushConfiguration.notification_request_body,
            delay: pushConfiguration.notification_request_delay,
            icon: pushConfiguration.notification_request_icon
        };

        if (!popupConfig || !popupConfig.title || !popupConfig.body) {
            return;
        }
        if (forcedPopupConfig) {
            popupConfig = Object.assign({}, popupConfig, forcedPopupConfig);
        }
        self._showNotificationRequestPopup(popupConfig, pushConfiguration, nextAskPermissionKeySuffix);
    }

    _showNotificationRequestPopup(popupConfig, pushConfig, nextAskPermissionKeySuffix) {
        var selector = '.o_social_push_notifications_permission_request';
        if (!popupConfig.title || !popupConfig.body || this.el.querySelector(selector)) {
            return;
        }

        var self = this;
        var notificationRequestPopup = new NotificationRequestPopup(this, {
            title: popupConfig.title,
            body: popupConfig.body,
            delay: popupConfig.delay,
            icon: popupConfig.icon
        });
        notificationRequestPopup.appendTo(this.el);

        notificationRequestPopup.on('allow', null, function () {
            Notification.requestPermission().then(function () {
                if (Notification.permission === "granted") {
                    const messaging = self._initializeFirebaseApp(pushConfig);
                    self._registerServiceWorker(pushConfig, messaging);
                    self._setForegroundNotificationHandler(pushConfig, messaging);
                }
            });
        });

        notificationRequestPopup.on('deny', null, function () {
            var nextAskPermissionDate = new Date();
            nextAskPermissionDate.setDate(nextAskPermissionDate.getDate() + 7);
            browser.localStorage.setItem('social_push_notifications.next_ask_permission' +
                (nextAskPermissionKeySuffix ? '.' + nextAskPermissionKeySuffix : ''),
                nextAskPermissionDate);
        });
    }

    _getPushConfiguration() {
        return this._getJSONLocalStorageItem(
            'social_push_notifications.configuration'
        );
    }

    _getNotificationRequestConfiguration() {
        const pushConfiguration = this._getJSONLocalStorageItem(
            'social_push_notifications.notification_request_config'
        );

        const wasUpdated = !this._isConfigurationUpToDate(pushConfiguration);
        const pushConfigurationPromise = wasUpdated ? this._fetchPushConfiguration() :
            Promise.resolve(pushConfiguration);

        return { pushConfigurationPromise, wasUpdated };
    }

    _getJSONLocalStorageItem(key) {
        var value = browser.localStorage.getItem(key);
        if (value) {
            return JSON.parse(value);
        }
        return null;
    }

    async _onNotificationRequest(nextAskPermissionKeySuffix, forcedPopupConfig) {
        if (Notification.permission !== 'default') {
            return;
        }
        this._askPermission(nextAskPermissionKeySuffix, forcedPopupConfig);
    }
}

registry.category("public.interactions").add("social_push_notifications.notification_widget", NotificationWidget);
export default NotificationWidget;
