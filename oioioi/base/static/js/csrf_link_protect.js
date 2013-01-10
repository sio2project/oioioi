$(document).ready(function() {
    $('body').on('click', '[data-post-url]', function(event) {
        var form = $('<form method="post"></form>');
        form.attr('action', $(this).data('post-url'));
        form.append($('<input type="hidden"></input>').attr('name',
                'csrfmiddlewaretoken').val($.cookie("csrftoken")));
        form.appendTo('body').submit();
        event.preventDefault();
    });
});
