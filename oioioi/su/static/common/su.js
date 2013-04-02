$(function() {
    var were_user;
    var is_under_su;

    function synchronizeSu(data) {
        var before = is_under_su;
        is_under_su = data.is_under_su;

        if (!before && is_under_su) {
            $('#main-navbar').addClass('under-su');
            $('#su-label').show()
        } else if (before && !is_under_su) {
            $('#main-navbar').removeClass('under-su');
            $('#su-label').hide();
        }

        $('#username').text(data.user);

        if (data.user != were_user) {
            if ($('#su-user-reason').length == 0) {
                $('<p id="su-user-reason"></p>').text(gettext(
                    "Reason: User assoctiated with this session has changed."
                )).appendTo('#modal-outdated .modal-body');
            }
            $('#su-user-reason').show();
            $('#modal-outdated').modal('show');
        } else {
            $('#su-user-reason').hide();
        }
    }

    $(window).on('initialStatus', function(ev, data){
        if (data.is_real_superuser) {
            were_user = data.user;
            is_under_su = data.is_under_su;
            synchronizeSu(data);
            $(window).on('updateStatus', function(ev, data){
                if (!('is_under_su' in data))
                    return;
                synchronizeSu(data);
            });
        }
    });
});
