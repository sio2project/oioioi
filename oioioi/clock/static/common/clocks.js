var seconds_from_epoch;
var remaining_seconds;
var round_duration;

var updateClock = function() {
    var time = new Date(seconds_from_epoch * 1000);
    $("#clock").text(time.toLocaleTimeString());

    if (remaining_seconds >= 0) {
        var countdown = remaining_seconds;
        if (round_duration) {
            var countdown_text_sufix = " left to the end of the round.";
        } else {
            var countdown_text_sufix = " left to the start of the round.";
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
            var countdown_text = hours + "h " + minutes + "m " + seconds + "s ";
        } else if (minutes) {
            var countdown_text =  minutes + "m " + seconds + "s ";
        } else if (seconds) {
            var countdown_text = seconds + "s ";
        } else {
            countdown_text_sufix = "";
            if (round_duration) {
                var countdown_text = "The round is over!";
            } else {
                var countdown_text = "The round has started!";
            }
        }
        countdown_text += countdown_text_sufix;

        if (round_duration) {
            var elapsed_part = 1 - remaining_seconds / round_duration;
            if (elapsed_part < 0.5) {
                var red = Math.floor(510 * elapsed_part);
                var green = 255;
            } else {
                var red = 255;
                var green = Math.floor(510 * (1 - elapsed_part));
            }
            var blue = 0;
            var bar_color = "rgb(" + red + "," + green +"," + blue + ")";
            $("#progressbar").css({
                "background": bar_color,
                "width": Math.floor(elapsed_part * 100) + "%"});
        }

        $("#countdown").text(countdown_text);
    }
}

function synchronizeTimeWithServer() {
    round_times_controller_url = oioioi_base_url + "round_times/";

    $.getJSON(round_times_controller_url, function(data) {
        remaining_seconds = 0;
        seconds_from_epoch = data.time;
        var start_date = data.round_start_date;
        var end_date = data.round_end_date;
        if (end_date) {
            remaining_seconds = end_date - seconds_from_epoch;
            round_duration = end_date - start_date;
        } else if (start_date) {
            remaining_seconds = start_date - seconds_from_epoch;
            round_duration = 0;
        }
        updateClock();
    });
}

$(document).ready(function() {
    seconds_from_epoch = 0;
    synchronizeTimeWithServer()

    setInterval(function() {
        if (seconds_from_epoch != 0) {
            seconds_from_epoch++;
            if (remaining_seconds > 0) {
                remaining_seconds--;
            }
            updateClock();
        }
    }, 1000);

    setInterval(function() {
        synchronizeTimeWithServer();
    }, 300000);
});
