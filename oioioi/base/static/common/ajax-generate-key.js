$(document).ready(function() {
    $('[id$=_input-with-generate]').each(function() {
        var input = $(this).children('input[type=text]');
        $(this).children('input[type=button]').click(function() {
            if ($(this).hasClass('unclickable')) {
                return false;
            }

            var btn = $(this).addClass('unclickable').attr('href', '#');
            $.ajax({
                url: /generate_key/,
                type: 'GET',
                dataType: 'text'
            }).done(function(data) {
                input.val(data);
            }).always(function() {
                btn.removeClass('unclickable');
            });
        });
    });
});
