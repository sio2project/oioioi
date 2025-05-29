var Problem = (function() {
    "use strict";

    var Problem = function(short_name, scores, max_score) {
        this.short_name = short_name;
        this.scores = scores;
        this.max_score = max_score;
        this.chartColumns = 10;
    };

    Problem.prototype.setupChart = function() {
        var histogramData = [];

        if (this.max_score !== 0) {
            histogramData = this._getHistorgramData();
        }

        var chartOptions = {
            chart: {
                renderTo: "pointsChart-" + this.short_name,
                type: "column",
                height: 60,
                margin: [2, 3, 2, 3],
                style: {
                    overflow: 'visible'
                },
                skipClone: true
            },
            title: {
                text: undefined
            },
            credits: {
                enabled: false
            },
            legend: {
                enabled: false
            },
            xAxis: {
                min: 0,
                max: this.max_score,
                plotBands: false,
                plotLines: false,
                labels: {
                    enabled: false
                },
                title: {
                    enabled: true,
                    text: gettext("Score"),
                    style: {"color": "#707070", "font-size": "0.7em"}
                },
                startOnTick: false,
                endOnTick: false,
                tickPositions: [],
                lineWidth: 1,
                tickWidth: 0
            },
            yAxis: {
                min: 0,
                labels: {
                    enabled: false
                },
                title: {
                    enabled: true,
                    text: gettext("Participants"),
                    style: {"color": "#707070", "font-size": "0.7em"}
                },
                startOnTick: false,
                endOnTick: false,
                tickPositions: [],
                lineWidth: 1
            },
            tooltip: {
                formatter: function() {
                    return interpolate(
                        ngettext(
                            '<strong>%(low)s - %(high)s points</strong><br>%(cnt)s participant', // XXX: splitting into 
                                                                                // multiple lines will break translation
                            '<strong>%(low)s - %(high)s points</strong><br>%(cnt)s participants',
                            this.point.y
                        ), {
                            low: this.point.l,
                            high: this.point.x,
                            cnt: this.point.y
                        },
                        true
                    );
                }
            },
            series: [{
                name: "Users",
                data: histogramData
            }],
            plotOptions: {
                series: {
                    animation: false,
                    lineWidth: 2,
                    shadow: false,
                    states: {
                        hover: {
                            lineWidth: 2
                        }
                    },
                    marker: {
                        radius: 2,
                        states: {
                            hover: {
                                radius: 3
                            }
                        }
                    },
                    fillOpacity: 0.25
                },
                column: {
                    negativeColor: '#910000',
                    pointPadding: 0,
                    borderWidth: 0,
                    groupPadding: 0,
                    shadow: false
                }
            }
        };

        this.chart = new Highcharts.Chart(chartOptions);
    };

    Problem.prototype._getHistorgramData = function() {
        var buckets = [];
        var scoreIndex = 0;

        var bucketSize = this.max_score / this.chartColumns;
        for (var threshold = bucketSize; threshold <= this.max_score;
             threshold += bucketSize) {
            var countAtThreshold = 0;

            while (scoreIndex < this.scores.length
                   && this.scores[scoreIndex][0] <= threshold) {
                countAtThreshold += this.scores[scoreIndex][1];
                scoreIndex++;
            }

            buckets.push({
                "x": threshold,
                "y": countAtThreshold,
                "l": threshold - bucketSize
            });
        }

        return buckets;
    };

    return Problem;
}());