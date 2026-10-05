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
                var cpu_exec_series = chart.series[2];
                var shift = cap_series.data.length > max_points;

                var time = (new Date()).getTime();
                var point_cap = [time, data.capacity];
                var point_av = [time, data.load];
                var point_cpu_exec = [time, data.cpu_exec_load];
                cap_series.addPoint(point_cap, true, shift);
                used_series.addPoint(point_av, true, shift);
                cpu_exec_series.addPoint(point_cpu_exec, true, shift);

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
        var load_color = Highcharts.getOptions().colors[1];
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
                color: load_color,
            },
            {
                name: gettext("CPU-exec load"),
                color: load_color,
                fillColor: {
                    pattern: {
                        color: load_color,
                        path: {
                            d: 'M 0 0 L 10 10 M 9 -1 L 11 1 M -1 9 L 1 11',
                            strokeWidth: 2,
                        },
                        width: 10,
                        height: 10,
                        opacity: 0.5,
                    },
                },
                zIndex: 1,
            }]
        });
    });
}
