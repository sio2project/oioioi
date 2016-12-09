$(function() {

    function synchronizeQuestions(data) {
        var messages_node =  $('#' + data.messages.id);
        if (data.messages === null || data.messages.id === null
            || data.messages.text === null || data.messages.link === null) {
            messages_node.hide();
            return;
        }
        messages_node.show();
        messages_node.attr('href', data.messages.link);
        $('#' + data.messages.id + ' > span').text(data.messages.text);
    }

    $(window).on('initialStatus', function(ev, data) {
        synchronizeQuestions(data);
        $(window).on('updateStatus', function(ev, data) {
            synchronizeQuestions(data);
        });
    });
});
