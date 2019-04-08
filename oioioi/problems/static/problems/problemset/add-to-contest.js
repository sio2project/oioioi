$(document).ready(function() {
    const link = $('a[data-addorupdate]');

    // Disable scrolling to top of
    // the webpage on contest selection
    link.click(function(event) {
        event.preventDefault();
    });

    // Set up "Add to contest" links
    link.one('click', function() {
        const addToContest = $('#add_to_contest');
        const urlKey = $('#url_key');
        const button = $(this).closest('.btn-group').children('.btn');

        button.children('.loading-spinner').removeClass('hidden');
        button.children('.add-contest-caret').addClass('hidden');

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
