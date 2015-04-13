$(function() {
    var content_mover = $('#miniprofile .content-mover');

    var tab_buttons = $('#miniprofile .tab-selector button');
    tab_buttons.on('click', function() {
        var miniprofile_width = $('#miniprofile').width();
        var me = $(this);
        var tab_id = parseInt(me.attr('data-tab-id'));

        tab_buttons.removeClass('btn-primary');
        me.addClass('btn-primary');
        content_mover.css('left',
                (-tab_id * miniprofile_width).toString() + 'px');
    });

    var loginBox = $('#miniprofile .lookup-form input[name=\'username\']');
    function userNotFound() {
        loginBox.addClass('red');
        setTimeout(function() {
            loginBox.removeClass('red');
        }, 500);
    }

    enableUserLookupForm('#miniprofile .lookup-form', userNotFound);
});
