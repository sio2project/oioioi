let notificationsClient; // jshint ignore:line

function TranslationClient() {
    this.translationQueue = {};
    this.translationCache = {};
}

TranslationClient.prototype.constructor = TranslationClient;

TranslationClient.prototype.translate = function (originalText) {
    if (this.translationCache[originalText])
        return Promise.resolve(this.translationCache[originalText]);

    let tClient = this;
    return new Promise((resolve, reject) => {
        if (!this.translationQueue[originalText]) {
            this.translationQueue[originalText] = [];
            $.get('/translate/', {query: originalText}, 'json')
                .success(function (data) {
                    tClient.translationCache[originalText] = data.answer;
                    for (let request of tClient.translationQueue[originalText]) {
                        request.resolve(data.answer);
                    }
                    delete tClient.translationQueue[originalText];
                })
                .fail(function (err) {
                    console.warn('Translation failed!',  err);
                    for (let request of tClient.translationQueue[originalText]) {
                        request.reject(err);
                    }
                    delete tClient.translationQueue[originalText];
                });
        }
        this.translationQueue[originalText].push({resolve: resolve, reject: reject});
    });
};

let translationClient = new TranslationClient();

function NotificationsClient(serverUrl, sessionId) {
    this.NUMBER_BADGE_ID = "#notifications_number";
    this.TABLE_NOTIFICATIONS_ID = "#balloon_table_notifications";
    this.NO_NOTIFICATIONS_ID = "#info_no_notifications";
    this.DROPDOWN_ID = "#notifications_dropdown";
    this.DROPDOWN_PANEL_ID = "#notifications_panel";
    this.NUMBER_BADGE = $(this.NUMBER_BADGE_ID);
    this.TABLE_NOTIFICATIONS = $(this.TABLE_NOTIFICATIONS_ID);
    this.NO_NOTIFICATIONS = $(this.NO_NOTIFICATIONS_ID);
    this.DROPDOWN_PANEL = $(this.DROPDOWN_PANEL_ID);
    this.DROPDOWN = $(this.DROPDOWN_ID);
    this.DEBUG = true;
    this.NOTIF_SERVER_URL = serverUrl;
    this.NOTIF_SESSION = sessionId;
    this.CONTENT_ENTRY = '<li class="%(notclass)s"><a href="%(address)s" ' +
        'id="notif_msg_%(id)s">...' +
        '<span class="notification-details">%(details)s</span>' +
        '<time class="notification-time">%(time)s</time></a></li>';
    this.socket = undefined;
    this.notifCount = 0;
    this.messages = [];
    this.renderSuspended = false;

    this.openNotifications = [];
    this.waitingPermissions = [];
    this.permissionBanner = null;

    if (typeof(io) === 'undefined') {
        this.setErrorState();
        return;
    }

    this.renderMessages();
    $(this.DROPDOWN).on("click", this.acknowledgeMessages.bind(this));
    this.socket = io.connect(this.NOTIF_SERVER_URL);
    this.socket.on('connect', this.authenticate.bind(this));
    this.socket.emits = function(k, v) {
        this.socket.emit(k, JSON.stringify(v));
    }.bind(this);
    setInterval(this.notifWatchdog.bind(this), 2000);
    this.storage = new MessageManager(this);
    this.socket.on("message", this.storage.onMessageReceived.bind(this.storage));

}

NotificationsClient.prototype.constructor = NotificationsClient;

NotificationsClient.prototype.notifWatchdog = function() {
    if (!this.socket || !this.socket.connected) {
        this.setErrorState();
    }
};

NotificationsClient.prototype.clearNumberBadgeClasses = function() {
    this.NUMBER_BADGE.removeClass("label-default");
    this.NUMBER_BADGE.removeClass("label-success");
    this.NUMBER_BADGE.removeClass("label-warning");
};

NotificationsClient.prototype.setErrorState = function() {
    this.NUMBER_BADGE.text('!');
    this.clearNumberBadgeClasses();
    this.NUMBER_BADGE.addClass("label-warning");
};

NotificationsClient.prototype.authenticate = function() {
    let me = this;
    const sid = this.NOTIF_SESSION;
    this.socket.emits("authenticate", {session_id: sid});
    this.socket.on("authenticate", function(result)
    {
        if (result.status !== 'OK') {
            me.setErrorState();
        }
        else {
            me.notifCount = 0;
            me.updateNotifCount();
            me.storage.notifyClientOfOfflineMessages();
        }
    });
};

NotificationsClient.prototype.updateNotifCount = function() {
    this.NUMBER_BADGE.text(this.notifCount);
    this.clearNumberBadgeClasses();
    this.NUMBER_BADGE.addClass(this.notifCount > 0 ? "label-success"
        : "label-default");
};

NotificationsClient.prototype.renderMessages = function() {
    if (this.renderSuspended)
        return;
    const msgs = this.messages;
    let content = '';
    let wereMessages;
    let msgsSorted = Object.keys(this.messages)
         .sort(function(a,b) {
            return Number(msgs[b].date) - Number(msgs[a].date);
        });

    for (let msgKey of msgsSorted) {
        wereMessages = true;
        const msg = this.messages[msgKey];
        content += interpolate(this.CONTENT_ENTRY,
            {
                address: msg.address || '#',
                id: msg.id,
                details: msg.details || '',
                notclass: msg.cached ? "notification" : "notification-new",
                time: notifs_getDateTimeOf(msg.date)
            }, true);

    }

    this.TABLE_NOTIFICATIONS.html(content);
    for (let msgKey of msgsSorted) {
        translationClient.translate(this.messages[msgKey].message)
            .catch(() => this.messages[msgKey].message)
            .then((msg) => {
                let text = interpolate(msg, this.messages[msgKey].arguments, true);
                $('#notif_msg_' + msgKey).text(text);
            });
    }
    if (!wereMessages) {
        this.TABLE_NOTIFICATIONS.append(this.NO_NOTIFICATIONS);
    }
};

function notifs_getDateTimeOf(timeOfMsg) {
    const t = function(time) { return time < 10 ? "0" + time : time; };
    const dateOfMsg = new Date(timeOfMsg);

    if (Date.now() - timeOfMsg < 24 * 60 * 60 * 1000) {
        return interpolate("%s:%s", [t(dateOfMsg.getHours()), t(dateOfMsg.getMinutes())]);
    }
    else {
        return interpolate("%s-%s-%s %s:%s", [t(dateOfMsg.getDate()), t(dateOfMsg.getMonth()),
            dateOfMsg.getYear(), t(dateOfMsg.getHours()), t(dateOfMsg.getMinutes())]);
    }
}

NotificationsClient.prototype.generatePermissionBanner = function () {
    return $("<div></div>").attr("id", "notifications_banner")
        .attr("role", "alert").addClass("alert alert-info")
        .text(gettext("Would you like to enable desktop notifications (for submission results and more)?"))
        .append(
            $("<a></a>").addClass("alert-link").attr("href", "#")
                .text(gettext("Yes, please!"))
                .click(() => {
                    this.permissionBanner.hide();
                    Notification.requestPermission().then((perm) => {
                        for (let request of this.waitingPermissions) {
                            if (perm === "granted") {
                                request.resolve();
                            } else {
                                request.reject("Notifications permission denied");
                            }
                        }
                        this.waitingPermissions = [];
                    });
                })
        ).append(
            $("<a></a>").addClass("alert-link").attr("href", "#")
                .text(gettext("Never ask again on this computer"))
                .click(() => {
                    this.permissionBanner.hide();
                    window.localStorage.setItem("notif_denied", true);
                    for (let request of this.waitingPermissions) {
                        request.reject("User rejected notifications");
                    }
                    this.waitingPermissions = [];
                })
        );
}

NotificationsClient.prototype.askPermission = function () {
    if (window.Notification) {
        if (Notification.permission === "granted")
            return Promise.resolve();
        if (Notification.permission === "denied" || window.localStorage["notif_denied"])
            return Promise.reject("User rejected notifications");
        return new Promise((resolve, reject) => {
            this.waitingPermissions.push({resolve: resolve, reject: reject});
            if (this.permissionBanner === null) {
                this.permissionBanner = this.generatePermissionBanner();
                this.permissionBanner.prependTo($(".body"));
            }
            this.permissionBanner.show();
        });
    }
    return Promise.reject("Notifications support missing");
};

NotificationsClient.prototype.onMessageReceived = function(message, cached) {
    if (this.messages[message.id]) {
        return;
    }
    if (cached) {
        message.cached = true;
    }
    this.messages[message.id] = message;
    this.renderMessages();
    if (!cached) {
        this.notifCount++;
        this.updateNotifCount();
        $.localStorage.set("notif_" + message.date + "_" + message.id, message);
        if (message.popup && !$(this.DROPDOWN_PANEL).hasClass('open')) {
            $(this.DROPDOWN).dropdown('toggle');
        }

        this.askPermission().then(() => {
            return translationClient.translate(message.message).catch(() => message.message);
        }).then((translation) => {
            let content = interpolate(translation, message.arguments, true);
            let notification = new Notification(content,
                {tag: message.id, timestamp: message.date, body: content});
            if (message.address) {
                notification.addEventListener('click', (ev) => {
                    ev.preventDefault();
                    window.open(message.address, '_blank');
                });
            }
            this.openNotifications.push(notification);
        }).catch((err) => {
            console.warn("Failed to display notification.", err);
        });
    }
    if (this.DEBUG) {
        console.log('Received message:', message);
    }
};

NotificationsClient.prototype.acknowledgeMessages = function() {
    this.notifCount = 0;
    this.updateNotifCount();
    this.openNotifications.forEach((notif) => {
        notif.close();
    });
    this.openNotifications = [];
};

function MessageManager(notificationsClient) {
    this.client = notificationsClient;
}

MessageManager.prototype.cleanCache = function() {
    const dateHourAgo = Date.now() - 60 * 60 * 1000;
    const keys = $.localStorage.keys();
    for (let key of keys) {
        let keyInfo = key.split('_');
        if (keyInfo[0] !== "notif")
            continue;
        if (Number(keyInfo[1]) < dateHourAgo)
            $.localStorage.remove(key);
    }
};

MessageManager.prototype.onMessageReceived = function(message) {
    this.client.onMessageReceived(message);
};

MessageManager.prototype.notifyClientOfOfflineMessages = function() {
    this.cleanCache();
    this.client.renderSuspended = true;
    const keys = $.localStorage.keys().filter(function(k) {
        return k.indexOf("notif") === 0;
    });
    for (let key of keys) {
        this.client.onMessageReceived($.localStorage.get(key), true);
    }
    this.client.renderSuspended = false;
    this.client.renderMessages();
};
