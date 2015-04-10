$(function() {
    var formSelector = '#invite-friends-form';
    var form = $(formSelector);
    var alert_box = form.prev();

    function userNotFound(username) {
        alert_box.removeClass('hidden');
        alert_box.children('span').text(username);
    }

    enableUserLookupForm(formSelector, userNotFound);
});
