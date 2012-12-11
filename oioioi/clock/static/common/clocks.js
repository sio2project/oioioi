$(function() {
    var round_times_controller_url;
    var round_duration_in_s;
    var is_admin;
    var is_admin_time_set;
    var delay_in_ms = null;
    var countdown_date;
    var ms_from_epoch;

    function updateClock() {
        var time = new Date(new Date().getTime() + delay_in_ms);
        $("#clock").text(time.toLocaleTimeString());
        var s_from_epoch = Math.floor((new Date().getTime() +
            delay_in_ms) / 1000);
        var remaining_seconds = countdown_date - s_from_epoch;

        if (remaining_seconds >= 0) {
            var countdown = remaining_seconds;
            if (round_duration_in_s) {
                var countdown_text_description = " left to the end" +
                    " of the round.";
            } else {
                var countdown_text_description = " left to the start" +
                    " of the round.";
            }

            var seconds = countdown % 60;
            countdown = Math.floor(countdown / 60);
            var minutes = countdown % 60;
            countdown = Math.floor(countdown / 60);
            var hours = countdown % 24;
            countdown = Math.floor(countdown / 24);
            var days = countdown;

            if (days) {
                var countdown_text = days + "d " + hours + "h " +
                    minutes + "m " + seconds + "s ";
            } else if (hours) {
                var countdown_text = hours + "h " + minutes + "m " +
                    seconds +"s ";
            } else if (minutes) {
                var countdown_text =  minutes + "m " + seconds + "s ";
            } else if (seconds) {
                var countdown_text = seconds + "s ";
            } else {
                countdown_text_description = "";
                if (round_duration_in_s) {
                    var countdown_text = "The round is over!";
                } else {
                    var countdown_text = "The round has started!";
                }
            }
            countdown_text += countdown_text_description;

            if (round_duration_in_s) {
                var elapsed_part = 1 - remaining_seconds / round_duration_in_s;
                if (elapsed_part < 0.5) {
                    var red = Math.floor(510 * elapsed_part);
                    var green = 255;
                } else {
                    var red = 255;
                    var green = Math.floor(510 * (1 - elapsed_part));
                }
                var blue = 0;
                var bar_color = "rgb(" + red + "," + green +"," + blue + ")";
                $("#navbar-progressbar").css({
                    "background": bar_color,
                    "width": Math.floor(elapsed_part * 100) + "%"});
            }

            $("#countdown").text(countdown_text);
        }
    }

    function synchronizeTimeWithServer() {
        round_times_controller_url = oioioi_base_url + "round_times/";

        $.getJSON(round_times_controller_url, function(data) {
            is_admin = data.is_admin;
            is_admin_time_set = data.is_admin_time_set;
            ms_from_epoch = data.time * 1000;
            delay_in_ms = ms_from_epoch - new Date().getTime();
            if (is_admin_time_set) {
                return;
            }
            var start_date = data.round_start_date;
            var end_date = data.round_end_date;
            if (end_date) {
                countdown_date = end_date;
                round_duration_in_s = end_date - start_date;
            } else if (start_date) {
                countdown_date = start_date;
                round_duration_in_s = null;
            }
            updateClock();
        });
    }

    function start_clock() {
        synchronizeTimeWithServer()
        delay_in_ms = null;

        var update_interval = setInterval(function() {
            if (delay_in_ms != null) {
                if (is_admin_time_set) {
                    clearInterval(update_interval);
                } else {
                    updateClock();
                }
            }
        }, 1000);

        var sync_interval = setInterval(function() {
            if (is_admin_time_set) {
                clearInterval(sync_interval);
            } else {
                synchronizeTimeWithServer();
            }
        }, 300000);
    }

    start_clock();

    var admin_clock = document.getElementById('admin-clock');
    //admin-clock exists only if user is a superuser
    if (admin_clock) {
        admin_clock.addEventListener('click', function() {
            var time;
            if (is_admin_time_set) {
                time = new Date(ms_from_epoch);
            } else {
                time = new Date(new Date().getTime() + delay_in_ms);
            }
            document.getElementById("admin-time").value = time.getFullYear() +
                "-" + ("0" + (time.getMonth() + 1)).slice(-2) +
                "-" + ("0" + time.getDate()).slice(-2) +
                " " + ("0" + time.getHours()).slice(-2) +
                ":" + ("0" + time.getMinutes()).slice(-2) +
                ":" + ("0" + time.getSeconds()).slice(-2);
        }, false);
    }

    var admin_sync_interval = setInterval(function() {
        if (delay_in_ms != null) {
            if (is_admin) {
                $.getJSON(round_times_controller_url, function(data) {
                    is_admin_time_set = data.is_admin_time_set;
                    if (is_admin_time_set) {
                        var time = new Date(data.time * 1000);
                        $("#clock").text(time.toLocaleDateString() +
                            " " + time.toLocaleTimeString());
                        if (!($("#main-navbar").hasClass("admin-time-set"))) {
                            start_clock();
                            $("#main-navbar").addClass("admin-time-set");
                            $("#admin-time-label").css({"display": "inline"})
                        }
                    } else if (!is_admin_time_set &&
                        ($("#main-navbar").hasClass("admin-time-set"))) {
                        start_clock();
                        $("#main-navbar").removeClass("admin-time-set");
                        $("#admin-time-label").css({"display": "none"})
                    }
                });
            } else {
                clearInterval(admin_sync_interval);
            }
        }
    }, 10000);
});
