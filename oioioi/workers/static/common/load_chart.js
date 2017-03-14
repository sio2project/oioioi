function make_load_chart(ajax_url, target_div) {
    var refresh_interval = 1500,
        max_points = 20;
    var chart;
    function requestData() {
        $.ajax({
            url: ajax_url,
            success: function(data) {
                var cap_series = chart.series[0];
                var used_series = chart.series[1];
                var shift = cap_series.data.length > max_points;

                var time = (new Date()).getTime();
                var point_cap = [time, data.capacity];
                var point_av = [time, data.load];
                cap_series.addPoint(point_cap, true, shift);
                used_series.addPoint(point_av, true, shift);

                setTimeout(requestData, refresh_interval);
            },
            error: function() {
                // Displaying a detailed error message isn't really necessary -
                // the worker list view uses the same function to query
                // sioworkersd, so after a refresh the user will see
                // an exception page anyway, with the same error.
                var msg = $('<div class="alert alert-danger"></div>').text(
                    gettext(
                    "Couldn't get data from server. Please refresh the page."));
                $('#' + target_div).after(msg);
            },
            cache: false
        });
    }

    $(document).ready(function() {
        chart = new Highcharts.Chart({
            chart: {
                type: 'area',
                height: 300,
                renderTo: target_div,
                events: {
                    load: requestData
                }
            },
            title: {
                text: gettext("Load"),
            },
            xAxis: {
                type: 'datetime',
                maxZoom: 20 * 1500
            },
            yAxis: {
                tickInterval: 1,
                min: 0,
                title: {
                    enabled: false
                },
            },
            series: [{
                name: gettext("Capacity"),
            },
            {
                name: gettext("Task load"),
            }]
        });
    });
}
