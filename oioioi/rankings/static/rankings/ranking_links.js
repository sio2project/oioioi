$(function() {
    var username;
    var is_contest_admin;

    function getUserResults() {
        return $('span.result[data-username="' + username + '"]');
    }

    function getAllResults() {
        return $('span.result');
    }

    function canSeeAllSubmissions() {
        return is_contest_admin;
    }

    function getViewableResults() {
        if (canSeeAllSubmissions()) {
            return getAllResults();
        } else {
            return getUserResults();
        }
    }

    function addLinksToViewableResults() {
        var viewableResults = getViewableResults();

        $.each(viewableResults, function() {
            $(this).wrap(
                $('<a>', {
                    href: $(this).data('result_url')
                })
            );
        });
    }

    $(window).one('initialStatus', function(ev, data) {
        username = data.user;
        is_contest_admin = data.is_contest_admin;

        addLinksToViewableResults();
    });
});