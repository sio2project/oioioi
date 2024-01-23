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
            $.get('/translate/', { query: originalText }, 'json')
                .success(function (data) {
                    tClient.translationCache[originalText] = data.answer;
                    for (let request of tClient.translationQueue[originalText]) {
                        request.resolve(data.answer);
                    }
                    delete tClient.translationQueue[originalText];
                })
                .fail(function (err) {
                    console.warn('Translation failed!', err);
                    for (let request of tClient.translationQueue[originalText]) {
                        request.reject(err);
                    }
                    delete tClient.translationQueue[originalText];
                });
        }
        this.translationQueue[originalText].push({ resolve: resolve, reject: reject });
    });
};

let translationClient = new TranslationClient();

function NotificationsClient(serverUrl, sessionId) {
    this.TABLE_NOTIFICATIONS_ID = "#notifications_table";
    this.HEADER_REFRESH_ID = "#notifications_refresh";
    this.DROPDOWN_ID = "#notifications_dropdown";
    this.DROPDOWN_PANEL_ID = "#notifications_panel";
    this.DROPDOWN_ICON_ID = "#notifications_icon";
    this.DROPDOWN_DISCONNECTED_ID = "#notifications_error";
    this.TABLE_NOTIFICATIONS = $(this.TABLE_NOTIFICATIONS_ID);
    this.HEADER_REFRESH = $(this.HEADER_REFRESH_ID);
    this.HEADER_REFRESH_SPINNER = this.HEADER_REFRESH.find("span");
    this.DROPDOWN_PANEL = $(this.DROPDOWN_PANEL_ID);
    this.DROPDOWN = $(this.DROPDOWN_ID);
    this.DROPDOWN_ICON = $(this.DROPDOWN_ICON_ID);
    this.DROPDOWN_DISCONNECTED = $(this.DROPDOWN_DISCONNECTED_ID);
    this.DEBUG = true;
    this.NOTIF_SERVER_URL = serverUrl;
    this.NOTIF_SESSION = sessionId;
    this.socket = undefined;
    this.notifCount = 0;

    this.dropdownUpToDate = false;
    this.dropdownLoading = false;

    this.openNotifications = [];
    this.waitingPermissions = [];
    this.permissionBanner = null;

    if (typeof (io) === 'undefined') {
        this.setErrorState();
        this.DROPDOWN_DISCONNECTED.show();
        return;
    }

    this.DROPDOWN_PANEL.on("show.bs.dropdown", this.renderMessages.bind(this));
    this.DROPDOWN_PANEL.on("shown.bs.dropdown", this.acknowledgeMessages.bind(this));
    this.DROPDOWN_PANEL.on("hidden.bs.dropdown", this.acknowledgeMessages.bind(this));
    this.DROPDOWN_PANEL.find(".dropdown-menu").click((ev) => {
        ev.stopPropagation();
    });
    this.HEADER_REFRESH.click(() => {
        if (this.dropdownLoading)
            return;
        this.dropdownUpToDate = false;
        this.renderMessages();
    });
    this.socket = io.connect(this.NOTIF_SERVER_URL);
    this.socket.on('connect', this.authenticate.bind(this));
    this.socket.emits = function (k, v) {
        this.socket.emit(k, JSON.stringify(v));
    }.bind(this);
    setInterval(this.notifWatchdog.bind(this), 2000);
    this.socket.on("message", this.onMessageReceived.bind(this));
}

NotificationsClient.prototype.constructor = NotificationsClient;

NotificationsClient.prototype.notifWatchdog = function () {
    if (!this.socket || !this.socket.connected) {
        this.setErrorState();
        this.DROPDOWN_DISCONNECTED.show();
    }
};

NotificationsClient.prototype.clearNumberBadgeClasses = function () {
    this.DROPDOWN.removeClass("btn btn-danger");
    this.DROPDOWN_ICON.removeClass("text-warning");
    this.DROPDOWN_DISCONNECTED.hide();
};

NotificationsClient.prototype.setErrorState = function () {
    this.clearNumberBadgeClasses();
    this.DROPDOWN_ICON.addClass("text-warning");
};

NotificationsClient.prototype.authenticate = function () {
    let me = this;
    const sid = this.NOTIF_SESSION;
    this.socket.emits("authenticate", { session_id: sid });
    this.socket.on("authenticate", function (result) {
        if (result.status !== 'OK') {
            me.setErrorState();
            me.DROPDOWN_DISCONNECTED.show();
        }
        else {
            me.notifCount = 0;
            me.updateNotifCount();
        }
    });
};

NotificationsClient.prototype.updateNotifCount = function () {
    this.clearNumberBadgeClasses();
    if (this.notifCount > 0)
        this.DROPDOWN.addClass("btn btn-danger");
};

NotificationsClient.prototype.renderMessages = function () {
    if (this.dropdownUpToDate || this.dropdownLoading)
        return;
    this.dropdownLoading = true;
    this.dropdownUpToDate = true;
    this.HEADER_REFRESH_SPINNER.addClass("spinner");
    $.get('/latest_submissions/', {}, 'html')
        .success((data) => {
            this.dropdownLoading = false;
            this.HEADER_REFRESH_SPINNER.removeClass("spinner");
            this.TABLE_NOTIFICATIONS.html(data);
            if (this.TABLE_NOTIFICATIONS.find("tbody tr").length < 1) {
                let columnsCount = this.TABLE_NOTIFICATIONS.find("thead th").length;
                this.TABLE_NOTIFICATIONS.find("tbody").append(
                    $("<tr></tr>").append(
                        $("<td></td>").attr('colspan', columnsCount)
                            .addClass("text-center")
                            .text(gettext("You don't have any submissions."))
                    )
                );
            }
            this.dropdownLoading = false;
        }).fail((err) => {
            console.warn(err);
            this.dropdownLoading = false;
            this.HEADER_REFRESH_SPINNER.removeClass("spinner");
            this.setErrorState();
            let text = gettext("A network error occured. Recent submissions list could not be loaded");
            this.TABLE_NOTIFICATIONS.html(
                $("<span></span>").addClass("dropdown-item-text").text(text)
            );
        });
};

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
};

NotificationsClient.prototype.askPermission = function () {
    if (window.Notification) {
        if (Notification.permission === "granted")
            return Promise.resolve();
        if (Notification.permission === "denied" || window.localStorage["notif_denied"])
            return Promise.reject("User rejected notifications");
        return new Promise((resolve, reject) => {
            this.waitingPermissions.push({ resolve: resolve, reject: reject });
            if (this.permissionBanner === null) {
                this.permissionBanner = this.generatePermissionBanner();
                this.permissionBanner.prependTo($(".body"));
            }
            this.permissionBanner.show();
        });
    }
    return Promise.reject("Notifications support missing");
};

NotificationsClient.prototype.onMessageReceived = function (message) {
    if (this.DEBUG) {
        console.log('Received message:', message);
    }

    if (message.type == 'submission_judged' || message.type == 'initial_results') {
        this.dropdownUpToDate = false;
        this.notifCount++;
        this.updateNotifCount();
        if (message.popup && !this.DROPDOWN_PANEL.hasClass('open')) {
            $(this.DROPDOWN).dropdown('toggle');
        }
        $(window).trigger('submissionUpdated', {
            submissionId: message.arguments.submission_id,
        });
    }

    this.askPermission().then(() => {
        return translationClient.translate(message.message).catch(() => message.message);
    }).then((translation) => {
        let content = interpolate(translation, message.arguments, true);
        let notification = new Notification(content,
            { tag: message.id, timestamp: message.date, body: content });
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
    if (this.DROPDOWN_PANEL.hasClass("open")) {
        this.renderMessages();
    }
};

NotificationsClient.prototype.acknowledgeMessages = function () {
    this.notifCount = 0;
    this.updateNotifCount();
    this.openNotifications.forEach((notif) => {
        notif.close();
    });
    this.openNotifications = [];
};
