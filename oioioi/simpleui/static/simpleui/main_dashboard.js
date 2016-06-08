$(function () {
    $('.contest_graph').each(function() {
        var i;
        var container = $(this);
        var max_score = parseInt(container.attr('data-max_score'));
        var scores = JSON.parse(container.attr('data-scores'));

        var no_chunks = 10; //number of bars in the chart
        if (max_score < no_chunks)
          no_chunks = max_score;
        var chunk_size = Math.floor(max_score / no_chunks);

        //Calculate interval sizes
        var intervals = [];
        for (i = 0; i < no_chunks; i++)
        {
            intervals.push({
                start: i * chunk_size,
                end: (i + 1) * chunk_size - 1
            });
        }

        //Create axis labels.
        var axisCategories = [];
        for (i = 0; i < no_chunks; i++)
            axisCategories.push(intervals[i].start + '-' + intervals[i].end);
        axisCategories.push(max_score);

        //Last bar represents 100% score.
        intervals.push({start: max_score, end: max_score});

        //Calculate number of scores for each interval.
        var data = [];
        for (i = 0; i <= no_chunks; i++)
            data.push(0);
        for (i = 0; i < scores.length; i++)
        {
            for (var j = 0; j < no_chunks; j++)
            {
                if (intervals[j].start <= scores[i]
                      && intervals[j].end >= scores[i])
                {
                    data[j]++;
                    break;
                }
            }
        }

        container.highcharts({
            chart: {
                type: 'column'
            },
            title: {
                text: '',
            },
            xAxis: {
                categories: axisCategories,
                title: {
                    text: gettext('Result')
                },
                labels: {
                    enabled: false
                }
            },
            yAxis: {
                title: {
                    text: gettext('Users')
                }
            },
            credits: {
                enabled: false
            },
            series: [{
                name: gettext('Users'),
                data: data
            }],
            legend: {
                enabled: false
            },
            plotOptions: {
                column: {
                    negativeColor: '#910000',
                    pointPadding: 0,
                    borderWidth: 1,
                    groupPadding: 0,
                    shadow: false
                },
                series: {
                    borderColor: '#666666'
                }
            }
        });
    });
});
