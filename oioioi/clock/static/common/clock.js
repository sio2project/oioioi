var seconds_from_epoch;

var updateClock = function() {
    var time = new Date(seconds_from_epoch * 1000)
    $("#clock").text(time.toLocaleTimeString());
}

function synchronizeTimeWithServer() {
    time_controller_url = oioioi_base_url + "clock/";
    $.getJSON(time_controller_url, function(data) {
        seconds_from_epoch = data.time;
        updateClock();
    });
}

$(document).ready(function() {
    seconds_from_epoch = 0;
    synchronizeTimeWithServer()
    setInterval(function() {
        if (seconds_from_epoch != 0) {
            seconds_from_epoch++;
            updateClock();
        }
    }, 1000);
    setInterval(function() {
        synchronizeTimeWithServer();
    }, 300000);
});

