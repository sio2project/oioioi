var notificationsClient;

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
    this.CONTENT_ENTRY = '<tr><td class="%(notclass)s"><a href="%(address)s" ' + '' +
        'id="notif_msg_%(id)s">...</a><br/>' +
        '<span class="notification-details">%(details)s</span>' +
        '</td><td class="notification-time">%(time)s</td></tr>';
    this.socket = undefined;
    this.notifCount = 0;
    this.unconfirmedMessages = [];
    this.messages = [];
    this.translatedText = {};
    this.renderSuspended = false;

    if (typeof(io) === 'undefined')
    {
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
    this.NUMBER_BADGE.removeClass("label-primary");
    this.NUMBER_BADGE.removeClass("label-success");
    this.NUMBER_BADGE.removeClass("label-warning");
};

NotificationsClient.prototype.setErrorState = function() {
    this.NUMBER_BADGE.text('!');
    this.clearNumberBadgeClasses();
    this.NUMBER_BADGE.addClass("label-warning");
};

NotificationsClient.prototype.resolveMessageText =
    function(messageId, originalText, args) {
        var me = this;
        if (me.translatedText[messageId]) {
            $('#notif_msg_' + messageId).text(me.translatedText[messageId]);
        }
        else {
            $.get('/translate/',
                {query: originalText}, 'json').
                success(function (data) {
                    var text = interpolate(data.answer, args, true);
                    me.translatedText[messageId] = text;
                    $('#notif_msg_' + messageId).text(text);
                }).
                fail(function (err) {
                    console.warn('Translation failed!' + err);
                    $('#notif_msg_' + messageId).text(
                        interpolate(originalText, args, true));
                });
        }
};

NotificationsClient.prototype.authenticate = function() {
    var me = this;
    var sid = this.NOTIF_SESSION;
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
    this.NUMBER_BADGE.addClass(this.notifCount > 0 ? "label-success" : "label-primary");
};

NotificationsClient.prototype.renderMessages = function() {
    if (this.renderSuspended)
        return;
    var msgs = this.messages;
    var content = '<colgroup><col/><col width="100px"/></colgroup>';
    var wereMessages;
    var msgsSorted = Object.keys(this.messages)
         .sort(function(a,b) {
            return Number(msgs[b].date) - Number(msgs[a].date);
        });

    for (var msgKeyId in msgsSorted) {
        var msgKey = msgsSorted[msgKeyId];
        wereMessages = true;
        var msg = this.messages[msgKey];
        content += interpolate(this.CONTENT_ENTRY,
            {
                address: msg.address || '#',
                id: msg.id,
                details: msg.details || '',
                notclass: msg.cached ? "notification" : "notification-new",
                time: notifs_getDateTimeOf(msg.date)
            }, true);

    }

    this.NO_NOTIFICATIONS.toggle(!wereMessages);
    this.TABLE_NOTIFICATIONS.html(content);
    for (var msgKeyId in msgsSorted) {
        var msgKey = msgsSorted[msgKeyId];
        this.resolveMessageText(msgKey,
            this.messages[msgKey].message,
            this.messages[msgKey].arguments);
    }
};

function notifs_getDateTimeOf(timeOfMsg) {
    var t = function(time) { return time < 10 ? "0" + time : time; };
    var dateOfMsg = new Date(timeOfMsg);
    var now = new Date();
    if (false || Date.now() - timeOfMsg < 24 * 60 * 60 * 1000) {
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
    var dateHourAgo = Date.now() - 60 * 60 * 1000;
    var keys = $.localStorage.keys();
    for (var keyId in keys) {
        var key = keys[keyId];
        var keyInfo = key.split('_');
        if (keyInfo[0] != "notif")
            continue;
        if (Number(keyInfo[1]) < dateHourAgo)
            $.localStorage.remove(key);
    }
}

MessageManager.prototype.onMessageReceived = function(message) {
    this.client.onMessageReceived(message);
}

MessageManager.prototype.notifyClientOfOfflineMessages = function() {
    this.cleanCache();
    this.client.renderSuspended = true;
    var keys = $.localStorage.keys().filter(function(k) {
        return k.indexOf("notif") === 0;
    });
    for (var keyId in keys) {
        this.client.onMessageReceived($.localStorage.get(keys[keyId]), true);
    }
    this.client.renderSuspended = false;
    this.client.renderMessages();
}
