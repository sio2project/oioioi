$(function() {
    const full_text_width = 550;
    const short_text_width = 250;
    var round_duration_in_s;
    var is_time_admin;
    var is_admin_time_set;
    var were_admin_time_set;
    var were_time;
    var delay_in_ms = 0;
    var countdown_date;
    var ms_from_epoch;

    function updateClock() {
        var time = new Date(new Date().getTime() + delay_in_ms);
        $('#clock').text(time.toLocaleTimeString());
        var s_from_epoch = Math.floor((new Date().getTime() +
            delay_in_ms) / 1000);
        var remaining_seconds = countdown_date - s_from_epoch;

        if (remaining_seconds >= 0) {
            var countdown = remaining_seconds;
            var countdown_destination;
            var countdown_dest_short;
            if (round_duration_in_s) {
                countdown_destination = gettext("end of the round.");
                countdown_dest_short = gettext("to the end");
            } else {
                countdown_destination = gettext("start of the round.");
                countdown_dest_short = gettext("to the start");
            }

            var seconds = countdown % 60;
            var seconds_str = ngettext("%(seconds)s second ",
                "%(seconds)s seconds ", seconds).fmt({seconds: seconds});
            var seconds_short =
                gettext("%(seconds)ss ").fmt({seconds: seconds});

            countdown = Math.floor(countdown / 60);
            var minutes = countdown % 60;
            var minutes_str = ngettext("%(minutes)s minute ",
                "%(minutes)s minutes ", minutes).fmt({minutes: minutes});
            var minutes_short =
                gettext("%(minutes)sm ").fmt({minutes: minutes});

            countdown = Math.floor(countdown / 60);
            var hours = countdown % 24;
            var hours_str = ngettext("%(hours)s hour ", "%(hours)s hours ",
                hours).fmt({hours: hours});
            var hours_short = gettext("%(hours)sh ").fmt({hours: hours});

            countdown = Math.floor(countdown / 24);
            var days = countdown;
            var days_str = ngettext("%(days)s day ", "%(days)s days ",
                days).fmt({days: days});
            var days_short = gettext("%(days)sd ").fmt({days: days});

            var countdown_text;
            var countdown_short;
            if (days) {
                var countdown_days = days_str + hours_str + minutes_str +
                    seconds_str;
                countdown_short = days_short + hours_short + minutes_short +
                    seconds_short + countdown_dest_short;
                countdown_text = ngettext(
                    "%(countdown_days)sleft to the %(countdown_destination)s",
                    "%(countdown_days)sleft to the %(countdown_destination)s",
                    days).fmt({countdown_days: countdown_days,
                    countdown_destination: countdown_destination});
            } else if (hours) {
                var countdown_hours = hours_str + minutes_str + seconds_str;
                countdown_short = hours_short + minutes_short + seconds_short +
                    countdown_dest_short;
                countdown_text = ngettext(
                    "%(countdown_hours)sleft to the" +
                    " %(countdown_destination)s",
                    "%(countdown_hours)sleft to the" +
                    " %(countdown_destination)s",
                    hours).fmt({countdown_hours: countdown_hours,
                    countdown_destination: countdown_destination});
            } else if (minutes) {
                var countdown_minutes = minutes_str + seconds_str;
                countdown_short = minutes_short + seconds_short +
                    countdown_dest_short;
                countdown_text = ngettext(
                    "%(countdown_minutes)sleft to the" +
                    " %(countdown_destination)s",
                    "%(countdown_minutes)sleft to the" +
                    " %(countdown_destination)s",
                    minutes).fmt({countdown_minutes: countdown_minutes,
                    countdown_destination: countdown_destination});
            } else if (seconds) {
                var countdown_seconds = seconds_str;
                countdown_short = seconds_short + countdown_dest_short;
                countdown_text = ngettext(
                    "%(countdown_seconds)sleft to the" +
                    " %(countdown_destination)s",
                    "%(countdown_seconds)sleft to the" +
                    " %(countdown_destination)s",
                    seconds).fmt({countdown_seconds: countdown_seconds,
                    countdown_destination: countdown_destination});
            } else {
                if (round_duration_in_s) {
                    countdown_text = gettext("The round is over!");
                } else {
                    countdown_text = gettext("The round has started!");
                }
                countdown_short = countdown_text;
            }

            if (round_duration_in_s) {
                var elapsed_part = 1 - remaining_seconds / round_duration_in_s;
                var red;
                var green;
                if (elapsed_part < 0.5) {
                    red = Math.floor(510 * elapsed_part);
                    green = 255;
                } else {
                    red = 255;
                    green = Math.floor(510 * (1 - elapsed_part));
                }
                var blue = 0;
                var bar_color = 'rgb(' + red + ',' + green +',' + blue + ')';
                $('#navbar-progressbar').css({
                    "background": bar_color,
                    "width": Math.floor(elapsed_part * 100) + "%"
                });
            }
            var bar_width = $('#navbar-progress').width();
            if (bar_width < short_text_width) {
                $('#navbar-progress').css('visibility', 'hidden');
            } else {
                $('#navbar-progress').css('visibility', 'visible');
                // When jQuery is supported, we override the countdown
                // type chosen by CSS.
                if (bar_width < full_text_width) {
                    $('#countdown').text(countdown_short);
                    $('#countdown_short').text(countdown_short);
                } else {
                    $('#countdown').text(countdown_text);
                    $('#countdown_short').text(countdown_text);
                }
            }
        }
    }

    var update_interval = null;
    function startClock() {
        clearInterval(update_interval);
        update_interval = setInterval(function() {
            if (is_admin_time_set) {
                clearInterval(update_interval);
                update_interval = null;
            } else {
                updateClock();
            }
        }, 1000);
    }

    var admin_clock = $('#admin-clock');
    //admin-clock exists only if real_user is a superuser
    if (admin_clock.length == 1) {
        admin_clock.on('click', function() {
            var time;
            if (is_admin_time_set) {
                time = new Date(ms_from_epoch);
            } else {
                time = new Date(new Date().getTime() + delay_in_ms);
            }
            $('#admin-time').val(time.getFullYear() +
                "-" + ("0" + (time.getMonth() + 1)).slice(-2) +
                "-" + ("0" + time.getDate()).slice(-2) +
                " " + ("0" + time.getHours()).slice(-2) +
                ":" + ("0" + time.getMinutes()).slice(-2) +
                ":" + ("0" + time.getSeconds()).slice(-2));
        });
    }

    function synchronizeTimeWithServer(data) {
        is_admin_time_set = data.is_admin_time_set;
        ms_from_epoch = data.time * 1000;
        var new_delay = ms_from_epoch - new Date().getTime();
        if (Math.abs(new_delay - delay_in_ms) > 1000) {
            delay_in_ms = new_delay;
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
    }

    function synchronizeAdminTime(data) {
        is_admin_time_set = data.is_admin_time_set;
        if (is_admin_time_set) {
            var time = new Date(data.time * 1000);
            updateClock(); // update progressbar
            $('#clock').text(time.toLocaleDateString() +
                " " + time.toLocaleTimeString());
            if (!$('#main-navbar').hasClass('admin-time-set')) {
                $('#main-navbar').addClass('admin-time-set');
                $('#admin-time-label').show();
            }
        } else if ($('#main-navbar').hasClass('admin-time-set')) {
            startClock();
            $('#main-navbar').removeClass('admin-time-set');
            $('#admin-time-label').hide();
        }

        if (is_admin_time_set != were_admin_time_set ||
                (is_admin_time_set && were_time != data.time)) {
            if ($('#admin-time-reason').length === 0) {
                $('<p id="admin-time-reason"></p>').text(
                        gettext("Reason: Admin-time status has changed.")
                    ).appendTo('#modal-outdated .modal-body');
            }
            $('#admin-time-reason').show();
            $('#modal-outdated').modal('show');
        } else {
            $('#admin-time-reason').hide();
        }
    }

    $(window).one('initialStatus', function(ev, data){
        were_admin_time_set = data.is_admin_time_set;
        were_time = data.time;
        is_time_admin = data.is_time_admin;
        synchronizeTimeWithServer(data);
        updateClock();
        startClock();
        if (is_time_admin) {
            synchronizeAdminTime(data);
        }
    });

    $(window).on('updateStatus', function(ev, data){
        if (!('time' in data))
            return;

        synchronizeTimeWithServer(data);
        if (is_time_admin) {
            synchronizeAdminTime(data);
        }
    });
});
