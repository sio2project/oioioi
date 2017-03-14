let notificationsClient; // jshint ignore:line

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
    this.unconfirmedMessages = [];
    this.messages = [];
    this.translationCache = {};
    this.translationQueue = {};
    this.renderSuspended = false;

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
    this.socket.on("ack_nots", this.onAcknowledgeCompleted.bind(this));

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

NotificationsClient.prototype.setTranslatedText =
    function(messageId, originalText) {
        $('#notif_msg_' + messageId).text(this.translationCache[originalText]);
    };

NotificationsClient.prototype.resolveMessageText =
    function(messageId, originalText, args) {
        if (this.translationCache[originalText]) {
            this.setTranslatedText(messageId, originalText);
            return;
        }
        // Only the first query initiates a request
        if (!this.translationQueue[originalText]) {
            this.translationQueue[originalText] = [];

            const dispatchCallbacks = (function(text, cacheTranslation) {
                if (cacheTranslation)
                    this.translationCache[originalText] = text;
                const queue = this.translationQueue[originalText];
                for (let i = 0; i < queue.length; i++)
                    queue[i]();
                delete this.translationQueue[originalText];
            }).bind(this);

            $.get('/translate/', {query: originalText}, 'json')
                .success(function (data) {
                    const text = interpolate(data.answer, args, true);
                    dispatchCallbacks(text, true);
                })
                .fail(function (err) {
                    console.warn('Translation failed!' + err);
                    const text = interpolate(originalText, args, true);
                    dispatchCallbacks(text, false);
                });
        }
        // Every query that had a cache miss adds itself to the queue
        const callback = this.setTranslatedText.bind(this, messageId,
                                                   originalText);
        this.translationQueue[originalText].push(callback);
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
        this.resolveMessageText(msgKey,
            this.messages[msgKey].message,
            this.messages[msgKey].arguments);
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
        this.unconfirmedMessages.push(message);
        if (message.popup && !$(this.DROPDOWN_PANEL).hasClass('open')) {
            $(this.DROPDOWN).dropdown('toggle');
        }
    }
    if (this.DEBUG) {
        console.log('Received message: ' + JSON.stringify(message));
    }
};

NotificationsClient.prototype.onAcknowledgeCompleted = function(result) {
    if (result && result.status === 'OK') {
        this.unconfirmedMessages.forEach(function(message) {
            $.localStorage.set("notif_" + message.date + "_" + message.id,
                               message);
        });
        this.notifCount = 0;
        this.updateNotifCount();
    }
};

NotificationsClient.prototype.acknowledgeMessages = function() {
    if (this.unconfirmedMessages.length > 0) {
        this.socket.emits("ack_nots",
                          this.unconfirmedMessages.map(function(message) {
                              return message.id;
                          }));
        if (this.DEBUG) {
           console.log('Acknowledging messages: ' + JSON.stringify(this.unconfirmedMessages));
        }
    }
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
