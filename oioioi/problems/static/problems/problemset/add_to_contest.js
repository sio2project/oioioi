$(document).ready(function() {
    // Disable scrolling to top of
    // the webpage on contest selection
    $('a[data-addorupdate]').click(function(ev) {
        ev.preventDefault();
    });

    // Set up "Add to contest" links
    $('a[data-addorupdate]').one('click', function() {
        var problemset_problem_site = $('.problemset-problem-site');
        var loading_spinner;

        if (problemset_problem_site.length) {
            loading_spinner = $('.loading-spinner');
            loading_spinner.removeClass('hide');
            loading_spinner.addClass('job-active');
            $('.add-contest-caret').addClass('hide');
        } else {
            loading_spinner =
                $(this).closest('.add-to-contest-group')
                       .children('.loading-spinner');
            loading_spinner.addClass('job-active');
        }

        // Fill form
        $('#add_to_contest').attr('action',
            $(this).attr('data-addorupdate') + '?key=problemset_source');
        $('#url_key').val($(this).attr('data-urlkey'));

        // http://stackoverflow.com/questions/37883351/browser-doesnt-redraw-webpage-if-i-submit-from-jquery
        setTimeout(function(){
            $('#add_to_contest').submit();
        }, 100);
    });
});
