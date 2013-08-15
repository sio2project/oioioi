function startRefreshingBalloons(body_url) {
    var prev_body;
    setInterval(function() {
        $.get(body_url, function(data) {
            if (data != prev_body) {
                prev_body = data;
                $('body').html(data);
            }
        });
    }, 5000);
}
