$(document).ready(function() {
    const link = $('a[data-addorupdate]');

    // Disable scrolling to top of
    // the webpage on contest selection
    link.click(function(event) {
        event.preventDefault();
    });

    // Set up "Add to contest" links
    link.one('click', function() {
        const problemsetProblemSite = $('.problemset__problem-site');
        const addToContest = $('#add_to_contest');
        const urlKey = $('#url_key');
        let spinner;

        if (problemsetProblemSite.length) {
            spinner = $('.loading-spinner');
            spinner.removeClass('hidden');
            spinner.addClass('job-active');
            $('.add-contest-caret').addClass('hidden');
        } else {
            spinner = $(this).closest('.add-to-contest-group')
                .children('.loading-spinner');
            spinner.addClass('job-active');
        }

        // Fill form
        addToContest.attr('action', $(this).attr('data-addorupdate') +
            '?key=problemset_source');
        urlKey.val($(this).attr('data-urlkey'));

        // http://stackoverflow.com/questions/37883351/browser-doesnt-redraw-webpage-if-i-submit-from-jquery
        setTimeout(function() {
            addToContest.submit();
        }, 100);
    });
});
