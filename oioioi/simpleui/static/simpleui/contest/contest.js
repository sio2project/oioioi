var Contest = (function() {
    "use strict";

    var Contest = function(contestData) {
        this.contestData = contestData;

        var _this = this;
        $(document).ready(function() {
            _this._setupProblems();
        });
    };

    Contest.prototype._setupProblems = function() {
        for (var problem_name in this.contestData) {
            if (this.contestData.hasOwnProperty(problem_name)) {
                var scores = this.contestData[problem_name].scores;
                var max_score = this.contestData[problem_name].max_score;

                var problem = new Problem(problem_name, scores, max_score);
                problem.setupChart();
            }
        }
    };
    return Contest;
}());