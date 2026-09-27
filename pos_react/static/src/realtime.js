(() => {
    "use strict";

    function connectRealtime({ token, version, lastId = 0, onSynchronisation, onStatus = () => {}, url }) {
        if (typeof token !== "string" || !token) throw new TypeError("token is required");
        if (typeof version !== "string" || !version) throw new TypeError("version is required");
        if (typeof onSynchronisation !== "function") throw new TypeError("onSynchronisation must be a function");
        if (typeof onStatus !== "function") throw new TypeError("onStatus must be a function");

        url ||= `${location.origin.replace(/^http/, "ws")}/websocket?version=${encodeURIComponent(version)}`;
        let socket;
        let retryTimer;
        let retryDelay = 1000;
        let closed = false;

        function open() {
            if (closed || !navigator.onLine || socket?.readyState < WebSocket.CLOSING) return;
            clearTimeout(retryTimer);
            onStatus("connecting");
            socket = new WebSocket(url);
            socket.onopen = () => {
                retryDelay = 1000;
                socket.send(JSON.stringify({ event_name: "subscribe", data: { channels: [token], last: lastId } }));
                onStatus("connected");
            };
            socket.onmessage = ({ data }) => {
                const notifications = JSON.parse(data);
                for (const notification of notifications) {
                    lastId = Math.max(lastId, notification.id || 0);
                    if (notification.message?.type === `${token}-SYNCHRONISATION`) {
                        onSynchronisation(notification.message.payload);
                    }
                }
            };
            socket.onerror = () => socket.close();
            socket.onclose = () => {
                socket = null;
                if (closed) return;
                onStatus("disconnected");
                clearTimeout(retryTimer);
                retryTimer = setTimeout(open, retryDelay);
                retryDelay = Math.min(retryDelay * 2, 30000);
            };
        }

        function reconnectOnline() {
            if (!closed && socket?.readyState !== WebSocket.OPEN) open();
        }

        addEventListener("online", reconnectOnline);
        open();
        return {
            close() {
                closed = true;
                clearTimeout(retryTimer);
                removeEventListener("online", reconnectOnline);
                socket?.close(1000);
                socket = null;
                onStatus("closed");
            },
            get lastId() {
                return lastId;
            },
        };
    }

    window.posReactRealtime = Object.freeze({ connect: connectRealtime });
})();
