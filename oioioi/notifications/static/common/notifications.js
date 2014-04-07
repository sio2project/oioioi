var notificationsClient;

function NotificationsClient(serverUrl, sessionId) {
    this.NUMBER_BADGE_ID = "#notifications_number";
    this.TABLE_NOTIFICATIONS_ID = "#balloon_table_notifications";
    this.NO_NOTIFICATIONS_ID = "#info_no_notifications";
    this.NUMBER_BADGE = $(this.NUMBER_BADGE_ID);
    this.TABLE_NOTIFICATIONS = $(this.TABLE_NOTIFICATIONS_ID);
    this.NO_NOTIFICATIONS = $(this.NO_NOTIFICATIONS_ID);
    this.DEBUG = true;
    this.NOTIF_SERVER_URL = serverUrl;
    this.NOTIF_SESSION = sessionId;

    this.socket = undefined;
    this.notifCount = 0;
    this.unconfirmedMessages = [];
    this.messages = {};

    if (typeof(io) === 'undefined')
    {
        this.setErrorState();
        return;
    }

    this.renderMessages();
    $(this.NUMBER_BADGE).on("click", this.acknowledgeMessages.bind(this));
    this.socket = io.connect(this.NOTIF_SERVER_URL);
    this.socket.on('connect', this.authenticate.bind(this));
    this.socket.emits = function(k, v) {
        this.socket.emit(k, JSON.stringify(v));
    }.bind(this);
    setInterval(this.notifWatchdog.bind(this), 2000);
    this.socket.on("message", this.onMessageReceived.bind(this));
    this.socket.on("ack_nots", this.onAcknowledgeCompleted.bind(this));
}

NotificationsClient.prototype.constructor = NotificationsClient;

NotificationsClient.prototype.notifWatchdog = function() {
    if (!this.socket || !this.socket.socket.connected) {
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
        }
    });
};

NotificationsClient.prototype.updateNotifCount = function() {
    this.NUMBER_BADGE.text(this.notifCount);
    this.clearNumberBadgeClasses();
    this.NUMBER_BADGE.addClass(this.notifCount > 0 ? "label-success" : "label-primary");
};

NotificationsClient.prototype.renderMessages = function() {
    var content = '<colgroup><col width="50px"/><col/></colgroup>';
    var wereMessages;
    var msgKeys = Object.keys(this.messages)
        .sort(function(a,b) { return Number(a) < Number(b); });

    for (var msgKeyId in msgKeys) {
        wereMessages = true;
        content += '<tr><td></td><td>' + this.messages[msgKeys[msgKeyId]].message +
            '</td></tr>';
    }

    this.NO_NOTIFICATIONS.toggle(!wereMessages);
    this.TABLE_NOTIFICATIONS.html(content);
};

NotificationsClient.prototype.onMessageReceived = function(message) {
    if (this.messages[message.id]) {
        return;
    }
    this.messages[message.id] = message;
    this.renderMessages();

    ++this.notifCount;
    this.updateNotifCount();
    this.unconfirmedMessages.push(message.id);
    if (this.DEBUG) {
        console.log('Received message: ' + JSON.stringify(message));
    }
};

NotificationsClient.prototype.onAcknowledgeCompleted = function(result) {
    if (result && result.status === 'OK') {
        this.notifCount = 0;
        this.updateNotifCount();
    }
};

NotificationsClient.prototype.acknowledgeMessages = function() {
    if (this.unconfirmedMessages.length > 0) {
        this.socket.emits("ack_nots", this.unconfirmedMessages);
        if (this.DEBUG) {
           console.log('Acknowledging messages: ' + JSON.stringify(this.unconfirmedMessages));
        }
    }
};